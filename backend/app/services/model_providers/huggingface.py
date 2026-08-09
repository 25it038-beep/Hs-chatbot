from app.config import settings
from app.services.model_providers.openai import OpenAIProvider
from openai import AsyncOpenAI

class HuggingFaceProvider(OpenAIProvider):
    def __init__(self, provider_name: str = "huggingface"):
        self.provider_name = provider_name
        self.api_key = settings.huggingface_api_key
        if not self.api_key:
            raise ValueError("Missing HUGGINGFACE_API_KEY")
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://router.huggingface.co/v1",
        )

    def _get_model(self, model: str | None) -> str:
        return model or "deepseek-ai/DeepSeek-V4-Flash-0731"
