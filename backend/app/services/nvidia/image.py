import time
import base64
from typing import Optional
import httpx
from app.services.nvidia.key_manager import KeyManager
from pydantic import BaseModel

key_manager = KeyManager()

FLUX_MODELS = {
    "flux-1-dev": "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-dev",
    "flux-1-schnell": "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell",
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

        payload = {
            "prompt": prompt,
            "steps": steps,
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
