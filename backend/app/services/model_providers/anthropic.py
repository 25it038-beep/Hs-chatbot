import time
import json
from typing import AsyncGenerator
from anthropic import AsyncAnthropic
from app.config import settings
from app.services.model_providers.base import ModelProvider, ModelResponse, StreamChunk


class AnthropicProvider(ModelProvider):
    def __init__(self, provider_name: str = "anthropic"):
        self.provider_name = provider_name
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key or "")

    def _get_model(self, model: str | None) -> str:
        return model or settings.anthropic_default_model

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
        system = system_prompt
        kwargs = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        response = await self.client.messages.create(**kwargs)
        latency = (time.time() - start) * 1000
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text
        return ModelResponse(
            content=content,
            model=model_name,
            provider=self.provider_name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
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
        system = system_prompt
        kwargs = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        input_tokens = 0
        output_tokens = 0
        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        yield StreamChunk(
                            type="content",
                            content=event.delta.text,
                            model=model_name,
                            provider=self.provider_name,
                        )
                elif event.type == "message_start":
                    if event.message.usage:
                        input_tokens = event.message.usage.input_tokens
                elif event.type == "message_delta":
                    if event.usage:
                        output_tokens = event.usage.output_tokens
                    if event.delta.stop_reason == "tool_use":
                        pass
        yield StreamChunk(
            type="done",
            model=model_name,
            provider=self.provider_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            done=True,
        )
