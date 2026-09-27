"""NVIDIA Cosmos 3 Nano Video Generation Provider."""

import base64
import asyncio
import logging
from typing import Optional, Tuple, Dict, Any
import httpx
from app.config import settings
from app.services.nvidia.key_manager import key_manager
from app.services.video.providers.base import BaseVideoProvider
from app.services.video.validation import video_validator

logger = logging.getLogger("hsbot.video.providers.cosmos")


class NvidiaCosmosVideoProvider(BaseVideoProvider):
    """
    NVIDIA Cosmos 3 Nano Video Generation Provider.
    Supports physical AI text-to-video and image-to-video synthesis.
    """

    COSMOS_PREVIEW_ENDPOINT = "https://ai.api.nvidia.com/v1/cosmos/nvidia/cosmos3-nano"
    COSMOS_NVCF_ENDPOINT = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/f65a2585-3b67-46ce-a431-af764d93e954"

    def __init__(self, model_id: str = "nvidia/cosmos3-nano"):
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
            raise RuntimeError("No active NVIDIA API key available for Cosmos video generation.")
        return key

    async def probe_health(self) -> Tuple[bool, str]:
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

        num_frames = max(24, int(duration_seconds * fps))

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": negative_prompt or "blurry, low quality, distorted, jitter",
            "height": height,
            "width": width,
            "num_frames": num_frames,
            "fps": fps,
        }
        if seed is not None:
            payload["seed"] = seed

        if reference_image_bytes:
            b64_img = base64.b64encode(reference_image_bytes).decode("utf-8")
            payload["input_image"] = f"data:image/png;base64,{b64_img}"
            payload["mode"] = "image2video"
        else:
            payload["mode"] = "text2video"

        if extra_params:
            payload.update(extra_params)

        endpoint = getattr(settings, "nvidia_cosmos_endpoint", None) or self.COSMOS_PREVIEW_ENDPOINT

        timeout = httpx.Timeout(180.0, connect=15.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
            except httpx.HTTPError:
                # Try NVCF endpoint fallback
                try:
                    response = await client.post(self.COSMOS_NVCF_ENDPOINT, json=payload, headers=headers)
                except Exception as e:
                    raise RuntimeError(f"Failed to connect to NVIDIA Cosmos service: {str(e)}")

            if response.status_code == 401:
                key_manager.mark_key_failed(api_key, 401)
                raise RuntimeError("NVIDIA Cosmos authentication failed (401 Unauthorized)")
            elif response.status_code == 429:
                key_manager.mark_key_failed(api_key, 429)
                raise RuntimeError("NVIDIA Cosmos rate limit exceeded (429 Too Many Requests)")

            if "video/mp4" in response.headers.get("content-type", ""):
                valid, err, _ = video_validator.validate_mp4_bytes(response.content)
                if not valid:
                    raise RuntimeError(f"Cosmos returned invalid MP4 data: {err}")
                return response.content

            if response.status_code == 202:
                req_id = response.headers.get("NVCF-REQID") or response.headers.get("nvcf-reqid")
                if not req_id:
                    try:
                        req_id = response.json().get("id")
                    except Exception:
                        pass
                if not req_id:
                    raise RuntimeError("NVIDIA Cosmos returned 202 without a request ID.")
                return await self._poll_nvcf_status(client, req_id, api_key)

            if response.status_code not in (200, 201):
                raise RuntimeError(f"NVIDIA Cosmos API error ({response.status_code}): {response.text[:300]}")

            try:
                res_data = response.json()
            except Exception:
                raise RuntimeError(f"Invalid non-JSON response from Cosmos API: {response.text[:200]}")

            return self._extract_video_bytes_from_json(res_data)

    def _extract_video_bytes_from_json(self, data_json: dict) -> bytes:
        candidates = [
            data_json.get("b64_video"),
            data_json.get("video_base64"),
            data_json.get("video"),
        ]
        if isinstance(data_json.get("data"), list) and len(data_json["data"]) > 0:
            candidates.append(data_json["data"][0].get("b64_json"))
            candidates.append(data_json["data"][0].get("url"))

        for c in candidates:
            if not c:
                continue
            if isinstance(c, str):
                if c.startswith("http://") or c.startswith("https://"):
                    import httpx
                    with httpx.Client(timeout=30.0) as cl:
                        res = cl.get(c)
                        if res.status_code == 200:
                            valid, err, _ = video_validator.validate_mp4_bytes(res.content)
                            if valid:
                                return res.content
                else:
                    raw_bytes = base64.b64decode(c)
                    valid, err, _ = video_validator.validate_mp4_bytes(raw_bytes)
                    if valid:
                        return raw_bytes

        raise RuntimeError("No decodable MP4 video payload returned from NVIDIA Cosmos.")

    async def _poll_nvcf_status(self, client: httpx.AsyncClient, req_id: str, api_key: str) -> bytes:
        poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
        for _ in range(72):
            await asyncio.sleep(2.5)
            try:
                res = await client.get(poll_url, headers=headers)
            except Exception:
                continue
            if res.status_code == 200:
                if "video/mp4" in res.headers.get("content-type", ""):
                    return res.content
                return self._extract_video_bytes_from_json(res.json())
            elif res.status_code == 202:
                continue
            else:
                raise RuntimeError(f"Cosmos job {req_id} failed ({res.status_code}): {res.text[:200]}")
        raise TimeoutError(f"Cosmos job {req_id} timed out.")
