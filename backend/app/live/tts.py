"""
NVIDIA TTS Client for HSBot Live Voice
Uses NVIDIA Chatterbox Multilingual TTS via gRPC worker.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger("hsbot.live.tts")

WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), "nvidia_grpc_worker.js")


class NvidiaLiveTTS:
    def __init__(self):
        self.worker_script = WORKER_SCRIPT

    async def synthesize(
        self,
        text: str,
        voice: str = "Chatterbox-Multilingual",
        sample_rate: int = 24000
    ) -> Optional[Dict[str, Any]]:
        """
        Synthesizes text into raw PCM audio base64 using NVIDIA TTS.
        Returns: { 'audio': base64_pcm, 'sampleRate': 24000, 'bytes': int }
        """
        clean_text = text.strip()
        if not clean_text:
            return None

        try:
            proc = await asyncio.create_subprocess_exec(
                "node",
                self.worker_script,
                "tts",
                clean_text,
                voice,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                err_text = stderr.decode("utf-8", errors="replace").strip()
                logger.error(f"NVIDIA TTS worker error (code {proc.returncode}): {err_text}")
                return None

            result_str = stdout.decode("utf-8", errors="replace").strip()
            if not result_str:
                return None

            data = json.loads(result_str)
            if data.get("success"):
                logger.info(f"NVIDIA TTS synthesized {data.get('bytes')} bytes for: '{clean_text[:40]}...'")
                return {
                    "audio": data.get("audio"),
                    "sampleRate": data.get("sampleRate", sample_rate),
                    "bytes": data.get("bytes", 0),
                }
            else:
                logger.error(f"NVIDIA TTS failure: {data.get('error')}")
                return None

        except Exception as e:
            logger.error(f"Exception during NVIDIA TTS synthesis: {e}")
            return None


# Singleton instance
live_tts = NvidiaLiveTTS()
