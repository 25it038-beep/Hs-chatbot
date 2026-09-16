"""
NVIDIA ASR — uses pure Python gRPC bridge (no Node.js).
"""
import logging
from app.live import riva_python_bridge as _bridge

logger = logging.getLogger("hsbot.live.asr")


class NvidiaLiveASR:
    async def transcribe_pcm(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        if not pcm_bytes or len(pcm_bytes) < 1600:
            return ""
        try:
            transcript = await _bridge.transcribe(pcm_bytes, sample_rate=sample_rate)
            if transcript:
                logger.info(f"[Riva ASR] '{transcript}'")
            return transcript
        except Exception as e:
            logger.error(f"[ASR] Error: {e}")
            return ""


live_asr = NvidiaLiveASR()
