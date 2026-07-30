import urllib.request, json, sys
token = sys.argv[1]
base = "http://127.0.0.1:8000"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Create chat
req = urllib.request.Request(f"{base}/api/chats", data=json.dumps({"model": "deepseek-v4-flash", "provider": "nvidia"}).encode(), headers=headers)
chat = json.loads(urllib.request.urlopen(req, timeout=30).read())
chat_id = chat["id"]
print(f"Chat: {chat_id}")

# Send message referencing file
body = json.dumps({"message": "[File: test_doc.txt] What is this document about?", "chat_id": chat_id, "model": "deepseek-v4-flash", "stream": False, "auto_route": True})
req = urllib.request.Request(f"{base}/api/nvidia/chat", data=body.encode(), headers=headers)
try:
    resp = urllib.request.urlopen(req, timeout=180)
    data = json.loads(resp.read())
    print(f"Model: {data.get('model')}")
    print(f"Response: {data.get('content', '')[:200]}")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode()[:500])
