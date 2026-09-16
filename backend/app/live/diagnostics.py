"""
HSBot Live Voice Diagnostics & Telemetry Module.
Instruments real-time latency, engine health, model availability, and session metrics.
"""

import time
from typing import Dict, Any, List, Optional
from app.live.voicechat import nemotron_voicechat
from app.config import settings


class LiveVoiceDiagnostics:
    """Collects and reports real-time telemetry for HSBot Live Voice."""

    def __init__(self):
        self._active_sessions = 0
        self._total_turns = 0
        self._last_turn_metrics: Dict[str, float] = {}
        self._recent_errors: List[Dict[str, Any]] = []
        self._current_engine = getattr(settings, "live_engine", "cascaded")

    def register_session_connect(self):
        self._active_sessions += 1

    def register_session_disconnect(self):
        if self._active_sessions > 0:
            self._active_sessions -= 1

    def set_engine(self, engine: str):
        self._current_engine = engine

    def get_engine(self) -> str:
        return self._current_engine

    def record_turn(self, metrics: Dict[str, float]):
        self._total_turns += 1
        self._last_turn_metrics = metrics

    def record_error(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self._recent_errors.append({
            "timestamp": time.time(),
            "code": code,
            "message": message,
            "details": details or {},
        })
        if len(self._recent_errors) > 20:
            self._recent_errors.pop(0)

    async def get_snapshot(self) -> Dict[str, Any]:
        """Returns structured 14-point diagnostic snapshot for observability."""
        nemotron_status = await nemotron_voicechat.check_availability()

        return {
            "status": "healthy" if (self._current_engine == "cascaded" or nemotron_status.get("available")) else "degraded",
            "timestamp": time.time(),
            "engine": {
                "active": self._current_engine,
                "default": getattr(settings, "live_engine", "cascaded"),
                "supported": ["nemotron_voicechat", "cascaded"],
            },
            "models": {
                "nemotron_voicechat": {
                    "model_id": getattr(settings, "nvidia_voicechat_model", "nvidia/nemotron-voicechat"),
                    "available": nemotron_status.get("available", False),
                    "code": nemotron_status.get("code"),
                    "status_code": nemotron_status.get("status_code"),
                    "reason": nemotron_status.get("reason"),
                    "detail": nemotron_status.get("detail"),
                },
                "cascaded": {
                    "asr": "parakeet-tdt-0.6b-en-US-asr-offline",
                    "llm": getattr(settings, "nvidia_default_chat_model", "llama-3.2-11b"),
                    "tts": "chatterbox-multilingual",
                    "available": True,
                }
            },
            "sessions": {
                "active": self._active_sessions,
                "total_turns": self._total_turns,
            },
            "latencies": self._last_turn_metrics,
            "recent_errors": self._recent_errors[-5:],
        }


live_diagnostics = LiveVoiceDiagnostics()
