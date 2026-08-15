import json
import urllib.request

BASE = "https://hs-chatbot-2.onrender.com/api"

def http(method, path, body=None, token=None, timeout=180):
    url = BASE + path
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.getcode(), resp
    except urllib.error.HTTPError as e:
        return e.code, e

# 1. Login
code, resp = http("POST", "/auth/login", {"username": "groqtest", "password": "testpass123"}, timeout=30)
if code == 404:
    print("no user - register")
    code, resp = http("POST", "/auth/register", {"email": "groqtest@test.com", "username": "groqtest", "password": "testpass123"}, timeout=30)
print("login/register:", code)
if code not in (200, 201):
    print(resp.read().decode()[:200])
    raise SystemExit
token = json.loads(resp.read())["access_token"]

# 2. Create default chat (should be groq/qwen)
code, resp = http("POST", "/chats", {"title": "Deploy Test"}, token=token, timeout=30)
chat = json.loads(resp.read())
print("create chat:", code, "provider:", chat.get("provider"), "model:", chat.get("model"))
chat_id = chat["id"]

# 3. Send message
req = urllib.request.Request(BASE + "/chats/messages", data=json.dumps({"message": "Say hello in 3 words", "chat_id": chat_id, "stream": False}).encode(), method="POST", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
try:
    resp = urllib.request.urlopen(req, timeout=180)
    raw = resp.read().decode()
    print("chat code:", resp.getcode())
    chunks = [json.loads(l[6:].strip()) for l in raw.splitlines() if l.startswith("data: ") and l[6:].strip() != "[DONE]"]
    content = "".join(c.get("content") or "" for c in chunks if c.get("type") == "content")
    errors = [c.get("content") for c in chunks if c.get("type") == "error"]
    print("content:", repr(content[:200]))
    if errors:
        print("ERRORS:", errors)
except urllib.error.HTTPError as e:
    print("chat HTTP:", e.code, e.read().decode()[:300])
