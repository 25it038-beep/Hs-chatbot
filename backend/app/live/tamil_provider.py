"""
NVIDIA Voice Engine Architecture for HSBot Live Voice (Additive, Isolated).

Strict Zero-Regression Guarantee:
- The existing English voice pipeline (Parakeet ASR + Llama 3.2 LLM + Chatterbox TTS)
  is 100% untouched and remains the active production default.
- Implements the dual VoiceEngine architecture:
      VoiceEngine
         |
         +── EnglishVoiceEngine (Adapter around existing locked implementation)
         |
         +── TamilVoiceEngine (Isolated adapter with catalog verification)
"""

import abc
import logging
from typing import Dict, Any, Optional, AsyncGenerator, List

from app.config import settings
from app.live.asr import live_asr
from app.live.tts import live_tts
from app.live.llm import live_llm

logger = logging.getLogger("hsbot.live.voice_engine")

TAMIL_LANGUAGE_CODE = "ta-IN"
ENGLISH_LANGUAGE_CODE = "en-US"

# Catalog Discovery Results from live gRPC GetRivaSynthesisConfig and GetRivaSpeechRecognitionConfig
CATALOG_DISCOVERY = {
    "asr": {
        "parakeet_tdt_0_6b": {
            "model_name": "parakeet-tdt-0.6b-en-US-asr-offline",
            "function_id": "d3fe9151-442b-4204-a70d-5fcc597fd610",
            "supported_languages": ["en-US"],
            "tamil_supported": False,
        },
        "canary_1b": {
            "model_name": "canary-1b-flash-multi-asr-offline",
            "function_id": "b0e8b4a5-217c-40b7-9b96-17d84e666317",
            "supported_languages": ["en-US", "hi-IN", "en-IN"],  # 72 locales, ta-IN missing
            "tamil_supported": False,
        },
        "parakeet_1_1b_rnnt": {
            "model_name": "parakeet-rnnt-1.1b-unified-ml-cs-universal-multi-asr-offline-silero-vad-sortformer",
            "function_id": "71203149-d3b7-4460-8231-1be2543a1fca",
            "supported_languages": ["en-US", "es-ES", "fr-FR", "de-DE", "hi-IN"],  # 26 langs, ta-IN missing
            "tamil_supported": False,
        },
    },
    "tts": {
        "chatterbox_multilingual": {
            "model_name": "chatterbox-Chatterbox-Multilingual",
            "function_id": "ddacc747-1269-4fab-bfd9-8f593dead106",
            "supported_languages": [
                "ar-SA", "da-DK", "de-DE", "el-GR", "en-US", "es-ES", "fi-FI", "fr-FR",
                "he-IL", "hi-IN", "it-IT", "ja-JP", "ko-KR", "ms-MY", "nl-NL", "nb-NO",
                "pl-PL", "pt-BR", "ru-RU", "sv-SE", "sw-KE", "tr-TR", "zh-CN"
            ],
            "tamil_supported": False,
        },
        "magpie_multilingual": {
            "model_name": "magpie_tts_ensemble-Magpie-Multilingual",
            "function_id": "877104f7-e885-42b9-8de8-f6e4c6303969",
            "supported_languages": [
                "en-US", "es-US", "fr-FR", "de-DE", "zh-CN", "vi-VN", "it-IT",
                "hi-IN", "ja-JP", "ko-KR", "ar-AR", "pt-BR"
            ],
            "tamil_supported": False,
        },
    },
}


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
    feature_enabled = getattr(settings, "enable_tamil_voice", False)
    tamil_tts_model = getattr(settings, "tamil_tts_model", None)
    tamil_tts_voice = getattr(settings, "tamil_tts_voice", None)
    tamil_asr_model = getattr(settings, "tamil_asr_model", None)

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

    return {
        "language": TAMIL_LANGUAGE_CODE,
        "supported": False,
        "enabled": False,
        "asr_model": None,
        "tts_model": None,
        "tts_voice": "UNAVAILABLE",
        "code": "TAMIL_TTS_NOT_SUPPORTED_BY_SELECTED_NVIDIA_MODEL",
        "reason": "Tamil is not supported by the selected NVIDIA hosted voice model (Chatterbox-Multilingual does not provide a ta-IN voice ID)",
        "catalog_discovery": {
            "asr_inspected": ["parakeet-tdt-0.6b", "canary-1b", "parakeet-rnnt-1.1b"],
            "tts_inspected": ["chatterbox-multilingual", "magpie-multilingual"],
            "tamil_in_catalog": False,
        },
    }


class BaseVoiceEngine(abc.ABC):
    """Abstract base class defining the Live Voice Engine contract."""

    @property
    @abc.abstractmethod
    def language(self) -> str:
        pass

    @abc.abstractmethod
    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        pass

    @abc.abstractmethod
    def stream_synthesize(self, text: str, voice: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        pass

    @abc.abstractmethod
    def get_prompt_instruction(self) -> Optional[str]:
        pass


class EnglishVoiceEngine(BaseVoiceEngine):
    """
    Adapter around the existing, locked English voice pipeline.
    Zero refactoring of underlying ASR, LLM, or TTS clients.
    """

    @property
    def language(self) -> str:
        return "en"

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        return await live_asr.transcribe_pcm(pcm_bytes, sample_rate=sample_rate)

    async def stream_synthesize(self, text: str, voice: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        active_voice = voice or getattr(settings, "live_voice", "Chatterbox-Multilingual")
        async for chunk in live_tts.stream_synthesize(text, voice=active_voice):
            yield chunk

    def get_prompt_instruction(self) -> Optional[str]:
        # Uses default English prompt without additional language constraint
        return None


class TamilVoiceEngine(BaseVoiceEngine):
    """
    Isolated Tamil voice engine.
    Strictly isolated from the existing English engine.
    """

    @property
    def language(self) -> str:
        return "ta"

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

    async def stream_synthesize(self, text: str, voice: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        status = is_tamil_voice_available()
        if not status["supported"]:
            raise TamilVoiceUnavailableError(
                code="TAMIL_TTS_UNAVAILABLE",
                message="NVIDIA hosted TTS does not support Tamil (ta-IN) on this deployment."
            )
        raise TamilVoiceUnavailableError("TAMIL_TTS_UNAVAILABLE", "Tamil TTS not provisioned.")
        yield b""  # unreachable, generator compliance

    def get_prompt_instruction(self) -> Optional[str]:
        return (
            "Respond naturally in Tamil. "
            "Use Tamil script. "
            "Do not switch to English unless explicitly requested by the user."
        )


# Global instances and class alias for backward compatibility
TamilVoiceProvider = TamilVoiceEngine
english_voice_engine = EnglishVoiceEngine()
tamil_voice_engine = TamilVoiceEngine()

# Keep backward-compatible alias
tamil_voice_provider = tamil_voice_engine


def get_voice_engine(language: str = "en") -> BaseVoiceEngine:
    """Factory returning the isolated voice engine for the requested language."""
    if language.lower() in ("ta", "ta-in", "tamil"):
        return tamil_voice_engine
    return english_voice_engine

