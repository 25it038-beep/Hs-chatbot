import time
import base64
from typing import Optional
import httpx
from app.services.nvidia.key_manager import KeyManager
from pydantic import BaseModel

key_manager = KeyManager()

FLUX_MODELS = {
    "flux-1-schnell": "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell",
    "flux-1-dev": "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-dev",
    "flux-2-klein": "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b",
}

DEFAULT_IMAGE_MODEL = "flux-1-dev"


class ImageGenResponse(BaseModel):
    image_b64: str
    model: str
    provider: str
    seed: int
    latency_ms: float


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

        headers = {
            "Authorization": f"Bearer {api_key.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 429:
                    key_manager.record_failure(api_key, "rate_limit")
                    raise ValueError("Rate limited by NVIDIA")
                if response.status_code in (400, 401, 403, 404):
                    key_manager.record_failure(api_key, f"image_model_unavailable: {response.status_code}")
                    for fb_model, fb_url in FLUX_MODELS.items():
                        if fb_model == model:
                            continue
                        fb_payload = {"prompt": prompt}
                        if fb_model == "flux-2-klein":
                            fb_payload.update({"width": 1024, "height": 1024, "steps": 4, "seed": seed})
                        else:
                            fb_payload.update({"mode": "base", "steps": min(steps or 40, 40), "seed": seed})
                        try:
                            fb_resp = await client.post(fb_url, headers=headers, json=fb_payload)
                            if fb_resp.status_code == 200:
                                fb_data = fb_resp.json()
                                fb_artifacts = fb_data.get("artifacts", [])
                                if fb_artifacts:
                                    key_manager.record_success(api_key)
                                    return ImageGenResponse(
                                        image_b64=fb_artifacts[0]["base64"],
                                        model=fb_model,
                                        provider="nvidia",
                                        seed=fb_artifacts[0].get("seed", seed),
                                        latency_ms=(time.time() - start) * 1000,
                                    )
                        except Exception:
                            continue
                    raise ValueError(f"Image model {model} unavailable (HTTP {response.status_code}) and no fallback worked")
                response.raise_for_status()
                data = response.json()
                latency = (time.time() - start) * 1000

                key_manager.record_success(api_key)

                artifacts = data.get("artifacts", [])
                if not artifacts:
                    raise ValueError("No image generated")

                return ImageGenResponse(
                    image_b64=artifacts[0]["base64"],
                    model=model,
                    provider="nvidia",
                    seed=artifacts[0].get("seed", seed),
                    latency_ms=latency,
                )

            except httpx.TimeoutException:
                key_manager.record_failure(api_key, "timeout")
                raise
            except Exception as e:
                key_manager.record_failure(api_key, str(e))
                raise

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
