import asyncio
import time
import base64
from typing import Optional
import httpx
from app.services.nvidia.key_manager import KeyManager
from pydantic import BaseModel

key_manager = KeyManager()

FLUX_MODELS = {
    "flux-1-dev": "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-dev",
    "flux-2-klein": "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b",
    "flux-1-schnell": "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell",
}

DEFAULT_IMAGE_MODEL = "flux-1-dev"

RETRY_DELAY_SECONDS = 2.0


class ImageGenResponse(BaseModel):
    image_b64: str
    model: str
    provider: str
    seed: int
    latency_ms: float


def _build_payload(model: str, prompt: str, steps: int, seed: int, image: Optional[bytes] = None) -> dict:
    if model == "flux-2-klein":
        payload = {
            "prompt": prompt,
            "width": 1024,
            "height": 1024,
            "steps": min(steps or 4, 4),
            "seed": seed,
        }
    else:
        payload = {
            "prompt": prompt,
            "mode": "base",
            "steps": steps if model == "flux-1-dev" else min(steps, 4),
            "seed": seed,
        }

    if image:
        encoded = base64.b64encode(image).decode("utf-8")
        payload["image"] = f"data:image/png;base64,{encoded}"

    return payload


class NvidiaImageProvider:
    async def generate(
        self,
        prompt: str,
        image: Optional[bytes] = None,
        model: str = DEFAULT_IMAGE_MODEL,
        steps: int = 40,
        seed: int = 0,
    ) -> ImageGenResponse:
        start = time.time()
        api_key = key_manager.get_key()
        if not api_key:
            raise ValueError("No available NVIDIA API keys")

        url = FLUX_MODELS.get(model, FLUX_MODELS[DEFAULT_IMAGE_MODEL])

        headers = {
            "Authorization": f"Bearer {api_key.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, headers=headers, json=_build_payload(model, prompt, steps, seed, image))
                if response.status_code == 200:
                    return self._success(response, model, start, api_key)

                if response.status_code == 429:
                    key_manager.record_failure(api_key, "rate_limit")
                    raise ValueError("Rate limited by NVIDIA")

                if response.status_code >= 500:
                    # Transient server error (NVIDIA cold start) — retry same model once, then fall back
                    key_manager.record_failure(api_key, f"image_model_error: {response.status_code}")
                    candidates = [model, *[m for m in FLUX_MODELS if m != model]]
                else:
                    # 400/401/403/404 — model unavailable with this key, try fallbacks directly
                    key_manager.record_failure(api_key, f"image_model_unavailable: {response.status_code}")
                    candidates = [m for m in FLUX_MODELS if m != model]

                for fb_model in candidates:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    fb_url = FLUX_MODELS[fb_model]
                    try:
                        fb_resp = await client.post(fb_url, headers=headers, json=_build_payload(fb_model, prompt, steps, seed, image))
                    except Exception:
                        continue
                    if fb_resp.status_code == 200:
                        return self._success(fb_resp, fb_model, start, api_key)
                    key_manager.record_failure(api_key, f"image_model_error: {fb_model}: {fb_resp.status_code}")

                raise ValueError(f"Image generation failed for {model} and all fallback models (HTTP {response.status_code})")
            except httpx.TimeoutException:
                key_manager.record_failure(api_key, "timeout")
                raise
            except Exception as e:
                key_manager.record_failure(api_key, str(e))
                raise

    def _success(self, response: httpx.Response, model: str, start: float, api_key) -> ImageGenResponse:
        data = response.json()
        artifacts = data.get("artifacts", [])
        if not artifacts:
            raise ValueError("No image generated")
        key_manager.record_success(api_key)
        return ImageGenResponse(
            image_b64=artifacts[0]["base64"],
            model=model,
            provider="nvidia",
            seed=artifacts[0].get("seed", 0),
            latency_ms=(time.time() - start) * 1000,
        )

    async def edit(
        self,
        prompt: str,
        image_data: bytes,
    ) -> ImageGenResponse:
        return await self.generate(
            prompt=prompt,
            image=image_data,
            steps=40,
        )
