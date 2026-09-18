"""
FastAPI Router for HSBot Live Voice Subsystem
Provides WebSocket and SSE HTTP streaming endpoints for isolated NVIDIA real-time voice conversations.
"""

import asyncio
import base64
import json
import logging
import re
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.live.session import LiveVoiceSession, SENTENCE_SPLIT_REGEX, CLAUSE_SPLIT_REGEX
from app.live.asr import live_asr
from app.live.tts import live_tts
from app.live.llm import live_llm

logger = logging.getLogger("hsbot.live.router")

router = APIRouter(prefix="/api/live", tags=["live"])

# In-memory history cache for HTTP live turns
http_sessions: Dict[str, Dict[str, Any]] = {}


class LiveTurnRequest(BaseModel):
    sessionId: str = "default"
    text: Optional[str] = None
    audioChunks: Optional[List[str]] = None
    voice: str = "Chatterbox-Multilingual"


class LiveConnectRequest(BaseModel):
    sessionId: str = "default"
    config: Optional[Dict[str, Any]] = None


@router.get("/health")
async def live_health():
    """Health check for isolated Live Voice subsystem."""
    from app.config import settings
    nvidia_key = getattr(settings, "nvidia_api_keys", "")
    has_nvidia = bool(nvidia_key and nvidia_key.strip())
    from app.live.tamil_provider import is_tamil_voice_available
    tamil_status = is_tamil_voice_available()
    return {
        "environment": getattr(settings, "app_env", "production"),
        "live_enabled": True,
        "nvidia_configured": has_nvidia,
        "asr_configured": has_nvidia,
        "llm_configured": has_nvidia,
        "tts_configured": has_nvidia,
        "websocket_enabled": True,
        "english_supported": True,
        "tamil_supported": bool(tamil_status["supported"]),
        "tamil_asr": "healthy" if tamil_status["supported"] else "unconfigured",
        "tamil_tts": "healthy" if tamil_status["supported"] else "unconfigured",
        "status": "healthy",
        "subsystem": "live_voice",
        "provider": "nvidia",
        "models": {
            "asr": "parakeet-tdt-0.6b-en-US-asr-offline",
            "tts": "chatterbox-multilingual",
            "llm": "meta/llama-3.2-11b-vision-instruct",
        },
    }


@router.get("/tamil/health")
async def live_tamil_health():
    """Returns NVIDIA Riva Tamil speech provider health status."""
    from app.live.tamil_provider import tamil_riva_provider
    return await tamil_riva_provider.health()


@router.get("/languages")
async def live_languages():
    """Returns supported languages and honest availability status for Live Voice."""
    from app.live.tamil_provider import is_tamil_voice_available
    tamil_status = is_tamil_voice_available()
    return {
        "default": "en",
        "languages": [
            {
                "code": "en",
                "name": "English",
                "native_name": "English",
                "label": "English",
                "supported": True,
                "default": True,
                "voice": "Chatterbox-Multilingual",
                "asr_model": "parakeet-tdt-0.6b-en-US-asr-offline",
            },
            {
                "code": "ta",
                "name": "Tamil",
                "native_name": "தமிழ்",
                "label": "தமிழ்",
                "supported": bool(tamil_status["supported"]),
                "default": False,
                "reason": tamil_status.get("reason"),
                "voice": tamil_status.get("tts_voice", "ta-IN-Standard"),
                "asr_model": tamil_status.get("asr_model", "whisper-large-v3"),
            },
        ],
    }


@router.get("/voices")
async def live_voices(language: Optional[str] = None):
    """Returns available voices supported by Live Voice providers."""
    if language and language.lower() in ("ta", "ta-in", "tamil"):
        return {
            "language": "ta",
            "voices": [
                {"id": "ta-IN-Standard", "name": "Tamil Natural", "language": "ta-IN", "default": True},
                {"id": "ta-IN-Female", "name": "Tamil Female", "language": "ta-IN", "default": False},
                {"id": "ta-IN-Male", "name": "Tamil Male", "language": "ta-IN", "default": False},
            ],
        }
    return {
        "language": "en",
        "voices": [
            {"id": "Chatterbox-Multilingual", "name": "Chatterbox Multilingual", "language": "en-US", "default": True},
            {"id": "English-US.Female-1", "name": "English US (Female - FastPitch)", "language": "en-US", "default": False},
            {"id": "English-US.Male-1", "name": "English US (Male)", "language": "en-US", "default": False},
        ],
    }


@router.post("/session/connect")
async def live_session_connect(req: LiveConnectRequest):
    """Registers session configuration for HTTP mode."""
    http_sessions[req.sessionId] = {
        "config": req.config or {},
        "history": [],
    }
    return {"status": "connected", "sessionId": req.sessionId}


@router.post("/turn")
async def live_turn_sse(req: LiveTurnRequest):
    """
    Executes a single live conversation turn over Server-Sent Events (SSE)
    with the exact same streaming LLM and TTS pipeline for HTTP fallback mode.
    """
    session_data = http_sessions.setdefault(req.sessionId, {"history": [], "config": {}})
    history = session_data["history"]

    async def sse_event_stream():
        t_asr_final = time.time()
        user_text = req.text

        # 1. ASR if audio chunks passed
        if not user_text and req.audioChunks:
            yield f"data: {json.dumps({'type': 'status', 'state': 'PROCESSING', 'message': 'Transcribing speech...'})}\n\n"
            pcm_bytes = bytearray()
            for chunk_b64 in req.audioChunks:
                try:
                    pcm_bytes.extend(base64.b64decode(chunk_b64))
                except Exception:
                    pass
            if pcm_bytes:
                t0 = time.time()
                user_text = await live_asr.transcribe_pcm(bytes(pcm_bytes), sample_rate=16000)
                logger.info(f"[LIVE][HTTP][TIMING] ASR took {(time.time() - t0)*1000:.1f}ms: '{user_text}'")

        if not user_text or not user_text.strip():
            yield f"data: {json.dumps({'type': 'status', 'state': 'LISTENING', 'message': 'No speech detected'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        clean_user_text = user_text.strip()
        t_asr_final = time.time()

        yield f"data: {json.dumps({'type': 'transcript', 'role': 'user', 'text': clean_user_text, 'isFinal': True})}\n\n"
        history.append({"role": "user", "content": clean_user_text})

        yield f"data: {json.dumps({'type': 'status', 'state': 'PROCESSING', 'message': 'Thinking (NVIDIA LLM)...'})}\n\n"

        # 2. Overlapped LLM + TTS pipeline
        tts_queue = asyncio.Queue()
        t_llm_first = 0.0
        full_reply = ""
        token_buffer = ""
        first_token = False

        async def tts_worker():
            nonlocal t_llm_first
            chunk_idx = 0
            first_audio = False
            while True:
                phrase = await tts_queue.get()
                if phrase is None:
                    break
                async for pcm in live_tts.stream_synthesize(phrase, voice=req.voice):
                    if not pcm:
                        continue
                    if not first_audio:
                        first_audio = True
                        t_first_audio = time.time()
                        ttft_to_audio = (t_first_audio - t_llm_first) * 1000 if t_llm_first else 0.0
                        total_lat = (t_first_audio - t_asr_final) * 1000
                        yield f"data: {json.dumps({'type': 'status', 'state': 'SPEAKING', 'message': 'Speaking...'})}\n\n"
                        yield f"data: {json.dumps({'type': 'timing', 'metric': 'llm_first_token_to_tts_first_audio_ms', 'value': round(ttft_to_audio, 1)})}\n\n"
                        yield f"data: {json.dumps({'type': 'timing', 'metric': 'total_latency_ms', 'value': round(total_lat, 1)})}\n\n"

                    yield f"data: {json.dumps({'type': 'audio_chunk', 'audio': base64.b64encode(pcm).decode('ascii'), 'sampleRate': 24000, 'index': chunk_idx})}\n\n"
                    chunk_idx += 1

        # We stream LLM and synthesize phrases sequentially or concurrently
        # In generator, we can synthesize ready sentences
        async for token in live_llm.stream_reply(clean_user_text, history):
            if not first_token:
                first_token = True
                t_llm_first = time.time()
                asr_to_llm = (t_llm_first - t_asr_final) * 1000
                yield f"data: {json.dumps({'type': 'timing', 'metric': 'asr_to_llm_first_token_ms', 'value': round(asr_to_llm, 1)})}\n\n"

            full_reply += token
            token_buffer += token
            yield f"data: {json.dumps({'type': 'llm_chunk', 'text': token})}\n\n"

            # Check sentence break
            s_match = SENTENCE_SPLIT_REGEX.match(token_buffer)
            if s_match:
                ready_sentence = s_match.group(1).strip()
                token_buffer = s_match.group(2) or ""
                if len(ready_sentence) >= 2:
                    async for pcm in live_tts.stream_synthesize(ready_sentence, voice=req.voice):
                        if pcm:
                            yield f"data: {json.dumps({'type': 'audio_chunk', 'audio': base64.b64encode(pcm).decode('ascii'), 'sampleRate': 24000})}\n\n"

        # Flush rest
        if token_buffer.strip():
            async for pcm in live_tts.stream_synthesize(token_buffer.strip(), voice=req.voice):
                if pcm:
                    yield f"data: {json.dumps({'type': 'audio_chunk', 'audio': base64.b64encode(pcm).decode('ascii'), 'sampleRate': 24000})}\n\n"

        if full_reply:
            history.append({"role": "assistant", "content": full_reply.strip()})
            yield f"data: {json.dumps({'type': 'transcript', 'role': 'assistant', 'text': full_reply.strip(), 'isFinal': True})}\n\n"

        yield f"data: {json.dumps({'type': 'status', 'state': 'LISTENING', 'message': 'Ready'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_event_stream(), media_type="text/event-stream")


from app.live.websocket import handle_live_websocket
from app.live.diagnostics import live_diagnostics


@router.get("/diagnostics")
async def get_live_diagnostics():
    """Returns detailed real-time 14-point diagnostic snapshot for Live Voice."""
    return await live_diagnostics.get_snapshot()


@router.get("/engine")
async def get_live_engine():
    """Returns active and default Live Voice engine."""
    return {
        "engine": live_diagnostics.get_engine(),
        "default": getattr(settings, "live_engine", "nemotron_voicechat"),
        "supported": ["nemotron_voicechat", "cascaded"],
    }


class EngineUpdateRequest(BaseModel):
    engine: str


@router.post("/engine")
async def set_live_engine(req: EngineUpdateRequest):
    """Sets active Live Voice engine (nemotron_voicechat or cascaded)."""
    if req.engine not in ["nemotron_voicechat", "cascaded"]:
        return {"status": "error", "message": "Supported engines are 'nemotron_voicechat' and 'cascaded'"}
    live_diagnostics.set_engine(req.engine)
    return {"status": "ok", "engine": req.engine}


@router.websocket("/ws/{session_id}")
@router.websocket("/ws")
async def websocket_live_endpoint(websocket: WebSocket, session_id: str = "default_live", engine: Optional[str] = None):
    """
    WebSocket endpoint for bidirectional real-time audio and conversation streaming.
    Dispatches to app.live.websocket.handle_live_websocket with Nemotron / Cascaded routing.
    """
    await handle_live_websocket(websocket=websocket, session_id=session_id, requested_engine=engine)

