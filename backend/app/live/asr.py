"""
NVIDIA ASR Client for HSBot Live Voice
Primary: NVIDIA Parakeet TDT 0.6B (gRPC via persistent Node.js bridge)
Fallback: Groq Whisper large-v3-turbo (REST API, fast, free tier available)
"""

import io
import logging
import wave
from typing import Optional

from app.live.riva_bridge import riva_bridge

logger = logging.getLogger("hsbot.live.asr")

# Groq Whisper fallback
_GROQ_AVAILABLE = False
_groq_client = None
try:
    from groq import AsyncGroq
    from app.config import settings
    _groq_key = getattr(settings, "groq_api_key", None)
    if _groq_key:
        _groq_client = AsyncGroq(api_key=_groq_key)
        _GROQ_AVAILABLE = True
        logger.info("Groq Whisper available as ASR fallback")
    else:
        logger.warning("GROQ_API_KEY not set — Groq ASR fallback disabled")
except Exception as _e:
    logger.warning(f"Groq ASR fallback unavailable: {_e}")


def _pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Wraps raw 16-bit PCM bytes into an in-memory WAV file for Groq Whisper."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


class NvidiaLiveASR:
    async def transcribe_pcm(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """
        Transcribes raw 16-bit PCM audio.
        1. Tries NVIDIA Parakeet via Riva gRPC bridge (Node.js).
        2. Falls back to Groq Whisper if bridge unavailable.
        """
        if not pcm_bytes or len(pcm_bytes) < 1600:
            return ""

        # ── Primary: NVIDIA Riva gRPC ──────────────────────────────────────────
        try:
            transcript = await riva_bridge.transcribe(pcm_bytes, sample_rate=sample_rate)
            if transcript:
                logger.info(f"[Riva ASR] '{transcript}'")
                return transcript
        except Exception as e:
            logger.warning(f"[ASR] Riva bridge failed ({e}), trying Groq Whisper fallback")

        # ── Fallback: Groq Whisper ─────────────────────────────────────────────
        if _GROQ_AVAILABLE and _groq_client:
            try:
                wav_bytes = _pcm_to_wav_bytes(pcm_bytes, sample_rate)
                wav_file = ("audio.wav", wav_bytes, "audio/wav")
                result = await _groq_client.audio.transcriptions.create(
                    file=wav_file,
                    model="whisper-large-v3-turbo",
                    language="en",
                    response_format="text",
                )
                transcript = result.strip() if isinstance(result, str) else result.text.strip()
                if transcript:
                    logger.info(f"[Groq Whisper ASR] '{transcript}'")
                return transcript
            except Exception as e:
                logger.error(f"[ASR] Groq Whisper fallback failed: {e}")

        return ""


# Singleton instance
live_asr = NvidiaLiveASR()
