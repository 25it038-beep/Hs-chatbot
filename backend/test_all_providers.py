import asyncio
import sys
import os

# Add parent dir to path so we can import app config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.services.model_providers import get_provider

async def test_provider(provider_name: str, model: str | None = None):
    print(f"\n=================== Testing Provider: {provider_name} (Model: {model or 'default'}) ===================")
    try:
        provider = get_provider(provider_name)
        messages = [{"role": "user", "content": "Hello! Please reply in exactly 3 words."}]
        print("Sending request...")
        
        # Test non-streaming generate
        response = await provider.generate(
            messages=messages,
            model=model,
            temperature=0.7,
            max_tokens=50
        )
        print(f"Generate response content: '{response.content}'")
        print(f"Model used: {response.model}")
        print(f"Latency: {response.latency_ms:.2f} ms")
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

async def main():
    print("Settings loaded successfully:")
    print("NVIDIA keys configured:", bool(settings.nvidia_api_keys))
    print("SambaNova key configured:", bool(settings.sambanova_api_key))
    print("Google key configured:", bool(settings.google_api_key))
    print("Groq key configured:", bool(settings.groq_api_key))

    # Test each provider in turn
    if settings.sambanova_api_key:
        await test_provider("sambanova", settings.sambanova_default_model)
    
    if settings.nvidia_api_keys:
        await test_provider("nvidia", settings.nvidia_default_chat_model)

    if settings.google_api_key:
        await test_provider("gemini", settings.google_default_model)
        
    if settings.groq_api_key:
        await test_provider("groq", settings.groq_default_model)

if __name__ == "__main__":
    asyncio.run(main())
