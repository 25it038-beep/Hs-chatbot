"""
Unified WebSocket Endpoint & Session Controller for HSBot Live Voice.
Handles dynamic engine selection:
- nemotron_voicechat (Primary): direct S2S model (nvidia/nemotron-voicechat)
- cascaded (Fallback): Riva ASR + NVIDIA LLM + Riva TTS
"""

import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

from app.config import settings
from app.live.voicechat import nemotron_voicechat, NemotronVoiceChatUnavailableError
from app.live.session import LiveVoiceSession
from app.live.diagnostics import live_diagnostics

logger = logging.getLogger("hsbot.live.websocket")


async def handle_live_websocket(
    websocket: WebSocket,
    session_id: str = "default_live",
    requested_engine: Optional[str] = None,
):
    """
    Handles live voice bidirectional WebSocket stream.
    Supports on-the-fly engine switching, graceful unavailable signaling,
    and cascaded fallback orchestration.
    """
    await websocket.accept()
    live_diagnostics.register_session_connect()

    # Determine initial engine
    engine = requested_engine or getattr(settings, "live_engine", "cascaded")
    logger.info(f"[LIVE_WS] Session {session_id} connected. Initial engine: {engine}")

    session_cascaded: Optional[LiveVoiceSession] = None

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection",
            "status": "CONNECTED",
            "sessionId": session_id,
            "engine": engine,
            "timestamp": time.time(),
        })

        if engine == "nemotron_voicechat":
            # Probe Nemotron VoiceChat availability
            avail = await nemotron_voicechat.check_availability()
            if not avail.get("available"):
                logger.warning(f"[LIVE_WS] Nemotron VoiceChat unavailable: {avail.get('error')}")
                live_diagnostics.record_error(
                    code="NEMOTRON_VOICECHAT_UNAVAILABLE",
                    message="NVIDIA VoiceChat is unavailable.",
                    details=avail,
                )
                await websocket.send_json({
                    "type": "error",
                    "code": "NEMOTRON_VOICECHAT_UNAVAILABLE",
                    "message": "NVIDIA VoiceChat is unavailable.",
                    "details": {
                        "model": getattr(settings, "nvidia_voicechat_model", "nvidia/nemotron-voicechat"),
                        "status_code": avail.get("status_code"),
                        "reason": avail.get("reason"),
                        "detail": avail.get("detail", "nvidia/nemotron-voicechat is an Early Access speech-to-speech NIM not provisioned on this key."),
                        "catalog_count": avail.get("catalog_count", 0),
                    },
                    "timestamp": time.time(),
                })
                await websocket.send_json({
                    "type": "status",
                    "state": "ERROR",
                    "message": "NVIDIA VoiceChat is unavailable.",
                })

        if engine == "cascaded":
            try:
                session_cascaded = LiveVoiceSession(session_id, websocket)
                session_cascaded.silence_monitor_task = asyncio.create_task(session_cascaded._monitor_silence())
                await websocket.send_json({
                    "type": "status",
                    "state": "LISTENING",
                    "message": "NVIDIA Riva Live is ready. Start speaking.",
                })
                asyncio.create_task(session_cascaded.send_greeting())
            except Exception as bridge_err:
                logger.error(f"[LIVE_WS] Failed to initialize cascaded session: {bridge_err}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "code": "RIVA_BRIDGE_UNAVAILABLE",
                    "message": f"Riva bridge could not start: {bridge_err}. Check NVIDIA_API_KEYS and Node.js availability.",
                    "timestamp": time.time(),
                })
                await websocket.send_json({"type": "status", "state": "ERROR", "message": "Live voice unavailable on this deployment."})
                session_cascaded = None

        # Session loop
        while True:
            raw_msg = await websocket.receive_text()
            if not raw_msg:
                continue

            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            # 1. Engine switch request
            if msg_type == "switch_engine":
                new_engine = msg.get("engine", "cascaded")
                logger.info(f"[LIVE_WS] Session {session_id} switching engine from {engine} to {new_engine}")
                engine = new_engine
                live_diagnostics.set_engine(engine)

                if session_cascaded:
                    await session_cascaded.cleanup()
                    session_cascaded = None

                if engine == "cascaded":
                    session_cascaded = LiveVoiceSession(session_id, websocket)
                    session_cascaded.silence_monitor_task = asyncio.create_task(session_cascaded._monitor_silence())

                await websocket.send_json({
                    "type": "engine_switched",
                    "engine": engine,
                    "status": "ready",
                    "timestamp": time.time(),
                })
                await websocket.send_json({
                    "type": "status",
                    "state": "LISTENING",
                    "message": f"Switched to {engine.replace('_', ' ').title()}",
                })
                continue

            # 2. Retry request
            if msg_type == "retry":
                logger.info(f"[LIVE_WS] Session {session_id} retrying availability probe...")
                avail = await nemotron_voicechat.check_availability(force=True)
                if not avail.get("available"):
                    await websocket.send_json({
                        "type": "error",
                        "code": "NEMOTRON_VOICECHAT_UNAVAILABLE",
                        "message": "NVIDIA VoiceChat is unavailable.",
                        "details": avail,
                        "timestamp": time.time(),
                    })
                else:
                    await websocket.send_json({
                        "type": "status",
                        "state": "LISTENING",
                        "message": "NVIDIA VoiceChat connected",
                    })
                continue

            # 3. Diagnostics snapshot request
            if msg_type == "get_diagnostics":
                diag = await live_diagnostics.get_snapshot()
                await websocket.send_json({
                    "type": "diagnostics",
                    "data": diag,
                })
                continue

            # 4. Engine-specific handling for speech turns
            if engine == "cascaded":
                if session_cascaded is None:
                    session_cascaded = LiveVoiceSession(session_id, websocket)

                # Route message to cascaded session handler
                if msg_type in ("audio_chunk", "audio"):
                    chunk_b64 = msg.get("data") or msg.get("audio") or ""
                    if chunk_b64:
                        import base64
                        try:
                            pcm = base64.b64decode(chunk_b64)
                            await session_cascaded.handle_audio_chunk(pcm)
                        except Exception as e:
                            logger.error(f"Error decoding audio chunk: {e}")

                elif msg_type == "turn_text" or (msg_type == "text" and msg.get("text")):
                    turn_text = msg.get("text", "").strip()
                    if turn_text:
                        asyncio.create_task(session_cascaded.execute_turn(text=turn_text))

                elif msg_type in ("audio_end", "commit_turn"):
                    asyncio.create_task(session_cascaded.finalize_user_speech())

                elif msg_type == "interrupt":
                    await session_cascaded.interrupt()

                elif msg_type == "set_language":
                    await session_cascaded.handle_message(raw_msg)

                elif msg_type == "config":
                    await session_cascaded.handle_message(raw_msg)

                else:
                    await session_cascaded.handle_message(raw_msg)

            elif engine == "nemotron_voicechat":
                # Primary Nemotron VoiceChat S2S
                avail = await nemotron_voicechat.check_availability()
                if not avail.get("available"):
                    await websocket.send_json({
                        "type": "error",
                        "code": "NEMOTRON_VOICECHAT_UNAVAILABLE",
                        "message": "NVIDIA VoiceChat is unavailable.",
                        "details": avail,
                        "timestamp": time.time(),
                    })
                    continue

                if msg_type == "audio_chunk" or msg_type == "turn_text":
                    try:
                        audio_b64 = msg.get("data") or msg.get("audio") if msg_type == "audio_chunk" else None
                        text = msg.get("text") if msg_type == "turn_text" else None
                        async for chunk in nemotron_voicechat.stream_voicechat(audio_pcm_base64=audio_b64, text=text):
                            await websocket.send_json(chunk)
                    except NemotronVoiceChatUnavailableError as e:
                        await websocket.send_json({
                            "type": "error",
                            "code": "NEMOTRON_VOICECHAT_UNAVAILABLE",
                            "message": "NVIDIA VoiceChat is unavailable.",
                            "details": e.details,
                        })

    except WebSocketDisconnect:
        logger.info(f"[LIVE_WS] Session {session_id} disconnected cleanly.")
    except Exception as e:
        logger.error(f"[LIVE_WS] Session {session_id} error: {e}", exc_info=True)
    finally:
        live_diagnostics.register_session_disconnect()
        if session_cascaded:
            await session_cascaded.cleanup()
