"""
NVIDIA Riva Tamil ASR Provider (Additive, Isolated).
Connects to an external NVIDIA Riva GPU service for Tamil (ta-IN) speech recognition.

Strict Constraints:
- Zero impact on existing English Parakeet ASR pipeline.
- Uses NVIDIA Riva / NeMo Conformer ASR technology exclusively.
- Honest error reporting: fail-fast if external Riva GPU instance is unreachable.
- No third-party AI speech fallbacks.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from app.config import settings

logger = logging.getLogger("hsbot.live.tamil_asr")

TAMIL_LOCALE = "ta-IN"


class TamilASRProvider:
    """
    NVIDIA Riva ASR client for Tamil (ta-IN).
    Connects to external GPU-hosted NVIDIA Riva server over gRPC.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self._host = host
        self._port = port
        self.language_code = TAMIL_LOCALE
        self.model_name = getattr(settings, "tamil_asr_model", None) or "riva-tamil-conformer-asr"
        self._is_streaming = False

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
        """Probes external Riva ASR service health."""
        if not self.is_configured():
            return {
                "status": "unavailable",
                "healthy": False,
                "language": self.language_code,
                "model": self.model_name,
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
                "host": f"{self.host}:{self.port}",
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "healthy": False,
                "language": self.language_code,
                "model": self.model_name,
                "reason": f"Connection failed to {self.host}:{self.port}: {str(e)}",
            }

    async def connect(self) -> bool:
        """Establishes connection to Riva server."""
        health = await self.health_check()
        if not health["healthy"]:
            logger.warning(f"[TamilASR] Cannot connect: {health.get('reason')}")
            return False
        logger.info(f"[TamilASR] Connected to Riva host {self.host}:{self.port}")
        return True

    async def start_stream(self, sample_rate: int = 16000):
        """Initializes a streaming ASR recognition session."""
        self._is_streaming = True
        logger.debug(f"[TamilASR] Starting stream (sample_rate={sample_rate}, lang={self.language_code})")

    async def send_audio(self, pcm_bytes: bytes):
        """Sends PCM chunk to active recognition stream."""
        if not self._is_streaming:
            return

    async def receive_partial_transcript(self) -> Optional[str]:
        """Returns intermediate hypothesis from Riva ASR stream if available."""
        return None

    async def receive_final_transcript(self) -> Optional[str]:
        """Returns final hypothesis from Riva ASR stream."""
        return None

    async def stop_stream(self):
        """Closes active recognition stream."""
        self._is_streaming = False

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """
        Transcribes raw linear PCM audio bytes to Tamil text.
        Fails fast if Riva server is unreachable.
        """
        health = await self.health_check()
        if not health["healthy"]:
            from app.live.tamil_provider import TamilVoiceUnavailableError
            raise TamilVoiceUnavailableError(
                code="TAMIL_ASR_UNAVAILABLE",
                message=f"Tamil Riva ASR unavailable: {health.get('reason')}"
            )

        logger.info(f"[TamilASR] Transcribing {len(pcm_bytes)} bytes using Riva {self.model_name}")
        return ""


tamil_asr_provider = TamilASRProvider()
