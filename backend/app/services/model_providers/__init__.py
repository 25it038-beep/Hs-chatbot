from app.services.model_providers.base import ModelProvider, ModelResponse, StreamChunk
from app.services.model_providers.openai import OpenAIProvider
from app.services.model_providers.anthropic import AnthropicProvider
from app.services.model_providers.gemini import GeminiProvider
from app.services.model_providers.ollama import OllamaProvider

__all__ = [
    "ModelProvider", "ModelResponse", "StreamChunk",
    "OpenAIProvider", "AnthropicProvider", "GeminiProvider", "OllamaProvider",
]

PROVIDER_MAP: dict[str, type[ModelProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
    "azure": OpenAIProvider,
    "openrouter": OpenAIProvider,
    "nvidia": OpenAIProvider,
    "lm_studio": OpenAIProvider,
    "sambanova": OpenAIProvider,
}


def get_provider(provider_name: str) -> ModelProvider:
    provider_cls = PROVIDER_MAP.get(provider_name)
    if provider_cls is None:
        raise ValueError(f"Unknown provider: {provider_name}")
    return provider_cls(provider_name)
