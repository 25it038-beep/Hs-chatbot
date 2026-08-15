import json
import urllib.request

BASE = "http://localhost:8000/api"

# Login/Register to get token
req = urllib.request.Request(BASE + "/auth/login", data=json.dumps({"username": "groqtest", "password": "testpass123"}).encode(), method="POST", headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req, timeout=30)
    token = json.loads(resp.read())["access_token"]
except:
    req = urllib.request.Request(BASE + "/auth/register", data=json.dumps({"email": "llama_test@test.com", "username": "llama_test", "password": "testpass123"}).encode(), method="POST", headers={"Content-Type": "application/json"})
    token = json.loads(urllib.request.urlopen(req).read())["access_token"]

# Create chat - no model/provider specified (should default to nvidia/llama-3.3-70b-instruct)
req = urllib.request.Request(BASE + "/chats", data=json.dumps({"title": "Llama Test"}).encode(), method="POST", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
chat = json.loads(urllib.request.urlopen(req).read())
print("Created chat:", chat["provider"], chat["model"])

# Send message
req = urllib.request.Request(BASE + "/chats/messages", data=json.dumps({"message": "Hello Llama, say hi in 3 words.", "chat_id": chat["id"], "stream": False}).encode(), method="POST", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
resp = urllib.request.urlopen(req, timeout=300) # Llama 70B can be slow
raw = resp.read().decode()
chunks = [json.loads(l[6:].strip()) for l in raw.splitlines() if l.startswith("data: ") and l[6:].strip() != "[DONE]"]
content = "".join(c.get("content") or "" for c in chunks if c.get("type") == "content")
print("Response:", repr(content))
print("Model used:", [c.get("model") for c in chunks if c.get("model")][0])
