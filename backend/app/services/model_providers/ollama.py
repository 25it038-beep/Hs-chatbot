import time
import json
from typing import AsyncGenerator
import httpx
from app.config import settings
from app.services.model_providers.base import ModelProvider, ModelResponse, StreamChunk


class OllamaProvider(ModelProvider):
    def __init__(self, provider_name: str = "ollama"):
        self.provider_name = provider_name
        self.base_url = settings.ollama_base_url

    def _get_model(self, model: str | None) -> str:
        return model or settings.ollama_default_model

    async def generate(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> ModelResponse:
        start = time.time()
        model_name = self._get_model(model)
        payload = {
            "model": model_name,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            data = response.json()
        latency = (time.time() - start) * 1000
        return ModelResponse(
            content=data.get("message", {}).get("content", ""),
            model=model_name,
            provider=self.provider_name,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            latency_ms=latency,
        )

    async def generate_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        model_name = self._get_model(model)
        payload = {
            "model": model_name,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt
        input_tokens = 0
        output_tokens = 0
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield StreamChunk(
                            type="content",
                            content=data["message"]["content"],
                            model=model_name,
                            provider=self.provider_name,
                        )
                    if "done" in data and data["done"]:
                        input_tokens = data.get("prompt_eval_count", 0)
                        output_tokens = data.get("eval_count", 0)
        yield StreamChunk(
            type="done",
            model=model_name,
            provider=self.provider_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            done=True,
        )
