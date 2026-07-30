import httpx, json

key = "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"
headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

models = [
    "deepseek-ai/deepseek-v4-pro",
    "deepseek-ai/deepseek-v4-flash",
    "meta/llama-3.3-70b-instruct",
    "mistralai/mistral-large",
    "nvidia/nemotron-4-340b-instruct",
]

for model in models:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5,
    }
    try:
        r = httpx.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            json=payload, headers=headers, timeout=30
        )
        print(f"{model}: HTTP {r.status_code}")
        if r.status_code != 200:
            print(f"  Body: {r.text[:200]}")
        else:
            print(f"  OK: {r.json()['choices'][0]['message']['content'][:50]}")
    except Exception as e:
        print(f"{model}: {type(e).__name__}")
