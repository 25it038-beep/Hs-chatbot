import httpx, json, sys

# Test 1: Backend NVIDIA endpoint
payload = {
    "message": "Say hello in one word",
    "model": "llama-3.3-70b",
    "stream": False,
    "auto_route": False
}

try:
    r = httpx.post(
        "http://localhost:8000/api/nvidia/chat",
        json=payload,
        timeout=60
    )
    print(f"Backend status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Backend error: {e}")

print("\n---\n")

# Test 2: Direct NVIDIA API with the model IDs we use
test_payload = {
    "model": "meta/llama-3.3-70b-instruct",
    "messages": [{"role": "user", "content": "say hi"}],
    "max_tokens": 20,
    "temperature": 0.7,
    "stream": False
}
headers = {
    "Authorization": "Bearer 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",
    "Content-Type": "application/json"
}

try:
    r = httpx.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        json=test_payload,
        headers=headers,
        timeout=60
    )
    print(f"Direct NVIDIA status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        print(f"Content: {content}")
    else:
        print(f"Error: {r.text[:500]}")
except Exception as e:
    print(f"Direct NVIDIA error: {e}")
