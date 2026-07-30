import httpx, json

# Test backend NVIDIA chat (non-streaming)
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
        timeout=120
    )
    print(f"Backend status: {r.status_code}")
    content = r.text
    print(f"Response length: {len(content)}")
    print(f"Response preview: {content[:300]}")
except Exception as e:
    print(f"Backend error: {type(e).__name__}: {e}")

print("\n--- Testing streaming ---")

# Test backend NVIDIA chat (streaming)
payload2 = {
    "message": "Count 1 to 3",
    "model": "llama-3.3-70b",
    "stream": True,
    "auto_route": False
}

try:
    with httpx.Client(timeout=120) as client:
        with client.stream("POST", "http://localhost:8000/api/nvidia/chat", json=payload2) as resp:
            print(f"Stream status: {resp.status_code}")
            chunk_count = 0
            for line in resp.iter_lines():
                if line:
                    chunk_count += 1
                    if chunk_count <= 3:
                        print(f"  Chunk {chunk_count}: {line[:100]}")
            print(f"Total chunks: {chunk_count}")
except Exception as e:
    print(f"Stream error: {type(e).__name__}: {e}")
