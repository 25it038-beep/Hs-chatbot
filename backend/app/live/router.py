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
    return {
        "status": "healthy",
        "subsystem": "live_voice",
        "provider": "nvidia",
        "models": {
            "asr": "parakeet-tdt-0.6b-en-US-asr-offline",
            "tts": "chatterbox-multilingual",
            "llm": "meta/llama-3.2-11b-vision-instruct",
        },
    }


@router.get("/voices")
async def live_voices():
    """Returns available voices supported by NVIDIA Riva TTS."""
    return {
        "voices": [
            {"id": "Chatterbox-Multilingual", "name": "Chatterbox Multilingual", "language": "en-US", "default": True},
            {"id": "English-US.Female-1", "name": "English US (Female)", "language": "en-US", "default": False},
            {"id": "English-US.Male-1", "name": "English US (Male)", "language": "en-US", "default": False},
        ]
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


@router.websocket("/ws/{session_id}")
@router.websocket("/ws")
async def websocket_live_endpoint(websocket: WebSocket, session_id: str = "default_live"):
    """
    WebSocket endpoint for bidirectional real-time audio and conversation streaming.
    Isolated completely to NVIDIA NIM backend services.
    """
    await websocket.accept()
    logger.info(f"Accepted Live Voice WebSocket connection: {session_id}")

    session = LiveVoiceSession(session_id, websocket)
    try:
        await session.start()
    except WebSocketDisconnect:
        logger.info(f"Live session {session_id} ended")
    except Exception as e:
        logger.error(f"Live session {session_id} encountered error: {e}")
    finally:
        await session.cleanup()
