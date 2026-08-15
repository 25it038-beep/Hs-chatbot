from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "HSBot"
    app_version: str = "1.0.0"
    app_env: str = "development"
    secret_key: str = "change-this-to-a-random-secret-key"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    database_url: str = "sqlite+aiosqlite:///./data/hsbot.db"

    redis_url: str = "redis://localhost:6379/0"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "hsbot_docs"

    nvidia_api_keys: str = "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"
    nvidia_default_chat_model: str = "llama-3.1-70b"
    nvidia_default_code_model: str = "glm-coder"
    nvidia_default_vision_model: str = "nemotron-vl"
    nvidia_default_image_model: str = "nemotron-vl"
    nvidia_default_embed_model: str = "nv-embed-v1"

    # NVIDIA Reliability Configuration
    nvidia_max_retries: int = 3
    nvidia_timeout_seconds: int = 60
    nvidia_connection_timeout_seconds: int = 10
    nvidia_max_concurrent_requests: int = 5
    nvidia_retry_base_delay: float = 1.0
    nvidia_retry_max_delay: float = 30.0
    nvidia_circuit_breaker_threshold: int = 5
    nvidia_circuit_breaker_cooldown: int = 30
    nvidia_rate_limit_cooldown: int = 60

    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_default_model: str = "gpt-4o"

    groq_api_key: Optional[str] = None
    groq_default_model: str = "llama-3.3-70b-versatile"

    huggingface_api_key: Optional[str] = None

    anthropic_api_key: Optional[str] = None
    anthropic_default_model: str = "claude-sonnet-4-20250514"

    google_api_key: Optional[str] = None
    google_default_model: str = "gemini-flash-latest"

    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.1"

    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment: Optional[str] = None

    openrouter_api_key: Optional[str] = None
    openrouter_default_model: Optional[str] = None

    lm_studio_base_url: str = "http://localhost:1234"

    sambanova_api_key: Optional[str] = None
    sambanova_base_url: str = "https://api.sambanova.ai/v1"
    sambanova_default_model: str = "Meta-Llama-3.3-70B-Instruct"

    cloudflare_gateway_api_key: Optional[str] = None
    cloudflare_gateway_account_id: str = "21e5f9f23e1d60cb56bf1200e89255f3"
    cloudflare_gateway_slug: str = "default"
    cloudflare_gateway_default_model: str = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

    upload_dir: str = "./data/uploads"
    max_file_size_mb: int = 50
    remote_backend_url: Optional[str] = "https://hs-chatbot-2.onrender.com"
    browser_ws_token: str = ""

    # Controls browser agent role:
    # 'server' = this process is the cloud backend (Render) — do NOT start a WS client
    # 'client' = this process is the local Windows desktop agent — connect to remote_backend_url
    # Default is 'server' so Render never accidentally connects to itself.
    browser_agent_mode: str = "server"

    cors_origins: str = "*"

    @property
    def browser_ws_auth_token(self) -> str:
        if self.browser_ws_token:
            return self.browser_ws_token
        base = (self.secret_key or "hsbot").strip()
        import hashlib
        return hashlib.sha256(f"{base}:browser-ws".encode("utf-8")).hexdigest()[:32]

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins or "*" in [o.strip() for o in self.cors_origins.split(",")]:
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs("./data", exist_ok=True)
