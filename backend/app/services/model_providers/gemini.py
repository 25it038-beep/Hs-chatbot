import time
from typing import AsyncGenerator
from google import genai
from google.genai import types
from app.config import settings
from app.services.model_providers.base import ModelProvider, ModelResponse, StreamChunk


class GeminiProvider(ModelProvider):
    def __init__(self, provider_name: str = "gemini"):
        self.provider_name = provider_name
        self.client = genai.Client(api_key=settings.google_api_key)

    def _get_model(self, model: str | None) -> str:
        return model or settings.google_default_model

    def _convert_messages(self, messages: list[dict]) -> list[types.Content]:
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
        return contents

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
        contents = self._convert_messages(messages)
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt,
        )
        response = self.client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
        latency = (time.time() - start) * 1000
        return ModelResponse(
            content=response.text or "",
            model=model_name,
            provider=self.provider_name,
            input_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
            output_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
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
        contents = self._convert_messages(messages)
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt,
        )
        response = self.client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=config,
        )
        input_tokens = 0
        output_tokens = 0
        for chunk in response:
            if chunk.usage_metadata:
                input_tokens = chunk.usage_metadata.prompt_token_count or 0
                output_tokens = chunk.usage_metadata.candidates_token_count or 0
            if chunk.text:
                yield StreamChunk(
                    type="content",
                    content=chunk.text,
                    model=model_name,
                    provider=self.provider_name,
                )
        yield StreamChunk(
            type="done",
            model=model_name,
            provider=self.provider_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            done=True,
        )
