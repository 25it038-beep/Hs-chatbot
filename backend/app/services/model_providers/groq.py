from groq import Groq
from typing import AsyncGenerator
from app.config import settings
from app.services.model_providers.base import ModelProvider, ModelResponse, StreamChunk
import time

class GroqProvider(ModelProvider):
    def __init__(self, provider_name: str = "groq"):
        self.provider_name = provider_name
        self.api_key = settings.groq_api_key
        if not self.api_key:
            raise ValueError("Missing GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key)

    def _get_model(self, model: str | None) -> str:
        return model or settings.groq_default_model or "qwen/qwen3.6-27b"

    async def generate(self, messages: list[dict], model: str | None = None, system_prompt: str | None = None, temperature: float = 0.7, max_tokens: int = 4096, tools: list[dict] | None = None) -> ModelResponse:
        start = time.time()
        model_name = self._get_model(model)
        
        # Groq client is synchronous. In production, consider running in executor.
        completion = self.client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": system_prompt}] + messages if system_prompt else messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return ModelResponse(
            content=completion.choices[0].message.content or "",
            model=model_name,
            provider=self.provider_name,
            input_tokens=completion.usage.prompt_tokens,
            output_tokens=completion.usage.completion_tokens,
            latency_ms=(time.time() - start) * 1000
        )

    async def generate_stream(self, messages: list[dict], model: str | None = None, system_prompt: str | None = None, temperature: float = 0.7, max_tokens: int = 4096, tools: list[dict] | None = None) -> AsyncGenerator[StreamChunk, None]:
        model_name = self._get_model(model)
        
        stream = self.client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": system_prompt}] + messages if system_prompt else messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield StreamChunk(type="content", content=chunk.choices[0].delta.content, model=model_name, provider=self.provider_name)
        
        yield StreamChunk(type="done", content="", model=model_name, provider=self.provider_name, done=True)
