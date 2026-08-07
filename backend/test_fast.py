from app.services.nvidia.key_manager import key_manager
import httpx, json

key = key_manager.get_key()
if not key:
    print("No key available!")
    exit()

print(f"Using key: {key.key[:15]}...")

# Test with flash model (fastest)
payload = {
    "model": "z-ai/glm-5.2",
    "messages": [{"role": "user", "content": "say hello in one word"}],
    "max_tokens": 10,
    "stream": False
}
headers = {
    "Authorization": f"Bearer {key.key}",
    "Content-Type": "application/json"
}

import sys
sys.stdout.flush()
try:
    r = httpx.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=30
    )
    print(f"Status: {r.status_code}")
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    print(f"Content: {content}")
    key_manager.record_success(key)
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    key_manager.record_failure(key, str(e))

print(f"\nKey stats: active={key.is_active}, rate_limited={key.is_rate_limited}")
