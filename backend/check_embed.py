import asyncio
import httpx

async def check():
    api_key = "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"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "input": ["test document content for embedding"],
        "model": "nvidia/nv-embed-v1",
        "encoding_format": "float",
        "input_type": "query",
        "truncate": "NONE",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post("https://integrate.api.nvidia.com/v1/embeddings", json=payload, headers=headers)
            print(f"Status: {r.status_code}")
            if r.status_code != 200:
                print(r.text[:300])
            else:
                data = r.json()
                print(f"OK - dims: {len(data['data'][0]['embedding'])}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(check())
