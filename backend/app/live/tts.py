"""
NVIDIA TTS Client for HSBot Live Voice
Uses persistent NVIDIA Chatterbox Multilingual gRPC via Riva bridge.
"""

import base64
import logging
from typing import Dict, Any, Optional, AsyncGenerator

from app.live.riva_bridge import riva_bridge

logger = logging.getLogger("hsbot.live.tts")


class NvidiaLiveTTS:
    async def stream_synthesize(
        self,
        text: str,
        voice: str = "Chatterbox-Multilingual",
        sample_rate: int = 24000,
    ) -> AsyncGenerator[bytes, None]:
        """Streams raw PCM audio chunks from NVIDIA Riva TTS."""
        clean_text = text.strip()
        if not clean_text:
            return
        try:
            async for chunk in riva_bridge.stream_synthesize(
                text=clean_text,
                voice=voice,
                sample_rate=sample_rate,
            ):
                if chunk:
                    yield chunk
        except Exception as e:
            logger.error(f"[TTS] Riva stream error: {e}")

    async def synthesize(
        self,
        text: str,
        voice: str = "Chatterbox-Multilingual",
        sample_rate: int = 24000,
    ) -> Optional[Dict[str, Any]]:
        """Returns full PCM audio as base64."""
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
            logger.error(f"[TTS] Synthesis error: {e}")
            return None


live_tts = NvidiaLiveTTS()
