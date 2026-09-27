"""NVIDIA Wan 2.2 Video Generation Provider."""

import base64
import asyncio
import logging
from typing import Optional, Tuple, Dict, Any
import httpx
from app.config import settings
from app.services.nvidia.key_manager import key_manager
from app.services.video.providers.base import BaseVideoProvider
from app.services.video.validation import video_validator

logger = logging.getLogger("hsbot.video.providers.wan")


class NvidiaWanVideoProvider(BaseVideoProvider):
    """
    Integration with NVIDIA Wan 2.2 Video Generation (wan-ai/wan2.2).
    Supports Text-to-Video and Image-to-Video via NVIDIA Foundation endpoints.
    """

    DEFAULT_ENDPOINT = "https://ai.api.nvidia.com/v1/videos/generations"
    FALLBACK_ENDPOINT = "https://integrate.api.nvidia.com/v1/videos/generations"
    NVCF_STATUS_URL = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/status"

    def __init__(self, model_id: str = "wan-ai/wan2.2"):
        self._model_id = model_id

    @property
    def provider_name(self) -> str:
        return "nvidia"

    @property
    def model_id(self) -> str:
        return self._model_id

    def _get_api_key(self) -> str:
        key = key_manager.get_key()
        if not key:
            raise RuntimeError("No active NVIDIA API key available for video generation.")
        return key

    async def probe_health(self) -> Tuple[bool, str]:
        """Probes the NVIDIA API configuration and key validity."""
        key = key_manager.get_key()
        if not key:
            return False, "NVIDIA API key not configured or exhausted"
        return True, "Ready"

    async def generate_video(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1280,
        height: int = 720,
        duration_seconds: int = 5,
        fps: int = 24,
        seed: Optional[int] = None,
        reference_image_bytes: Optional[bytes] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        api_key = self._get_api_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Build payload according to NVIDIA OpenAI-compatible video specs
        payload: Dict[str, Any] = {
            "model": self.model_id,
            "prompt": prompt,
            "size": f"{width}x{height}",
            "seconds": duration_seconds,
            "fps": fps,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if seed is not None:
            payload["seed"] = seed

        if reference_image_bytes:
            b64_img = base64.b64encode(reference_image_bytes).decode("utf-8")
            payload["image"] = f"data:image/png;base64,{b64_img}"
            payload["model_mode"] = "image2video"
        else:
            payload["model_mode"] = "text2video"

        if extra_params:
            payload.update(extra_params)

        endpoint = getattr(settings, "nvidia_video_endpoint", None) or self.DEFAULT_ENDPOINT

        # Maximum poll timeout: up to 180 seconds for video rendering
        timeout = httpx.Timeout(180.0, connect=15.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
            except httpx.HTTPError as e:
                # Retry on fallback endpoint if default failed
                try:
                    response = await client.post(self.FALLBACK_ENDPOINT, json=payload, headers=headers)
                except Exception:
                    raise RuntimeError(f"Failed to connect to NVIDIA video service: {str(e)}")

            if response.status_code == 401:
                key_manager.mark_key_failed(api_key, 401)
                raise RuntimeError("NVIDIA API authentication failed (401 Unauthorized)")
            elif response.status_code == 429:
                key_manager.mark_key_failed(api_key, 429)
                raise RuntimeError("NVIDIA video generation rate limit exceeded (429 Too Many Requests)")

            # Check for direct video binary
            content_type = response.headers.get("content-type", "")
            if "video/mp4" in content_type:
                data = response.content
                valid, err, _ = video_validator.validate_mp4_bytes(data)
                if not valid:
                    raise RuntimeError(f"NVIDIA returned invalid MP4: {err}")
                return data

            # Check for 202 Accepted (NVCF asynchronous polling)
            if response.status_code == 202:
                req_id = response.headers.get("NVCF-REQID") or response.headers.get("nvcf-reqid")
                if not req_id:
                    try:
                        resp_json = response.json()
                        req_id = resp_json.get("id") or resp_json.get("request_id")
                    except Exception:
                        pass

                if not req_id:
                    raise RuntimeError("NVIDIA returned 202 Accepted without a request ID for status polling.")

                return await self._poll_nvcf_status(client, req_id, api_key)

            if response.status_code not in (200, 201):
                err_text = response.text[:400]
                raise RuntimeError(f"NVIDIA Video API error ({response.status_code}): {err_text}")

            # Parse JSON response
            try:
                data_json = response.json()
            except Exception:
                raise RuntimeError(f"Unexpected non-JSON response from NVIDIA: {response.text[:200]}")

            return self._extract_video_bytes_from_json(data_json)

    def _extract_video_bytes_from_json(self, data_json: dict) -> bytes:
        # Check standard OpenAI video structure: data[0].b64_json or url
        items = data_json.get("data") or [data_json]
        for item in items:
            if isinstance(item, dict):
                b64 = item.get("b64_json") or item.get("b64_video") or item.get("video_base64")
                if b64:
                    raw_bytes = base64.b64decode(b64)
                    valid, err, _ = video_validator.validate_mp4_bytes(raw_bytes)
                    if valid:
                        return raw_bytes
                
                # Check video asset URL
                url = item.get("url") or item.get("video_url")
                if url:
                    # Synchronous fetch of video asset url
                    import httpx
                    with httpx.Client(timeout=30.0) as cl:
                        res = cl.get(url)
                        if res.status_code == 200:
                            valid, err, _ = video_validator.validate_mp4_bytes(res.content)
                            if valid:
                                return res.content

        raise RuntimeError("No valid MP4 video payload found in NVIDIA API response.")

    async def _poll_nvcf_status(self, client: httpx.AsyncClient, req_id: str, api_key: str) -> bytes:
        """Polls NVCF execution gateway until video generation completes."""
        poll_url = f"{self.NVCF_STATUS_URL}/{req_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }

        poll_interval = 2.5
        max_polls = 72  # 72 * 2.5s = 180 seconds

        for attempt in range(max_polls):
            await asyncio.sleep(poll_interval)
            try:
                res = await client.get(poll_url, headers=headers)
            except Exception as e:
                logger.warning(f"Polling error for video job {req_id}: {e}")
                continue

            if res.status_code == 200:
                content_type = res.headers.get("content-type", "")
                if "video/mp4" in content_type:
                    return res.content
                data = res.json()
                return self._extract_video_bytes_from_json(data)
            elif res.status_code == 202:
                # Still generating
                continue
            else:
                raise RuntimeError(f"NVIDIA video generation job {req_id} failed with HTTP {res.status_code}: {res.text[:300]}")

        raise TimeoutError(f"NVIDIA video generation job {req_id} timed out after 180 seconds.")
