"""
Simulate exact frontend request when user types 'open youtube'
"""
import urllib.request
import json

base = "https://hs-chatbot-2.onrender.com"

# 1. Login / get auth token or use default token
# First create a test chat
req = urllib.request.Request(
    base + "/api/chats",
    data=json.dumps({"model": "llama-3.1-70b", "provider": "nvidia"}).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer hsbot_default_access_token"},
    method="POST"
)

try:
    res = urllib.request.urlopen(req)
    chat_data = json.loads(res.read())
    chat_id = chat_data["id"]
    print("[1] Created test chat:", chat_id)
except Exception as e:
    print("[1] Create chat failed:", e)
    chat_id = None

# 2. Send message 'open youtube'
msg_req = urllib.request.Request(
    base + "/api/chats/messages",
    data=json.dumps({
        "message": "open youtube",
        "chat_id": chat_id,
        "model": "llama-3.1-70b",
        "provider": "nvidia",
        "stream": True
    }).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer hsbot_default_access_token"},
    method="POST"
)

try:
    res = urllib.request.urlopen(msg_req)
    print("[2] Streaming response from /api/chats/messages:")
    for line in res:
        line_str = line.decode("utf-8", errors="replace").strip()
        if line_str:
            print("  ", line_str[:120])
except Exception as e:
    print("[2] Send message failed:", e)
