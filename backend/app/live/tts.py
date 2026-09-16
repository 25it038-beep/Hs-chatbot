"""
NVIDIA TTS — uses pure Python gRPC bridge (no Node.js).
"""
import base64
import logging
from typing import AsyncGenerator, Dict, Any, Optional

from app.live import riva_python_bridge as _bridge

logger = logging.getLogger("hsbot.live.tts")


class NvidiaLiveTTS:
    async def stream_synthesize(
        self,
        text: str,
        voice: str = "Chatterbox-Multilingual",
        sample_rate: int = 24000,
    ) -> AsyncGenerator[bytes, None]:
        clean = text.strip()
        if not clean:
            return
        try:
            async for chunk in _bridge.stream_synthesize(clean, voice=voice, sample_rate=sample_rate):
                if chunk:
                    yield chunk
        except Exception as e:
            logger.error(f"[TTS] Error: {e}")

    async def synthesize(
        self,
        text: str,
        voice: str = "Chatterbox-Multilingual",
        sample_rate: int = 24000,
    ) -> Optional[Dict[str, Any]]:
        chunks = []
        async for chunk in self.stream_synthesize(text, voice=voice, sample_rate=sample_rate):
            chunks.append(chunk)
        if not chunks:
            return None
        all_bytes = b"".join(chunks)
        return {
            "audio": base64.b64encode(all_bytes).decode("ascii"),
            "sampleRate": sample_rate,
            "bytes": len(all_bytes),
        }


live_tts = NvidiaLiveTTS()
