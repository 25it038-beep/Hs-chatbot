"""
NVIDIA ASR Client for HSBot Live Voice
Uses NVIDIA Parakeet TDT 0.6B / Whisper Large v3 via gRPC worker.
"""

import asyncio
import json
import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger("hsbot.live.asr")

WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), "nvidia_grpc_worker.js")


class NvidiaLiveASR:
    def __init__(self):
        self.worker_script = WORKER_SCRIPT

    async def transcribe_pcm(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """
        Transcribes raw 16-bit 16kHz PCM audio bytes using NVIDIA ASR.
        """
        if not pcm_bytes:
            return ""

        try:
            # Run node worker via stdin for lowest latency
            proc = await asyncio.create_subprocess_exec(
                "node",
                self.worker_script,
                "asr",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate(input=pcm_bytes)

            if proc.returncode != 0:
                err_text = stderr.decode("utf-8", errors="replace").strip()
                logger.error(f"NVIDIA ASR worker error (code {proc.returncode}): {err_text}")
                return ""

            result_str = stdout.decode("utf-8", errors="replace").strip()
            if not result_str:
                return ""

            data = json.loads(result_str)
            if data.get("success"):
                transcript = data.get("text", "").strip()
                logger.info(f"NVIDIA ASR transcribed: '{transcript}'")
                return transcript
            else:
                logger.error(f"NVIDIA ASR failure: {data.get('error')}")
                return ""

        except Exception as e:
            logger.error(f"Exception during NVIDIA ASR transcription: {e}")
            return ""


# Singleton instance
live_asr = NvidiaLiveASR()
