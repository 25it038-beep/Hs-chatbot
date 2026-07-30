import time
import json
import base64
from typing import Optional
import httpx
from app.services.nvidia.config import NVIDIA_BASE_URL
from app.services.nvidia.key_manager import KeyManager
from app.services.model_providers.base import ModelResponse

key_manager = KeyManager()


def encode_image(image_data: bytes, mime_type: str = "image/png") -> str:
    return f"data:{mime_type};base64,{base64.b64encode(image_data).decode('utf-8')}"


class NvidiaVisionProvider:
    def __init__(self):
        self.base_url = NVIDIA_BASE_URL

    async def analyze(
        self,
        image_data: bytes,
        prompt: str = "Describe this image in detail.",
        mime_type: str = "image/png",
        model: str = "meta/llama-3.2-11b-vision-instruct",
        temperature: float = 1.0,
        max_tokens: int = 512,
    ) -> ModelResponse:
        start = time.time()
        api_key = key_manager.get_key()
        if not api_key:
            raise ValueError("No available NVIDIA API keys")

        encoded = encode_image(image_data, mime_type)

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": encoded}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {api_key.key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if response.status_code in (429, 503, 529):
                    key_manager.record_failure(api_key, f"server_busy: {response.status_code}")
                    raise ValueError(f"Server busy: {response.status_code}")
                if response.status_code >= 500:
                    key_manager.record_failure(api_key, f"server_error: {response.status_code}")
                    raise ValueError(f"Server error: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                latency = (time.time() - start) * 1000
                content = data["choices"][0]["message"]["content"] or ""
                usage = data.get("usage", {})

                key_manager.record_success(api_key, usage.get("total_tokens", 0))
                return ModelResponse(
                    content=content,
                    model=model,
                    provider="nvidia",
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    latency_ms=latency,
                )

            except httpx.TimeoutException:
                key_manager.record_failure(api_key, "timeout")
                raise
            except Exception as e:
                key_manager.record_failure(api_key, str(e))
                raise
