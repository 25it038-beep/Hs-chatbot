import time
import json
from typing import Optional
import httpx
from app.services.nvidia.key_manager import KeyManager

key_manager = KeyManager()

RIVA_ASR_URL = "https://api.nvidia.com/v1/audio/transcriptions"


class NvidiaSpeechProvider:
    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "en",
        model: str = "nvidia/riva-1.1b-rnnt-multilingual-asr",
    ) -> str:
        api_key = key_manager.get_key()
        if not api_key:
            raise ValueError("No available NVIDIA API keys")

        headers = {
            "Authorization": f"Bearer {api_key.key}",
        }

        files = {
            "file": ("audio.wav", audio_data, "audio/wav"),
            "model": (None, model),
            "language": (None, language),
            "response_format": (None, "json"),
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    RIVA_ASR_URL,
                    headers=headers,
                    files=files,
                )
                if response.status_code == 429:
                    key_manager.record_failure(api_key, "rate_limit")
                    raise ValueError("Rate limited")
                response.raise_for_status()
                data = response.json()

                key_manager.record_success(api_key)
                return data.get("text", "")

            except httpx.ConnectError:
                raise ValueError("Speech-to-text is not available on this NVIDIA plan. Voice input requires a Riva ASR subscription.")
            except Exception as e:
                key_manager.record_failure(api_key, str(e))
                raise
