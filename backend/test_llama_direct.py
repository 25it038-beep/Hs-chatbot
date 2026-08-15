import httpx
import os

key = "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"
models = ["meta/llama-3.1-70b-instruct", "meta/llama-3.3-70b-instruct"]

for model in models:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "say hello in 2 words"}],
        "max_tokens": 10,
        "temperature": 0.1,
        "stream": False
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    print(f"\nTesting {model}...")
    try:
        r = httpx.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=15
        )
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print(f"Response: {r.json()['choices'][0]['message']['content']}")
        else:
            print(f"Error Response: {r.text}")
    except Exception as e:
        print(f"Error: {e}")
