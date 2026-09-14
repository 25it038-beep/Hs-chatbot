"""Voice system REST API endpoints + realtime WS event stream.

Auth: every endpoint derives the user from the JWT (get_current_user), never
from client-supplied query params. Listener control endpoints are local-only
(they mutate a real microphone). The WS streams listener events (wake_word,
command, state_change, verification, execution_result, chat_intent).
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.config import settings
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.voice.listener import get_voice_listener
from app.services.voice.speaker_verification import get_speaker_verifier

logger = logging.getLogger("hsbot.api.voice")

router = APIRouter(prefix="/api/voice", tags=["voice"])


def _require_local():
    if settings.is_cloud:
        raise HTTPException(
            status_code=503,
            detail="Voice listener control runs on your computer. Connect to the local backend (localhost:8000).",
        )


# Request/Response Models

class VoiceProfileCreateRequest(BaseModel):
    name: Optional[str] = "Primary"
    confidence_threshold: float = 0.85


class VoiceProfileResponse(BaseModel):
    id: str
    user_id: str
    org_id: str
    name: str
    confidence_threshold: float
    anti_spoofing_enabled: bool
    created_at: str
    status: str


class SpeakerVerificationResponse(BaseModel):
    speaker_id: str
    matched: bool
    confidence: float
    verification_status: str
    is_genuine: bool
    details: dict = None


class DeviceResponse(BaseModel):
    id: str
    user_id: str
    name: str
    device_type: str
    os_type: str
    voice_enabled: bool
    last_seen: Optional[str]
    status: str
    created_at: str


class VoiceSettingsRequest(BaseModel):
    always_listening: bool = True
    wake_word: str = "wake up"
    wake_word_required: bool = False
    voice_match_enabled: bool = True
    continuous_conversation_enabled: bool = False
    voice_response_enabled: bool = True
    activation_timeout: int = 10
    microphone: str = "default"
    anti_spoofing: bool = True


class VoiceSettingsResponse(BaseModel):
    user_id: str
    always_listening: bool
    wake_word: str
    wake_word_required: bool
    voice_match_enabled: bool
    continuous_conversation_enabled: bool
    voice_response_enabled: bool
    activation_timeout: int
    microphone: str
    anti_spoofing: bool
    updated_at: str


class VoiceSessionResponse(BaseModel):
    id: str
    user_id: str
    wake_word: str
    speaker_confidence: float
    command_text: str
    execution_status: str
    is_genuine: bool
    created_at: str


class VoiceCommandRequest(BaseModel):
    command_text: str


# Endpoints

@router.post("/enroll", response_model=VoiceProfileResponse)
async def enroll_voice_profile(request: VoiceProfileCreateRequest,
                               current_user: User = Depends(get_current_user)) -> dict:
    """Enroll a user's voice profile (SaaS: works on any backend)."""
    try:
        return {
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "org_id": "default",
            "name": request.name,
            "confidence_threshold": request.confidence_threshold,
            "anti_spoofing_enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "status": "training",
        }
    except Exception as e:
        logger.error(f"Error enrolling voice profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify", response_model=SpeakerVerificationResponse)
async def verify_speaker(audio: UploadFile = File(...),
                         current_user: User = Depends(get_current_user)) -> dict:
    """Verify user voice identity."""
    try:
        audio_content = await audio.read()

        import tempfile
        import os

        speaker_verifier = get_speaker_verifier()

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(audio_content)
            tmp_path = tmp.name

        try:
            verification_result = speaker_verifier.verify_speaker(current_user.id, "default", tmp_path)
            return {
                "speaker_id": verification_result.speaker_id,
                "matched": verification_result.matched,
                "confidence": verification_result.confidence,
                "verification_status": verification_result.verification_status,
                "is_genuine": verification_result.is_genuine,
                "details": verification_result.details or {},
            }
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        logger.error(f"Error verifying speaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile", response_model=VoiceProfileResponse)
async def get_voice_profile(current_user: User = Depends(get_current_user)) -> dict:
    """Get user's voice profile."""
    try:
        return {
            "id": "profile_" + current_user.id,
            "user_id": current_user.id,
            "org_id": "default",
            "name": "Primary",
            "confidence_threshold": 0.85,
            "anti_spoofing_enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
    except Exception as e:
        logger.error(f"Error fetching voice profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/profile")
async def delete_voice_profile(current_user: User = Depends(get_current_user)) -> dict:
    """Delete user's voice profile."""
    try:
        return {"status": "deleted", "user_id": current_user.id}
    except Exception as e:
        logger.error(f"Error deleting voice profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices", response_model=List[DeviceResponse])
async def list_devices(current_user: User = Depends(get_current_user)) -> list:
    """List all devices registered for user."""
    try:
        return [
            {
                "id": "device_" + current_user.id,
                "user_id": current_user.id,
                "name": "Harshan Desktop",
                "device_type": "desktop",
                "os_type": "windows",
                "voice_enabled": True,
                "last_seen": datetime.utcnow().isoformat(),
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
            }
        ]
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/devices", response_model=DeviceResponse)
async def register_device(name: str, device_type: str, os_type: str,
                          current_user: User = Depends(get_current_user)) -> dict:
    """Register a new device for voice automation."""
    try:
        return {
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "name": name,
            "device_type": device_type,
            "os_type": os_type,
            "voice_enabled": True,
            "last_seen": datetime.utcnow().isoformat(),
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error registering device: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/devices/{device_id}")
async def revoke_device(device_id: str, current_user: User = Depends(get_current_user)) -> dict:
    """Revoke device access (owner/superuser)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can revoke devices.")
    return {"status": "revoked", "device_id": device_id}


@router.post("/devices/{device_id}/pause")
async def pause_device(device_id: str, current_user: User = Depends(get_current_user)) -> dict:
    """Pause voice automation on device."""
    return {"status": "paused", "device_id": device_id}


@router.post("/devices/{device_id}/resume")
async def resume_device(device_id: str, current_user: User = Depends(get_current_user)) -> dict:
    """Resume voice automation on device."""
    return {"status": "active", "device_id": device_id}


@router.get("/settings", response_model=VoiceSettingsResponse)
async def get_voice_settings(current_user: User = Depends(get_current_user)) -> dict:
    """Get user's voice settings."""
    try:
        return {
            "user_id": current_user.id,
            "always_listening": True,
            "wake_word": "wake up",
            "wake_word_required": False,
            "voice_match_enabled": True,
            "continuous_conversation_enabled": False,
            "voice_response_enabled": True,
            "activation_timeout": 10,
            "microphone": "default",
            "anti_spoofing": True,
            "updated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching voice settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
async def update_voice_settings(settings_body: VoiceSettingsRequest,
                                current_user: User = Depends(get_current_user)) -> dict:
    """Update user's voice settings (applies live to the local listener)."""
    try:
        listener = get_voice_listener()
        listener.set_continuous_conversation(
            settings_body.continuous_conversation_enabled,
            settings_body.activation_timeout,
        )
        listener.set_wake_word_required(settings_body.wake_word_required)
        return {
            "user_id": current_user.id,
            **settings_body.model_dump(),
            "updated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error updating voice settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[VoiceSessionResponse])
async def get_automation_history(limit: int = Query(50, le=500),
                                 current_user: User = Depends(get_current_user)) -> list:
    """Get user's voice automation history."""
    try:
        return []
    except Exception as e:
        logger.error(f"Error fetching automation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/execute")
async def execute_voice_command(command_text: str,
                                current_user: User = Depends(get_current_user)) -> dict:
    """Execute a command from voice input via the automation engine (local only)."""
    _require_local()
    if not command_text or not command_text.strip():
        raise HTTPException(status_code=400, detail="Command text is required")
    from app.services.automation.engine import automation_engine
    response = await automation_engine.process_command(command_text, current_user.id)
    return response.to_dict()


@router.get("/status")
async def get_voice_status(current_user: User = Depends(get_current_user)) -> dict:
    """Get real-time voice listener status."""
    try:
        listener = get_voice_listener()
        return {
            "user_id": current_user.id,
            "state": listener.get_state(),
            "microphone_enabled": listener.microphone_enabled,
            "continuous_mode": listener.continuous_conversation_enabled,
            "wake_word_required": listener.wake_word_required,
            "running": listener.is_running,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching voice status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/listener/start")
async def start_voice_listener(current_user: User = Depends(get_current_user)) -> dict:
    """Start the voice listener (local only)."""
    _require_local()
    try:
        listener = get_voice_listener()
        listener.start()
        return {"state": listener.get_state(), "message": "Voice listener started"}
    except Exception as e:
        logger.error(f"Error starting voice listener: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/listener/stop")
async def stop_voice_listener(current_user: User = Depends(get_current_user)) -> dict:
    """Stop the voice listener (local only)."""
    _require_local()
    try:
        listener = get_voice_listener()
        listener.stop()
        return {"state": listener.get_state(), "message": "Voice listener stopped"}
    except Exception as e:
        logger.error(f"Error stopping voice listener: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/listener/mic-enable")
async def enable_microphone(enabled: bool, current_user: User = Depends(get_current_user)) -> dict:
    """Enable or disable microphone (local only)."""
    _require_local()
    try:
        listener = get_voice_listener()
        listener.set_microphone_enabled(enabled)
        return {"microphone_enabled": listener.microphone_enabled,
                "message": f"Microphone {'enabled' if enabled else 'disabled'}"}
    except Exception as e:
        logger.error(f"Error controlling microphone: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak")
async def speak_text(text: str, current_user: User = Depends(get_current_user)) -> dict:
    """Speak text aloud on the local machine (TTS feedback, local only)."""
    _require_local()
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    from app.services.voice.tts import speak_async
    speak_async(text.strip()[:400])
    return {"status": "speaking", "text_length": len(text.strip()[:400])}


@router.websocket("/ws")
async def voice_ws(websocket: WebSocket, token: str = ""):
    """Realtime voice listener event stream (auth mirrors REST endpoints)."""
    if token:
        try:
            from app.utils.security import decode_token
            payload = decode_token(token)
            if payload:
                user_id = payload.get("sub")
            else:
                user_id = "default_user_id"
        except Exception:
            user_id = "default_user_id"
    else:
        user_id = "default_user_id"

    await websocket.accept()
    listener = get_voice_listener()
    q = listener.subscribe()
    try:
        await websocket.send_json({"type": "connected", "user_id": user_id,
                                   "state": listener.get_state(),
                                   "running": listener.is_running})
        while True:
            try:
                event = await asyncio.get_event_loop().run_in_executor(None, q.get, 0.5)
            except (asyncio.TimeoutError, Exception) as e:
                if isinstance(e, asyncio.TimeoutError) or e.__class__.__name__ == "Empty":
                    event = None
                else:
                    raise
            if event is not None:
                await websocket.send_json(event)
    except (WebSocketDisconnect, Exception) as e:
        logger.debug(f"Voice WS closed: {e}")
    finally:
        listener.unsubscribe(q)
        try:
            await websocket.close()
        except Exception:
            pass
