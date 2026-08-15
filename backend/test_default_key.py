import httpx

key = "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"

payload = {
    "model": "meta/llama-3.1-70b-instruct",
    "messages": [{"role": "user", "content": "say hello"}],
    "max_tokens": 10,
    "temperature": 0.1,
    "stream": False
}
headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

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
