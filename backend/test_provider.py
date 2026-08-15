import sys
import os
# Add backend to path to import app
sys.path.append(r"C:\Users\BS.Harshan seliyan\OneDrive\Documents\HSBot\backend")

from app.services.nvidia import NvidiaChatProvider
from app.config import settings

print("Testing NVIDIA Provider Initialization...")
try:
    provider = NvidiaChatProvider()
    print("Provider initialized successfully.")
    print("Testing connection with model:", settings.nvidia_default_chat_model)
    
    # Test a small completion
    from openai import AsyncOpenAI
    import asyncio
    
    async def test():
        # The provider uses settings.nvidia_api_keys which should be loaded
        key = settings.nvidia_api_keys.split(",")[0].strip()
        client = AsyncOpenAI(api_key=key, base_url="https://integrate.api.nvidia.com/v1")
        completion = await client.chat.completions.create(
            model=settings.nvidia_default_chat_model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10
        )
        print("Response:", completion.choices[0].message.content)

    asyncio.run(test())
except Exception as e:
    print("Provider Error:", e)
