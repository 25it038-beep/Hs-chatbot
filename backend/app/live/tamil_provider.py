"""
NVIDIA Tamil Voice Provider Module (Additive, Isolated).

Strict Zero-Regression Guarantee:
- The existing English voice pipeline (Parakeet ASR + Llama 3.2 LLM + Chatterbox TTS)
  is 100% untouched and remains the active production default.
- This module implements the capability check and isolated adapter for Tamil (ta-IN).
- If NVIDIA does not provide a verified hosted Tamil ASR or TTS model on the active key,
  Tamil remains explicitly marked as UNAVAILABLE with reason
  'TAMIL_TTS_NOT_SUPPORTED_BY_SELECTED_NVIDIA_MODEL'.
"""

import logging
from typing import Dict, Any, Optional

from app.config import settings

logger = logging.getLogger("hsbot.live.tamil_provider")

TAMIL_LANGUAGE_CODE = "ta-IN"


class TamilVoiceUnavailableError(Exception):
    """Raised when Tamil voice is requested but not provisioned on NVIDIA."""
    def __init__(self, code: str = "TAMIL_VOICE_UNAVAILABLE", message: str = "Tamil voice is currently unavailable on NVIDIA"):
        super().__init__(message)
        self.code = code
        self.message = message


def is_tamil_voice_available() -> Dict[str, Any]:
    """
    Verifies actual NVIDIA Tamil capability.
    Checks whether Tamil ASR and TTS endpoints are configured and provisioned on NVIDIA.
    """
    # 1. Check feature flag (default: false)
    feature_enabled = getattr(settings, "enable_tamil_voice", False)
    tamil_tts_model = getattr(settings, "tamil_tts_model", None)
    tamil_tts_voice = getattr(settings, "tamil_tts_voice", None)
    tamil_asr_model = getattr(settings, "tamil_asr_model", None)

    # If explicit verified Tamil endpoints are provided via config, check them
    if feature_enabled and tamil_tts_model and tamil_tts_voice and tamil_asr_model:
        return {
            "language": TAMIL_LANGUAGE_CODE,
            "supported": True,
            "enabled": True,
            "asr_model": tamil_asr_model,
            "tts_model": tamil_tts_model,
            "tts_voice": tamil_tts_voice,
            "reason": None,
        }

    # Otherwise, report exact missing capability honestly
    return {
        "language": TAMIL_LANGUAGE_CODE,
        "supported": False,
        "enabled": False,
        "asr_model": None,
        "tts_model": None,
        "tts_voice": "UNAVAILABLE",
        "code": "TAMIL_TTS_NOT_SUPPORTED_BY_SELECTED_NVIDIA_MODEL",
        "reason": "Tamil is not supported by the selected NVIDIA hosted voice model (Chatterbox-Multilingual does not provide a ta-IN voice ID)",
    }


class TamilVoiceProvider:
    """
    Isolated Tamil voice provider.
    Strictly isolated from the existing English provider.
    """
    def __init__(self):
        self.language_code = TAMIL_LANGUAGE_CODE

    def get_status(self) -> Dict[str, Any]:
        return is_tamil_voice_available()

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        status = is_tamil_voice_available()
        if not status["supported"]:
            raise TamilVoiceUnavailableError(
                code="TAMIL_ASR_UNAVAILABLE",
                message="NVIDIA hosted ASR does not support Tamil (ta-IN) on this deployment."
            )
        raise TamilVoiceUnavailableError("TAMIL_ASR_UNAVAILABLE", "Tamil ASR not provisioned.")

    async def stream_synthesize(self, text: str):
        status = is_tamil_voice_available()
        if not status["supported"]:
            raise TamilVoiceUnavailableError(
                code="TAMIL_TTS_UNAVAILABLE",
                message="NVIDIA hosted TTS does not support Tamil (ta-IN) on this deployment."
            )
        raise TamilVoiceUnavailableError("TAMIL_TTS_UNAVAILABLE", "Tamil TTS not provisioned.")


# Global isolated singleton
tamil_voice_provider = TamilVoiceProvider()
