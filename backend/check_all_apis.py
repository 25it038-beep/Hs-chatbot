import subprocess
import time
import sys
import os
import json
import urllib.request
import urllib.error
import urllib.parse

BACKEND_DIR = r"C:\Users\BS.Harshan seliyan\OneDrive\Documents\HSBot\backend"
BASE = "http://127.0.0.1:8000/api"
LOG = r"C:\Users\BS857E~1.HAR\AppData\Local\Temp\api_check_log.txt"

results = []

def record(name, ok, detail=""):
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))

def http(method, path, body=None, token=None, timeout=60, headers=None, raw=False):
    url = BASE + path
    h = {"Content-Type": "application/json"} if body is not None else {}
    if headers:
        h.update(headers)
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        code = resp.getcode()
        if raw:
            return code, resp.read()
        ct = resp.headers.get("Content-Type", "")
        if "application/json" in ct:
            return code, json.loads(resp.read())
        return code, resp.read().decode()
    except urllib.error.HTTPError as e:
        ct = e.headers.get("Content-Type", "")
        if raw:
            return e.code, e.read()
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, e.read().decode()
    except urllib.error.URLError as e:
        return 0, str(e)

def wait_ready(timeout=30):
    for _ in range(timeout):
        try:
            urllib.request.urlopen(BASE + "/health", timeout=3)
            return True
        except Exception:
            time.sleep(1)
    return False

# Start server
p = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=BACKEND_DIR,
    stdout=open(LOG, "w"),
    stderr=subprocess.STDOUT,
)

print("Starting backend...")
if not wait_ready():
    print("SERVER FAILED TO START")
    print(open(LOG).read() if os.path.exists(LOG) else "no log")
    p.terminate()
    sys.exit(1)
print("Backend is up.\n")

# 1. Health
code, data = http("GET", "/health")
record("GET /health", code == 200 and data.get("status") == "ok", str(data))

# 2. Register a user
uid = time.strftime("%H%M%S")
reg_body = {"email": f"apitest{uid}@test.com", "username": f"apitest{uid}", "password": "testpass123"}
code, data = http("POST", "/auth/register", reg_body)
record("POST /auth/register", code == 200 and "access_token" in data, str(data.get("user", data)))
token = data.get("access_token", "")

# 3. Login
code, data = http("POST", "/auth/login", {"username": reg_body["username"], "password": "testpass123"})
record("POST /auth/login", code == 200 and "access_token" in data, str(data.get("token_type", data)))
token = token or data.get("access_token", "")

# 4. Get me
code, data = http("GET", "/auth/me", token=token)
record("GET /auth/me", code == 200 and data.get("username") == reg_body["username"], str(data.get("username")))

# 5. Models list
code, data = http("GET", "/models", token=token)
record("GET /models", code == 200 and isinstance(data, list), f"{len(data)} providers")

# 6. NVIDIA models
code, data = http("GET", "/models/nvidia", token=token)
record("GET /models/nvidia", code == 200 and isinstance(data, list), f"{len(data)} models")

# 7. NVIDIA usage
code, data = http("GET", "/nvidia/usage", token=token)
record("GET /nvidia/usage", code == 200 and "total_keys" in data, str(data.get("total_keys")))

# 8. NVIDIA route
code, data = http("GET", "/nvidia/route?message=" + urllib.parse.quote("write python code"), token=token)
record("GET /nvidia/route", code == 200 and "model" in data, f"task={data.get('task')} model={data.get('model')}")

# 9. Create chat
code, data = http("POST", "/chats", {"model": "glm-5.2", "provider": "nvidia", "title": "API Test"}, token=token)
record("POST /chats", code == 200 and data.get("id"), str(data.get("id", data)))
chat_id = data.get("id", "")

# 10. List chats
code, data = http("GET", "/chats", token=token)
record("GET /chats", code == 200 and isinstance(data, list), f"{len(data)} chats")

# 11. Get chat
code, data = http("GET", f"/chats/{chat_id}", token=token)
record("GET /chats/{id}", code == 200 and data.get("id") == chat_id, str(data.get("title")))

# 12. Get messages (empty)
code, data = http("GET", f"/chats/{chat_id}/messages", token=token)
record("GET /chats/{id}/messages", code == 200 and isinstance(data, list), f"{len(data)} messages")

# 13. NVIDIA chat (non-streaming)
code, data = http("POST", "/nvidia/chat", {"message": "Say hello in 3 words", "model": "glm-5.2", "stream": False, "auto_route": False, "chat_id": chat_id}, token=token, timeout=300)
ok = code == 200 and isinstance(data, dict) and data.get("content")
record("POST /nvidia/chat (non-stream)", ok, f"model={data.get('model')} '{str(data.get('content'))[:40]}'")

# 14. Chat message via /chats/messages
code, data = http("POST", "/chats/messages", {"message": "hi", "chat_id": chat_id, "model": "glm-5.2", "provider": "nvidia", "stream": False}, token=token, timeout=300)
record("POST /chats/messages", code in (200, 201) or (isinstance(data, dict) and data.get("content")), str(data)[:60])

# 15. Streaming chat (check it returns SSE)
code, raw = http("POST", "/nvidia/chat", {"message": "Say hi", "model": "glm-5.2", "stream": True, "auto_route": False}, token=token, timeout=300, raw=True)
record("POST /nvidia/chat (stream)", code == 200 and b"data:" in raw, f"first bytes: {raw[:40]}")

# 16. NVIDIA embeddings
code, data = http("POST", "/nvidia/embeddings", {"texts": ["hello world"], "model": "nv-embed-v1", "input_type": "query"}, token=token, timeout=60)
record("POST /nvidia/embeddings", code == 200 and len(data.get("embeddings", [])) > 0, f"dims={data.get('dimensions')}")

# 17. Upload a file (requires multipart)
boundary = "----APIChkBoundary"
content = b"HSBot API test document content for upload."
mp_body = b"--" + boundary.encode() + b"\r\n"
mp_body += b'Content-Disposition: form-data; name="file"; filename="api_test.txt"\r\n'
mp_body += b"Content-Type: text/plain\r\n\r\n"
mp_body += content + b"\r\n"
mp_body += b"--" + boundary.encode() + b"--\r\n"
url = BASE + "/files/upload"
req = urllib.request.Request(url, data=mp_body, method="POST", headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Authorization": f"Bearer {token}"})
try:
    resp = urllib.request.urlopen(req, timeout=60)
    fdata = json.loads(resp.read())
    record("POST /files/upload", resp.getcode() == 200 and fdata.get("chunk_count") is not None, f"chunks={fdata.get('chunk_count')} preview={str(fdata.get('text_preview'))[:30]}")
except urllib.error.HTTPError as e:
    record("POST /files/upload", False, f"HTTP {e.code} {e.read()[:100]}")

# 18. Delete chat
code, data = http("DELETE", f"/chats/{chat_id}", token=token)
record("DELETE /chats/{id}", code in (200, 204), f"code={code}")

# 19. Auth error case - no token on protected endpoint
code, data = http("GET", "/chats")
record("Auth required (no token)", code == 401, f"code={code}")

# Summary
print("\n=== SUMMARY ===")
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"{passed}/{total} passed")
for name, ok, detail in results:
    if not ok:
        print(f"  FAILED: {name} - {detail}")

p.terminate()

if __name__ == "__main__":
    pass