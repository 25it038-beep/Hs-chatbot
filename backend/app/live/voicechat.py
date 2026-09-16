"""
NVIDIA Nemotron VoiceChat Integration Module for HSBot Live Voice.
Provides direct access to nvidia/nemotron-voicechat S2S model.

Strict Contract:
- Real API calls only (NVIDIA NIM).
- Zero mock, zero simulation, zero fake voice.
- If model is unavailable (e.g. 404/403), raises NemotronVoiceChatUnavailableError.
"""

import asyncio
import json
import logging
import urllib.error
import urllib.request
from typing import AsyncGenerator, Dict, Any, Optional

from app.config import settings

logger = logging.getLogger("hsbot.live.voicechat")


class NemotronVoiceChatUnavailableError(Exception):
    """Raised when nvidia/nemotron-voicechat is not provisioned or inaccessible on the API key."""
    def __init__(self, message: str = "NEMOTRON_VOICECHAT_UNAVAILABLE", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = "NEMOTRON_VOICECHAT_UNAVAILABLE"
        self.details = details or {}


class NemotronVoiceChatClient:
    """Client for NVIDIA Nemotron VoiceChat speech-to-speech engine."""

    def __init__(self):
        self.model = getattr(settings, "nvidia_voicechat_model", "nvidia/nemotron-voicechat")
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self._availability_cache: Optional[Dict[str, Any]] = None
        self._last_checked = 0.0

    def _get_api_key(self) -> str:
        keys = [k.strip() for k in settings.nvidia_api_keys.split(",") if k.strip()]
        return keys[0] if keys else ""

    async def check_availability(self, force: bool = False) -> Dict[str, Any]:
        """
        Probes NVIDIA NIM to check if nvidia/nemotron-voicechat is available.
        Performs a real HTTP probe and caches result for 60 seconds.
        """
        import time
        now = time.time()
        if not force and self._availability_cache is not None and (now - self._last_checked) < 60.0:
            return self._availability_cache

        api_key = self._get_api_key()
        if not api_key:
            res = {
                "available": False,
                "model": self.model,
                "code": "NVIDIA_API_KEY_MISSING",
                "error": "No NVIDIA API key configured in backend settings.",
                "raw_response": "Missing API key",
            }
            self._availability_cache = res
            self._last_checked = now
            return res

        loop = asyncio.get_running_loop()

        def _probe_sync():
            # Probe 1: Direct model metadata endpoint
            model_url = f"{self.base_url}/models/{self.model}"
            req = urllib.request.Request(
                model_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "HSBot-LiveVoice/1.0",
                },
                method="GET",
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = resp.read().decode("utf-8")
                    return {
                        "available": True,
                        "model": self.model,
                        "status_code": resp.status,
                        "raw_response": data[:500],
                    }
            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8")
                except Exception:
                    pass

                # Probe 2: Check full catalog to see if account has access
                catalog_url = f"{self.base_url}/models"
                cat_req = urllib.request.Request(
                    catalog_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    method="GET",
                )
                in_catalog = False
                total_catalog = 0
                try:
                    with urllib.request.urlopen(cat_req, timeout=5) as cat_resp:
                        cat_data = json.loads(cat_resp.read().decode("utf-8"))
                        model_list = [m.get("id") for m in cat_data.get("data", [])]
                        total_catalog = len(model_list)
                        in_catalog = self.model in model_list
                except Exception:
                    pass

                return {
                    "available": False,
                    "model": self.model,
                    "code": "NEMOTRON_VOICECHAT_UNAVAILABLE",
                    "status_code": e.code,
                    "reason": e.reason,
                    "error": f"HTTP {e.code} {e.reason}: {err_body}".strip(),
                    "in_catalog": in_catalog,
                    "catalog_count": total_catalog,
                    "detail": (
                        f"Model '{self.model}' returned HTTP {e.code} {e.reason}. "
                        f"NIM catalog has {total_catalog} models on this key, but '{self.model}' is not provisioned. "
                        "NVIDIA Nemotron VoiceChat is early-access containerized NIM. Use Cascaded NVIDIA Live fallback."
                    ),
                }
            except Exception as e:
                return {
                    "available": False,
                    "model": self.model,
                    "code": "NEMOTRON_VOICECHAT_UNAVAILABLE",
                    "error": str(e),
                    "detail": f"Connection to NVIDIA NIM failed: {e}",
                }

        result = await loop.run_in_executor(None, _probe_sync)
        self._availability_cache = result
        self._last_checked = now
        logger.info(f"[NEMOTRON_VOICECHAT] Probe status for {self.model}: available={result.get('available')}")
        return result

    async def stream_voicechat(
        self,
        audio_pcm_base64: Optional[str] = None,
        text: Optional[str] = None,
        history: Optional[list] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams audio and text from NVIDIA Nemotron VoiceChat.
        If unavailable, immediately raises NemotronVoiceChatUnavailableError.
        DOES NOT mock or simulate audio.
        """
        status = await self.check_availability()
        if not status.get("available"):
            raise NemotronVoiceChatUnavailableError(
                message="NEMOTRON_VOICECHAT_UNAVAILABLE",
                details=status,
            )

        api_key = self._get_api_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        messages = list(history or [])
        if text:
            messages.append({"role": "user", "content": text})
        elif audio_pcm_base64:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "input_audio", "input_audio": {"data": audio_pcm_base64, "format": "pcm16"}},
                ]
            })

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "modalities": ["text", "audio"],
            "audio": {"voice": "alloy", "format": "pcm16"},
        }

        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/chat/completions", headers=headers, json=payload) as resp:
                if resp.status != 200:
                    err_txt = await resp.text()
                    raise NemotronVoiceChatUnavailableError(
                        message=f"HTTP {resp.status} from Nemotron VoiceChat: {err_txt}",
                        details={"status": resp.status, "body": err_txt},
                    )
                async for line in resp.content:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: ") and line_str != "data: [DONE]":
                        try:
                            data = json.loads(line_str[6:])
                            yield data
                        except Exception:
                            pass


# Global singleton
nemotron_voicechat = NemotronVoiceChatClient()
