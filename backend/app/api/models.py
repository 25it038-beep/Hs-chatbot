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
        {"id": "gemini-flash-latest", "name": "Gemini Flash", "provider": "gemini", "capabilities": ["chat", "vision", "tools", "streaming"]},
        {"id": "gemini-flash", "name": "Gemini 2.5 Flash", "provider": "gemini", "capabilities": ["chat", "vision", "tools", "streaming"]},
        {"id": "gemini-pro", "name": "Gemini Pro", "provider": "gemini", "capabilities": ["chat", "vision", "tools", "streaming", "reasoning"]},
    ])
    # Ollama
    models.extend([
        {"id": "llama3.1", "name": "Llama 3.1", "provider": "ollama", "capabilities": ["chat", "streaming"]},
        {"id": "llama3.2", "name": "Llama 3.2", "provider": "ollama", "capabilities": ["chat", "vision", "streaming"]},
        {"id": "mistral", "name": "Mistral", "provider": "ollama", "capabilities": ["chat", "streaming"]},
        {"id": "codellama", "name": "CodeLlama", "provider": "ollama", "capabilities": ["chat", "streaming"]},
    ])
    # SambaNova
    models.extend([
        {"id": "Meta-Llama-3.3-70B-Instruct", "name": "Meta Llama 3.3 70B (Fast)", "provider": "sambanova", "capabilities": ["chat", "streaming", "tools"]},
        {"id": "DeepSeek-V3.2", "name": "DeepSeek V3.2", "provider": "sambanova", "capabilities": ["chat", "streaming", "tools"]},
        {"id": "DeepSeek-V3.1", "name": "DeepSeek V3.1", "provider": "sambanova", "capabilities": ["chat", "streaming", "tools"]},
        {"id": "MiniMax-M2.7", "name": "MiniMax M2.7", "provider": "sambanova", "capabilities": ["chat", "streaming", "tools"]},
        {"id": "gemma-4-31B-it", "name": "Gemma 4 31B", "provider": "sambanova", "capabilities": ["chat", "streaming", "tools"]},
        {"id": "gpt-oss-120b", "name": "GPT-OSS 120B", "provider": "sambanova", "capabilities": ["chat", "streaming", "tools"]},
    ])
    # Cloudflare AI Gateway
    models.extend([
        {"id": "@cf/meta/llama-3.3-70b-instruct-fp8-fast", "name": "Llama 3.3 70B (Workers AI)", "provider": "cloudflare", "capabilities": ["chat", "streaming"]},
        {"id": "@cf/meta/llama-3.2-3b-instruct", "name": "Llama 3.2 3B (Workers AI)", "provider": "cloudflare", "capabilities": ["chat", "streaming"]},
        {"id": "@cf/qwen/qwen2.5-coder-32b-instruct", "name": "Qwen 2.5 Coder 32B (Workers AI)", "provider": "cloudflare", "capabilities": ["chat", "streaming"]},
        {"id": "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b", "name": "DeepSeek R1 Distill (Workers AI)", "provider": "cloudflare", "capabilities": ["chat", "reasoning", "streaming"]},
    ])
    # Groq
    models.extend([
        {"id": "qwen/qwen3.6-27b", "name": "Qwen 3.6 27B", "provider": "groq", "capabilities": ["chat", "streaming", "reasoning"]},
        {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B Versatile", "provider": "groq", "capabilities": ["chat", "streaming", "tools"]},
        {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant", "provider": "groq", "capabilities": ["chat", "streaming", "tools"]},
        {"id": "llama3-70b-8192", "name": "Llama 3 70B", "provider": "groq", "capabilities": ["chat", "streaming", "tools"]},
        {"id": "llama3-8b-8192", "name": "Llama 3 8B", "provider": "groq", "capabilities": ["chat", "streaming", "tools"]},
        {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "provider": "groq", "capabilities": ["chat", "streaming", "tools"]},
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
    {"id": "sambanova", "name": "SambaNova", "icon": "zap", "requires_key": True},
    {"id": "cloudflare", "name": "Cloudflare Gateway", "icon": "cloud", "requires_key": True},
    {"id": "groq", "name": "Groq", "icon": "zap", "requires_key": True},
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
