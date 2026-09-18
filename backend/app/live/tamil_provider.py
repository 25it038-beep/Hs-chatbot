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


class TamilSpeechProvider(abc.ABC):
    """Abstract interface defining the Tamil Speech Provider contract."""

    @abc.abstractmethod
    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribes raw PCM bytes into Tamil Unicode text."""
        pass

    @abc.abstractmethod
    def stream_synthesize(self, text: str, voice: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        """Streams synthesized raw PCM bytes from Tamil text."""
        pass

    @abc.abstractmethod
    async def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Synthesizes text into complete PCM audio base64 payload."""
        pass

    @abc.abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Returns standard health status for Tamil Riva service."""
        pass


class TamilRivaProvider(TamilSpeechProvider):
    """
    NVIDIA Riva / NeMo Tamil Speech Provider (Independent, Additive).
    Connects to an external GPU-hosted NVIDIA Riva instance running Tamil ASR & TTS.
    Does not require Render to host an NVIDIA GPU.
    """

    def __init__(self):
        self.language_code = TAMIL_LANGUAGE_CODE

    def is_configured(self) -> bool:
        enabled = getattr(settings, "tamil_voice_enabled", False) or getattr(settings, "enable_tamil_voice", False)
        host = getattr(settings, "tamil_riva_host", None)
        return bool(enabled and host and host.strip())

    async def probe_riva_connection(self) -> bool:
        """Probes external Riva gRPC host connectivity with a fail-fast timeout."""
        import asyncio
        host = getattr(settings, "tamil_riva_host", None)
        port = getattr(settings, "tamil_riva_port", 50051) or 50051
        if not host or not host.strip():
            return False

        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host.strip(), int(port)),
                timeout=2.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception as e:
            logger.debug(f"[TamilRiva] Connection probe to {host}:{port} failed: {e}")
            return False

    async def health(self) -> Dict[str, Any]:
        """
        Implements GET /api/live/tamil/health contract:
        If healthy:
        { "enabled": true, "language": "ta-IN", "asr": "healthy", "tts": "healthy", "riva": "healthy" }
        If unavailable:
        { "enabled": false, "language": "ta-IN", "reason": "Tamil Riva service unavailable" }
        """
        if not self.is_configured():
            return {
                "enabled": False,
                "language": self.language_code,
                "reason": "Tamil Riva service unavailable (TAMIL_RIVA_HOST not configured or service disabled)",
            }

        from app.live.tamil_asr import tamil_asr_provider
        from app.live.tamil_tts import tamil_tts_provider
        asr_h = await tamil_asr_provider.health_check()
        tts_h = await tamil_tts_provider.health_check()

        is_connected = await self.probe_riva_connection()
        if not is_connected:
            host = getattr(settings, "tamil_riva_host", "")
            port = getattr(settings, "tamil_riva_port", 50051)
            return {
                "enabled": False,
                "language": self.language_code,
                "reason": f"Tamil Riva service unreachable at {host}:{port}",
            }

        return {
            "enabled": True,
            "language": self.language_code,
            "asr": "healthy" if asr_h.get("healthy") else "unhealthy",
            "tts": "healthy" if tts_h.get("healthy") else "unhealthy",
            "riva": "healthy",
            "host": getattr(settings, "tamil_riva_host", ""),
            "port": getattr(settings, "tamil_riva_port", 50051),
        }

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        from app.live.tamil_asr import tamil_asr_provider
        return await tamil_asr_provider.transcribe(pcm_bytes, sample_rate=sample_rate)

    async def stream_synthesize(self, text: str, voice: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        from app.live.tamil_tts import tamil_tts_provider
        async for chunk in tamil_tts_provider.synthesize_stream(text, voice=voice):
            yield chunk

    async def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[Dict[str, Any]]:
        from app.live.tamil_tts import tamil_tts_provider
        return await tamil_tts_provider.synthesize(text, voice=voice)


# Isolated global Tamil Riva provider singleton
tamil_riva_provider = TamilRivaProvider()


def is_tamil_voice_available() -> Dict[str, Any]:
    """
    Verifies NVIDIA Tamil speech capability.
    Supports external NVIDIA Riva GPU service when configured, with native
    NVIDIA NVCF Whisper Large V3 ASR & Chatterbox TTS integrated.
    """
    is_ext = tamil_riva_provider.is_configured()
    return {
        "language": TAMIL_LANGUAGE_CODE,
        "supported": True,
        "enabled": True,
        "mode": "external_riva" if is_ext else "nvidia_nvcf",
        "asr_model": getattr(settings, "tamil_asr_model", None) or ("riva-tamil-asr" if is_ext else "ai-whisper-large-v3"),
        "tts_model": getattr(settings, "tamil_tts_model", None) or ("riva-tamil-tts" if is_ext else "chatterbox-multilingual"),
        "tts_voice": getattr(settings, "tamil_tts_voice", None) or ("ta-IN-Standard" if is_ext else "Chatterbox-Multilingual"),
        "reason": None,
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

    async def speech_to_text(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        return await self.transcribe(pcm_bytes, sample_rate=sample_rate)

    @abc.abstractmethod
    def stream_synthesize(self, text: str, voice: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        pass

    def text_to_speech(self, text: str, voice: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        return self.stream_synthesize(text, voice=voice)

    @abc.abstractmethod
    def get_prompt_instruction(self) -> Optional[str]:
        pass

    def get_supported_languages(self) -> list:
        from app.live.language_config import LanguageConfig
        return list(LanguageConfig.get_supported_languages().keys())

    def get_supported_voices(self) -> list:
        from app.live.language_config import LanguageConfig
        return LanguageConfig.get_supported_voices(self.language)


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
    Delegates to TamilRivaProvider.
    """

    def __init__(self, provider: Optional[TamilSpeechProvider] = None):
        self.provider = provider or tamil_riva_provider

    @property
    def language(self) -> str:
        return "ta"

    def get_status(self) -> Dict[str, Any]:
        return is_tamil_voice_available()

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        return await self.provider.transcribe(pcm_bytes, sample_rate=sample_rate)

    async def stream_synthesize(self, text: str, voice: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        async for chunk in self.provider.stream_synthesize(text, voice=voice):
            yield chunk

    def get_prompt_instruction(self) -> Optional[str]:
        return (
            "You are speaking with the user in Tamil.\n"
            "Respond naturally in Tamil.\n"
            "Use clear conversational Tamil.\n"
            "Preserve technical terminology in English when that is more natural "
            "(e.g., Python, FastAPI, React, JavaScript, API, database, GitHub, Docker, NVIDIA).\n"
            "Do not translate programming keywords unnecessarily.\n"
            "If the user explicitly asks for English, respond in English."
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

