from fastapi import APIRouter
from pydantic import BaseModel
from app.services.nvidia.config import NVIDIA_MODELS

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    capabilities: list[str]


def _build_models():
    models = []
    # NVIDIA models
    for key, conf in NVIDIA_MODELS.items():
        models.append({
            "id": key,
            "name": conf["name"],
            "provider": "nvidia",
            "capabilities": conf.get("capabilities", ["chat"]),
        })
    # OpenAI
    models.extend([
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "capabilities": ["chat", "vision", "tools", "json", "streaming"]},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "capabilities": ["chat", "vision", "tools", "json", "streaming"]},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "openai", "capabilities": ["chat", "vision", "tools", "json", "streaming"]},
        {"id": "o1", "name": "o1", "provider": "openai", "capabilities": ["chat", "reasoning", "json"]},
        {"id": "o3-mini", "name": "o3 Mini", "provider": "openai", "capabilities": ["chat", "reasoning", "json"]},
    ])
    # Anthropic
    models.extend([
        {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "provider": "anthropic", "capabilities": ["chat", "vision", "tools", "streaming", "reasoning"]},
        {"id": "claude-haiku-3-5", "name": "Claude Haiku 3.5", "provider": "anthropic", "capabilities": ["chat", "vision", "tools", "streaming"]},
        {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "provider": "anthropic", "capabilities": ["chat", "vision", "tools", "streaming", "reasoning"]},
    ])
    # Gemini
    models.extend([
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "gemini", "capabilities": ["chat", "vision", "tools", "streaming"]},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "gemini", "capabilities": ["chat", "vision", "tools", "streaming", "reasoning"]},
    ])
    # Ollama
    models.extend([
        {"id": "llama3.1", "name": "Llama 3.1", "provider": "ollama", "capabilities": ["chat", "streaming"]},
        {"id": "llama3.2", "name": "Llama 3.2", "provider": "ollama", "capabilities": ["chat", "vision", "streaming"]},
        {"id": "mistral", "name": "Mistral", "provider": "ollama", "capabilities": ["chat", "streaming"]},
        {"id": "codellama", "name": "CodeLlama", "provider": "ollama", "capabilities": ["chat", "streaming"]},
    ])
    return models


AVAILABLE_MODELS = _build_models()

PROVIDERS: list[dict] = [
    {"id": "nvidia", "name": "NVIDIA NIM", "icon": "cpu", "requires_key": True, "models": len([m for m in AVAILABLE_MODELS if m["provider"] == "nvidia"])},
    {"id": "openai", "name": "OpenAI", "icon": "sparkles", "requires_key": True},
    {"id": "anthropic", "name": "Anthropic", "icon": "clover", "requires_key": True},
    {"id": "gemini", "name": "Google Gemini", "icon": "sparkle", "requires_key": True},
    {"id": "ollama", "name": "Ollama (Local)", "icon": "server", "requires_key": False},
    {"id": "azure", "name": "Azure OpenAI", "icon": "cloud", "requires_key": True},
    {"id": "openrouter", "name": "OpenRouter", "icon": "route", "requires_key": True},
    {"id": "lm_studio", "name": "LM Studio", "icon": "monitor", "requires_key": False},
]


@router.get("", response_model=list[ModelInfo])
async def list_models():
    return [ModelInfo(**m) for m in AVAILABLE_MODELS]


@router.get("/providers")
async def list_providers():
    return PROVIDERS


@router.get("/nvidia")
async def list_nvidia_models():
    return [
        {"key": k, **v}
        for k, v in NVIDIA_MODELS.items()
    ]
