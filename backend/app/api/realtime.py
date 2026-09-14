"""Real-time voice conversation WebSocket API router.

Provides:
- WebSocket endpoint: /api/realtime/ws/{conversation_id}
- Real-time event streaming:
  - Inbound: transcript_partial, transcript_final, interrupt, config, audio
  - Outbound: status, tool_executed, ai_text_chunk, ai_text_done, audio_chunk, error
- Barge-in cancellation support
- Direct integration with live session manager & processor
"""

from __future__ import annotations

import asyncio
import json
import base64
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger

from app.realtime.session import live_session_manager, LiveSession
from app.realtime.processor import live_conversation_processor
from app.services.voice.tts import speak_async

router = APIRouter(prefix="/api/realtime", tags=["realtime"])


@router.websocket("/ws/{conversation_id}")
async def realtime_voice_ws(
    websocket: WebSocket,
    conversation_id: str,
    language: Optional[str] = Query("en"),
    timezone: Optional[str] = Query("UTC"),
    location: Optional[str] = Query(None),
):
    """Bidirectional real-time voice and streaming conversation WebSocket."""
    await websocket.accept()
    logger.info("Real-time WebSocket connected for conversation {}", conversation_id)

    # Initialize or get active LiveSession
    session = await live_session_manager.get_or_create(
        conversation_id=conversation_id,
        language=language or "en",
        timezone=timezone or "UTC",
        location=location,
    )
    session.set_status("listening")

    # Send initial status
    await websocket.send_text(
        json.dumps({
            "type": "session_init",
            "session_id": session.session_id,
            "conversation_id": conversation_id,
            "status": "listening",
            "language": session.language,
            "timezone": session.timezone,
            "location": session.location,
        })
    )

    current_worker_task: Optional[asyncio.Task] = None

    async def _run_utterance(user_text: str):
        try:
            async for event in live_conversation_processor.stream_utterance_response(session, user_text):
                try:
                    await websocket.send_text(json.dumps(event))
                except Exception as send_err:
                    logger.warning("Failed sending event to WS: {}", send_err)
                    break
        except asyncio.CancelledError:
            logger.info("Utterance generation task cancelled for session {}", session.session_id)
            try:
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "status": "interrupted",
                }))
            except Exception:
                pass
        except Exception as e:
            logger.error("Error running live utterance: {}", e)
            try:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": str(e),
                }))
            except Exception:
                pass

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except Exception:
                continue

            msg_type = msg.get("type")

            # 1. BARGE-IN INTERRUPTION
            if msg_type == "interrupt":
                logger.info("Received interrupt for session {}", session.session_id)
                session.interrupt()
                if current_worker_task and not current_worker_task.done():
                    current_worker_task.cancel()
                    current_worker_task = None
                session.set_status("listening")
                await websocket.send_text(
                    json.dumps({
                        "type": "status",
                        "status": "listening",
                        "interrupted": True,
                    })
                )
                continue

            # 2. CONFIGURATION UPDATE (e.g. language or location changed on frontend)
            elif msg_type == "config":
                if "language" in msg and msg["language"]:
                    session.language = msg["language"]
                if "timezone" in msg and msg["timezone"]:
                    session.timezone = msg["timezone"]
                if "location" in msg and msg["location"]:
                    session.location = msg["location"]
                logger.info("Updated live session config: lang={}, tz={}, loc={}", session.language, session.timezone, session.location)
                await websocket.send_text(json.dumps({
                    "type": "config_updated",
                    "language": session.language,
                    "timezone": session.timezone,
                    "location": session.location,
                }))
                continue

            # 3. PARTIAL TRANSCRIPT (User is actively speaking)
            elif msg_type == "transcript_partial":
                partial_text = msg.get("text", "").strip()
                session.touch()
                # If AI was speaking or generating, user speech triggers automatic barge-in!
                if session.status in ("speaking", "processing"):
                    logger.info("Automatic barge-in triggered by partial speech: '{}'", partial_text)
                    session.interrupt()
                    if current_worker_task and not current_worker_task.done():
                        current_worker_task.cancel()
                        current_worker_task = None
                    session.set_status("listening")
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "status": "listening",
                        "interrupted": True,
                    }))
                continue

            # 4. FINAL TRANSCRIPT (User finished speaking an utterance)
            elif msg_type == "transcript_final":
                final_text = msg.get("text", "").strip()
                if not final_text:
                    continue

                logger.info("Received final transcript: '{}'", final_text)

                # Cancel any prior running task
                if current_worker_task and not current_worker_task.done():
                    current_worker_task.cancel()

                # Launch generation task
                current_worker_task = asyncio.create_task(_run_utterance(final_text))
                session.current_task = current_worker_task
                continue

            # 5. AUDIO CHUNK FROM CLIENT (Binary / Base64 if streaming audio directly)
            elif msg_type == "audio_chunk":
                # For environments without browser Web Speech API
                # Pass through or decode if audio transcription is needed
                session.touch()
                continue

            # 6. SESSION END REQUEST
            elif msg_type == "session_end":
                logger.info("User requested session end for conv {}", conversation_id)
                if current_worker_task and not current_worker_task.done():
                    current_worker_task.cancel()
                session.set_status("stopped")
                await websocket.send_text(json.dumps({"type": "session_ended"}))
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for conv {}", conversation_id)
    except Exception as e:
        logger.error("Unexpected WebSocket error in session {}: {}", session.session_id, e)
    finally:
        if current_worker_task and not current_worker_task.done():
            current_worker_task.cancel()
        await live_session_manager.end_session(session.session_id)
