from app.services.nvidia.key_manager import key_manager
print(f"Key count: {len(key_manager.keys)}")
for k in key_manager.keys:
    print(f"  Key: {k.key[:15]}... active={k.is_active} rate_limited={k.is_rate_limited}")

key = key_manager.get_key()
print(f"\nGot key: {key.key[:15] if key else 'None'}...")

# Test making a direct API call with this key
import httpx
import json

payload = {
    "model": "z-ai/glm-5.2",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 5,
    "temperature": 0.1,
    "stream": False
}
headers = {
    "Authorization": f"Bearer {key.key}",
    "Content-Type": "application/json"
}

print("\nTesting direct API call with managed key...")
import sys; sys.stdout.flush()
try:
    r = httpx.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=30
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Content: {data['choices'][0]['message']['content']}")
except httpx.TimeoutException:
    print("TIMEOUT")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
