from app.services.nvidia.key_manager import key_manager
import httpx, json

# Test with multiple keys and different models
models_to_test = [
    "meta/llama-3.3-70b-instruct",
    "z-ai/glm-5.2",
    "meta/llama-3.2-11b-vision-instruct",
]

for key in key_manager.keys:
    for model in models_to_test:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
            "temperature": 0.1,
            "stream": False
        }
        headers = {
            "Authorization": f"Bearer {key.key}",
            "Content-Type": "application/json"
        }
        try:
            r = httpx.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=15
            )
            status = r.status_code
            if status == 200:
                content = r.json()["choices"][0]["message"]["content"]
                print(f"OK   key={key.key[:15]} model={model} => '{content}'")
                break
            else:
                print(f"FAIL key={key.key[:15]} model={model} => HTTP {status}: {r.text[:80]}")
        except httpx.TimeoutException:
            print(f"T/O  key={key.key[:15]} model={model}")
        except Exception as e:
            print(f"ERR  key={key.key[:15]} model={model} => {type(e).__name__}")
