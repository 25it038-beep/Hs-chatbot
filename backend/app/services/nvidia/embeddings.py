import time
from typing import Optional
import httpx
from app.services.nvidia.config import NVIDIA_BASE_URL
from app.services.nvidia.key_manager import KeyManager

key_manager = KeyManager()


class NvidiaEmbeddingsProvider:
    def __init__(self):
        self.base_url = NVIDIA_BASE_URL

    async def create(
        self,
        texts: list[str],
        model: str = "nvidia/nv-embed-v1",
        input_type: str = "query",
        truncate: str = "NONE",
    ) -> list[list[float]]:
        api_key = key_manager.get_key()
        if not api_key:
            raise ValueError("No available NVIDIA API keys")

        payload = {
            "input": texts,
            "model": model,
            "encoding_format": "float",
            "input_type": input_type,
            "truncate": truncate,
        }

        headers = {
            "Authorization": f"Bearer {api_key.key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 429:
                    key_manager.record_failure(api_key, "rate_limit")
                    raise ValueError("Rate limited")
                response.raise_for_status()
                data = response.json()

                key_manager.record_success(api_key)
                return [item["embedding"] for item in data["data"]]

            except Exception as e:
                key_manager.record_failure(api_key, str(e))
                raise

    async def create_code_embedding(self, texts: list[str], input_type: str = "query") -> list[list[float]]:
        return await self.create(
            texts=texts,
            model="nvidia/nv-embedcode-7b-v1",
            input_type=input_type,
        )
