"""
NVIDIA TTS Client for HSBot Live Voice
Primary: NVIDIA Riva Chatterbox Multilingual (gRPC via persistent Node.js bridge)
Fallback: edge-tts (Microsoft neural voices, no API key, pure Python)
"""

import base64
import logging
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator

from app.live.riva_bridge import riva_bridge

logger = logging.getLogger("hsbot.live.tts")

# edge-tts fallback voice — high quality female voice, no API key needed
EDGE_TTS_VOICE = "en-US-JennyNeural"

# Will be set to False if edge-tts import fails
_EDGE_TTS_AVAILABLE = False
try:
    import edge_tts
    _EDGE_TTS_AVAILABLE = True
    logger.info("edge-tts available as TTS fallback")
except ImportError:
    logger.warning("edge-tts not installed — Riva-only TTS mode")

# Will be set to False if miniaudio import fails
_MINIAUDIO_AVAILABLE = False
try:
    import miniaudio
    _MINIAUDIO_AVAILABLE = True
except ImportError:
    logger.warning("miniaudio not installed — MP3→PCM conversion unavailable")


async def _edge_tts_stream_pcm(text: str, sample_rate: int = 24000) -> AsyncGenerator[bytes, None]:
    """
    Synthesizes text via edge-tts (free Microsoft neural voice, no key needed),
    decodes MP3 to raw 16-bit PCM and yields chunks compatible with the Live audio pipeline.
    """
    if not _EDGE_TTS_AVAILABLE:
        logger.error("edge-tts not available for fallback TTS")
        return

    try:
        communicate = edge_tts.Communicate(text.strip(), voice=EDGE_TTS_VOICE)

        if _MINIAUDIO_AVAILABLE:
            # Stream MP3 chunks, collect, decode to PCM with miniaudio
            mp3_buf = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_buf.extend(chunk["data"])

            if not mp3_buf:
                return

            decoded = miniaudio.decode(
                bytes(mp3_buf),
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=1,
                sample_rate=sample_rate,
            )
            pcm_bytes = bytes(decoded.samples)
            logger.info(f"[edge-tts] Synthesized {len(pcm_bytes)} PCM bytes via miniaudio decode")

            chunk_size = sample_rate * 2 // 10  # 100ms chunks
            for i in range(0, len(pcm_bytes), chunk_size):
                yield pcm_bytes[i : i + chunk_size]
        else:
            # No miniaudio — yield raw MP3 bytes and let frontend handle decoding
            # Frontend will see format:'mp3' flag and use decodeAudioData
            mp3_buf = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_buf.extend(chunk["data"])
            if mp3_buf:
                # Yield as a single chunk; caller must handle MP3 format
                logger.info(f"[edge-tts] Yielding {len(mp3_buf)} MP3 bytes (no PCM decode)")
                yield bytes(mp3_buf)

    except Exception as e:
        logger.error(f"[edge-tts] Fallback TTS error: {e}", exc_info=True)


class NvidiaLiveTTS:
    """
    TTS client with automatic fallback:
      1. NVIDIA Riva gRPC (via persistent Node.js bridge) — best quality
      2. edge-tts (Microsoft Jenny neural voice) — no key, pure Python fallback
    """

    async def stream_synthesize(
        self,
        text: str,
        voice: str = "Chatterbox-Multilingual",
        sample_rate: int = 24000,
    ) -> AsyncGenerator[bytes, None]:
        """
        Streams raw PCM audio chunks. Tries Riva first, falls back to edge-tts.
        """
        clean_text = text.strip()
        if not clean_text:
            return

        # ── Primary: NVIDIA Riva gRPC ──────────────────────────────────────────
        riva_ok = False
        try:
            chunk_count = 0
            async for chunk in riva_bridge.stream_synthesize(
                text=clean_text,
                voice=voice,
                sample_rate=sample_rate,
            ):
                if chunk:
                    chunk_count += 1
                    riva_ok = True
                    yield chunk
        except Exception as e:
            logger.warning(f"[TTS] Riva bridge failed ({e}), falling back to edge-tts")

        if riva_ok:
            return  # Riva succeeded, done

        # ── Fallback: edge-tts (Microsoft neural voice, no API key) ───────────
        if _EDGE_TTS_AVAILABLE:
            logger.info(f"[TTS] Using edge-tts fallback ({EDGE_TTS_VOICE}) for: {clean_text[:60]}")
            async for chunk in _edge_tts_stream_pcm(clean_text, sample_rate=sample_rate):
                yield chunk
        else:
            logger.error("[TTS] Both Riva and edge-tts unavailable — no audio output")

    async def synthesize(
        self,
        text: str,
        voice: str = "Chatterbox-Multilingual",
        sample_rate: int = 24000,
    ) -> Optional[Dict[str, Any]]:
        """
        Synthesizes text into full PCM audio base64 (accumulating stream chunks).
        Returns: { 'audio': base64_pcm, 'sampleRate': sample_rate, 'bytes': int }
        """
        clean_text = text.strip()
        if not clean_text:
            return None

        chunks = []
        try:
            async for chunk in self.stream_synthesize(clean_text, voice=voice, sample_rate=sample_rate):
                chunks.append(chunk)

            if not chunks:
                return None

            all_bytes = b"".join(chunks)
            return {
                "audio": base64.b64encode(all_bytes).decode("ascii"),
                "sampleRate": sample_rate,
                "bytes": len(all_bytes),
            }
        except Exception as e:
            logger.error(f"[TTS] Exception during synthesis: {e}")
            return None


# Singleton instance
live_tts = NvidiaLiveTTS()
