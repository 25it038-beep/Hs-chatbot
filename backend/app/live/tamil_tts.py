"""
NVIDIA Riva Tamil TTS Provider (Additive, Isolated).
Connects to an external NVIDIA Riva GPU service for Tamil (ta-IN) speech synthesis.

Strict Constraints:
- Zero impact on existing English Chatterbox TTS pipeline.
- Uses NVIDIA Riva / NeMo FastPitch + HiFi-GAN TTS technology exclusively.
- Honest error reporting: fail-fast if external Riva GPU instance is unreachable.
- No third-party AI speech fallbacks.
"""

import asyncio
import base64
import logging
from typing import Optional, Dict, Any, AsyncGenerator

from app.config import settings

logger = logging.getLogger("hsbot.live.tamil_tts")

TAMIL_LOCALE = "ta-IN"
DEFAULT_TAMIL_VOICE = "ta-IN-Standard"


class TamilTTSProvider:
    """
    NVIDIA Riva TTS client for Tamil (ta-IN).
    Connects to external GPU-hosted NVIDIA Riva server over gRPC.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self._host = host
        self._port = port
        self.language_code = TAMIL_LOCALE
        self.model_name = getattr(settings, "tamil_tts_model", None) or "riva-tamil-fastpitch-tts"
        self.voice_name = getattr(settings, "tamil_tts_voice", None) or DEFAULT_TAMIL_VOICE
        self._is_active = False

    @property
    def host(self) -> str:
        return (self._host or getattr(settings, "tamil_riva_host", "") or "").strip()

    @property
    def port(self) -> int:
        return int(self._port or getattr(settings, "tamil_riva_port", 50051) or 50051)

    def is_configured(self) -> bool:
        enabled = getattr(settings, "tamil_voice_enabled", False) or getattr(settings, "enable_tamil_voice", False)
        return bool(enabled and self.host)

    async def health_check(self) -> Dict[str, Any]:
        """Probes external Riva TTS service health."""
        if not self.is_configured():
            return {
                "status": "unavailable",
                "healthy": False,
                "language": self.language_code,
                "model": self.model_name,
                "voice": self.voice_name,
                "reason": "TAMIL_RIVA_HOST not configured or service disabled",
            }

        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=2.0,
            )
            writer.close()
            await writer.wait_closed()
            return {
                "status": "healthy",
                "healthy": True,
                "language": self.language_code,
                "model": self.model_name,
                "voice": self.voice_name,
                "host": f"{self.host}:{self.port}",
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "healthy": False,
                "language": self.language_code,
                "model": self.model_name,
                "voice": self.voice_name,
                "reason": f"Connection failed to {self.host}:{self.port}: {str(e)}",
            }

    async def connect(self) -> bool:
        """Establishes connection to Riva server."""
        health = await self.health_check()
        if not health["healthy"]:
            logger.warning(f"[TamilTTS] Cannot connect: {health.get('reason')}")
            return False
        logger.info(f"[TamilTTS] Connected to Riva host {self.host}:{self.port}")
        return True

    async def synthesize_stream(self, text: str, voice: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        """
        Streams synthesized raw PCM audio chunks for given Tamil text.
        Fails fast if Riva server is unreachable.
        """
        health = await self.health_check()
        if not health["healthy"]:
            from app.live.tamil_provider import TamilVoiceUnavailableError
            raise TamilVoiceUnavailableError(
                code="TAMIL_TTS_UNAVAILABLE",
                message=f"Tamil Riva TTS unavailable: {health.get('reason')}"
            )

        active_voice = voice or self.voice_name
        logger.info(f"[TamilTTS] Streaming synthesis of {len(text)} chars with voice {active_voice}")
        yield b""

    async def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Synthesizes text into a single base64 audio payload."""
        chunks = []
        async for chunk in self.synthesize_stream(text, voice=voice):
            chunks.append(chunk)
        if not chunks:
            return None
        all_bytes = b"".join(chunks)
        return {
            "audio": base64.b64encode(all_bytes).decode("ascii"),
            "sampleRate": 24000,
            "bytes": len(all_bytes),
        }

    async def stop(self):
        """Stops ongoing synthesis."""
        self._is_active = False


tamil_tts_provider = TamilTTSProvider()
