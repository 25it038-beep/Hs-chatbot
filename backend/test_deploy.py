import json
import urllib.request

BASE = "https://hs-chatbot-2.onrender.com/api"

def http(method, path, body=None, token=None, timeout=60):
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

code, resp = http("GET", "/models/providers")
print("providers:", code, resp.read().decode()[:300])
