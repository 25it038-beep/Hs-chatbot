import time
import json
from typing import Optional
import httpx
from app.services.nvidia.key_manager import KeyManager
from app.config import settings

key_manager = KeyManager()

RIVA_ASR_URL = "https://api.nvidia.com/v1/audio/transcriptions"
RIVA_TTS_URL = "https://api.nvidia.com/v1/audio/speech"


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

    async def synthesize(
        self,
        text: str,
        voice: str = "en-US-Female-1",
        model: str = "nvidia/riva-tts-multilingual",
        language: str = "en-US",
        sample_rate: int = 24000,
    ) -> bytes:
        """Generate speech audio from text using NVIDIA Riva TTS."""
        api_key = key_manager.get_key()
        if not api_key:
            raise ValueError("No available NVIDIA API keys")

        headers = {
            "Authorization": f"Bearer {api_key.key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "language": language,
            "sample_rate": sample_rate,
            "response_format": "wav",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    RIVA_TTS_URL,
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 429:
                    key_manager.record_failure(api_key, "rate_limit")
                    raise ValueError("Rate limited")
                response.raise_for_status()

                key_manager.record_success(api_key)
                return response.content

            except httpx.ConnectError:
                raise ValueError("Text-to-speech is not available on this NVIDIA plan. Voice output requires a Riva TTS subscription.")
            except Exception as e:
                key_manager.record_failure(api_key, str(e))
                raise

    async def synthesize_stream(
        self,
        text: str,
        voice: str = "en-US-Female-1",
        model: str = "nvidia/riva-tts-multilingual",
        language: str = "en-US",
        sample_rate: int = 24000,
        chunk_size: int = 1024,
    ):
        """Stream speech audio chunks for real-time playback."""
        api_key = key_manager.get_key()
        if not api_key:
            raise ValueError("No available NVIDIA API keys")

        headers = {
            "Authorization": f"Bearer {api_key.key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "language": language,
            "sample_rate": sample_rate,
            "response_format": "wav",
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                async with client.stream("POST", RIVA_TTS_URL, headers=headers, json=payload) as response:
                    if response.status_code == 429:
                        key_manager.record_failure(api_key, "rate_limit")
                        raise ValueError("Rate limited")
                    response.raise_for_status()

                    async for chunk in response.aiter_bytes(chunk_size):
                        if chunk:
                            yield chunk

                    key_manager.record_success(api_key)

            except httpx.ConnectError:
                raise ValueError("Text-to-speech streaming is not available on this NVIDIA plan.")
            except Exception as e:
                key_manager.record_failure(api_key, str(e))
                raise
