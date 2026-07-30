import httpx, json, sys

# Test DeepSeek V4 Flash (faster model) with a very short request
test_payload = {
    "model": "deepseek-ai/deepseek-v4-flash",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 5,
    "temperature": 0.1,
    "stream": False
}
headers = {
    "Authorization": "Bearer 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",
    "Content-Type": "application/json"
}

print("Testing DeepSeek V4 Flash...")
sys.stdout.flush()
try:
    r = httpx.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        json=test_payload,
        headers=headers,
        timeout=30
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        print(f"Content: '{content}'")
        print(f"Usage: {data.get('usage', {})}")
    else:
        print(f"Error body: {r.text[:500]}")
except httpx.TimeoutException:
    print("TIMEOUT after 30s")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
