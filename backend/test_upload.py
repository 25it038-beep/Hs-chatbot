import urllib.request
import json
import sys

token = sys.argv[1] if len(sys.argv) > 1 else ""

file_content = b"HSBot is a multi-provider AI chat assistant with RAG support. It supports NVIDIA NIM, OpenAI, Anthropic, Google Gemini, Ollama, and more. Users can upload documents and the AI will use them as context."

boundary = b"----WebKitFormBoundary7MA4YWxkTrZu0gW"

body = b"--" + boundary + b"\r\n"
body += b'Content-Disposition: form-data; name="file"; filename="test_doc.txt"\r\n'
body += b"Content-Type: text/plain\r\n\r\n"
body += file_content + b"\r\n"
body += b"--" + boundary + b"--\r\n"

req = urllib.request.Request("http://127.0.0.1:8000/api/files/upload", data=body)
req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary.decode())
req.add_header("Authorization", "Bearer " + token)

try:
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    print(f"Upload OK: filename={data['filename']}, chunks={data['chunk_count']}")
    print(f"Preview: {data['text_preview'][:80]}")
except Exception as e:
    print(f"Upload Error: {e}")
    if hasattr(e, "read"):
        print(e.read().decode())
