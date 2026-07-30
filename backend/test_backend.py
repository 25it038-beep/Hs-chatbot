import httpx, json

# Test backend with the fastest model
payload = {
    "message": "hi",
    "model": "deepseek-v4-pro",
    "stream": False,
    "auto_route": False,
    "max_tokens": 5,
    "temperature": 0.1
}

print(f"Testing backend with model: {payload['model']}")
try:
    r = httpx.post(
        "http://localhost:8000/api/nvidia/chat",
        json=payload,
        timeout=30
    )
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except httpx.TimeoutException:
    print("TIMEOUT after 30s")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
