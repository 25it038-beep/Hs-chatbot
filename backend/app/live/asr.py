"""
NVIDIA ASR Client for HSBot Live Voice
Uses persistent NVIDIA Parakeet TDT 0.6B gRPC channel via Node.js bridge.
"""

import logging
from app.live.riva_bridge import riva_bridge

logger = logging.getLogger("hsbot.live.asr")


class NvidiaLiveASR:
    async def transcribe_pcm(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """
        Transcribes raw 16-bit PCM audio bytes using NVIDIA Riva ASR gRPC.
        """
        if not pcm_bytes or len(pcm_bytes) < 1600:
            return ""
        try:
            transcript = await riva_bridge.transcribe(pcm_bytes, sample_rate=sample_rate)
            if transcript:
                logger.info(f"[Riva ASR] '{transcript}'")
            return transcript
        except Exception as e:
            logger.error(f"[ASR] Riva transcription error: {e}")
            return ""


live_asr = NvidiaLiveASR()
