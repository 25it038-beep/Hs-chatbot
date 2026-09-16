"""
FastAPI Router for HSBot Live Voice Subsystem
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.live.session import LiveVoiceSession

logger = logging.getLogger("hsbot.live.router")

router = APIRouter(prefix="/api/live", tags=["live"])


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


@router.websocket("/ws/{session_id}")
async def websocket_live_endpoint(websocket: WebSocket, session_id: str):
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
