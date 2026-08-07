import time
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI
from app.config import settings
from app.services.model_providers.base import ModelProvider, ModelResponse, StreamChunk
from app.services.nvidia.config import NVIDIA_MODELS

NVIDIA_MODEL_MAP = {v["id"]: k for k, v in NVIDIA_MODELS.items()}
NVIDIA_ID_MAP = {k: v["id"] for k, v in NVIDIA_MODELS.items()}


class OpenAIProvider(ModelProvider):
    def __init__(self, provider_name: str = "openai"):
        self.provider_name = provider_name
        api_key = settings.openai_api_key
        base_url = settings.openai_base_url
        if provider_name == "azure":
            api_key = settings.azure_openai_api_key
            base_url = f"{settings.azure_openai_endpoint}/openai/deployments/{settings.azure_openai_deployment}"
        elif provider_name == "openrouter":
            api_key = settings.openrouter_api_key
            base_url = "https://openrouter.ai/api/v1"
        elif provider_name == "nvidia":
            api_key = settings.nvidia_api_keys.split(",")[0].strip() if settings.nvidia_api_keys else ""
            base_url = "https://integrate.api.nvidia.com/v1"
        elif provider_name == "lm_studio":
            api_key = "not-needed"
            base_url = f"{settings.lm_studio_base_url}/v1"
        elif provider_name == "sambanova":
            api_key = settings.sambanova_api_key
            base_url = settings.sambanova_base_url
        if not api_key:
            raise ValueError(
                f"Missing API key for provider '{provider_name}'. "
                f"Set {provider_name.upper()}_API_KEY in the environment."
            )
        self.client = AsyncOpenAI(api_key=api_key or "", base_url=base_url or "")

    def _get_model(self, model: str | None) -> str:
        if not model:
            defaults = {
                "openai": settings.openai_default_model,
                "azure": settings.azure_openai_deployment or "gpt-4o",
                "openrouter": settings.openrouter_default_model or "openai/gpt-4o",
                "nvidia": "z-ai/glm-5.2",
                "lm_studio": settings.ollama_default_model,
                "sambanova": settings.sambanova_default_model or "DeepSeek-V3.2",
            }
            return defaults.get(self.provider_name, settings.openai_default_model)
        if self.provider_name == "nvidia":
            return NVIDIA_ID_MAP.get(model, model)
        return model

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
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        openai_messages.extend(messages)
        kwargs = {
            "model": model_name,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        if self.provider_name == "nvidia":
            model_conf = NVIDIA_MODELS.get(model or "")
            if model_conf and model_conf.get("supports_thinking"):
                kwargs["extra_body"] = {"chat_template_kwargs": {"thinking": True}}
        response = await self.client.chat.completions.create(**kwargs)
        latency = (time.time() - start) * 1000
        return ModelResponse(
            content=response.choices[0].message.content or "",
            model=model,
            provider=self.provider_name,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
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
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        openai_messages.extend(messages)
        kwargs = {
            "model": model_name,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            kwargs["tools"] = tools
        if self.provider_name == "nvidia":
            model_conf = NVIDIA_MODELS.get(model or "")
            if model_conf and model_conf.get("supports_thinking"):
                kwargs["extra_body"] = {"chat_template_kwargs": {"thinking": True}}
        stream = await self.client.chat.completions.create(**kwargs)
        input_tokens = 0
        output_tokens = 0
        async for chunk in stream:
            if chunk.usage:
                input_tokens = chunk.usage.prompt_tokens or 0
                output_tokens = chunk.usage.completion_tokens or 0
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta:
                if delta.content:
                    yield StreamChunk(
                        type="content",
                        content=delta.content,
                        model=model_name,
                        provider=self.provider_name,
                    )
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        yield StreamChunk(
                            type="tool_call",
                            content=tc.model_dump_json(),
                            model=model_name,
                            provider=self.provider_name,
                        )
        yield StreamChunk(
            type="done",
            content="",
            model=model_name,
            provider=self.provider_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            done=True,
        )
