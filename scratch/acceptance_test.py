"""
HS Bot End-to-End Acceptance Test
Tests all the required acceptance criteria against the deployed Render backend.

Run:  python scratch/acceptance_test.py
"""
import json
import http.client
import ssl
import time
import urllib.request
import urllib.error

BASE = "hs-chatbot-2.onrender.com"
CONTEXT = ssl.create_default_context()

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
WARN = "\033[33mWARN\033[0m"


def test(label, ok, detail=""):
    status = PASS if ok else FAIL
    suffix = " | " + detail if detail else ""
    print(label.ljust(55), status + suffix)
    return ok


results = []


# ─── 1. Basic Health ──────────────────────────────────────────────────────────
try:
    r = urllib.request.urlopen("https://" + BASE + "/api/health", timeout=20)
    data = json.loads(r.read())
    commit = data.get("commit", "?")
    results.append(test("1. GET /api/health", data.get("status") == "ok", "commit=" + commit))
except Exception as e:
    results.append(test("1. GET /api/health", False, str(e)))

# ─── 2. /api/health/full ──────────────────────────────────────────────────────
try:
    r = urllib.request.urlopen("https://" + BASE + "/api/health/full", timeout=20)
    data = json.loads(r.read())
    providers = data.get("providers", {})
    browser = data.get("browser", {})
    results.append(test("2. GET /api/health/full", "providers" in data,
                        "nvidia=" + str(providers.get("nvidia", {}).get("configured")) +
                        " sambanova=" + str(providers.get("sambanova", {}).get("configured")) +
                        " browser_mode=" + browser.get("agent_mode", "?")))
except Exception as e:
    results.append(test("2. GET /api/health/full", False, str(e)))


def _options(path, origin="https://hs-chatbot-2.onrender.com"):
    conn = http.client.HTTPSConnection(BASE, context=CONTEXT, timeout=15)
    conn.request("OPTIONS", path, headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })
    resp = conn.getresponse()
    body = resp.read(500).decode(errors="replace")
    hdrs = dict(resp.getheaders())
    conn.close()
    return resp.status, hdrs, body


# ─── 3. OPTIONS /api/browser/state ───────────────────────────────────────────
try:
    status, hdrs, body = _options("/api/browser/state")
    ok = status < 300
    allow_origin = hdrs.get("access-control-allow-origin", "MISSING")
    results.append(test("3. OPTIONS /api/browser/state", ok,
                        "status=" + str(status) + " allow_origin=" + allow_origin + (" | " + body[:80] if not ok else "")))
except Exception as e:
    results.append(test("3. OPTIONS /api/browser/state", False, str(e)))

# ─── 4. OPTIONS /api/browser/diagnostics ─────────────────────────────────────
try:
    status, hdrs, body = _options("/api/browser/diagnostics")
    ok = status < 300
    allow_origin = hdrs.get("access-control-allow-origin", "MISSING")
    results.append(test("4. OPTIONS /api/browser/diagnostics", ok,
                        "status=" + str(status) + " allow_origin=" + allow_origin + (" | " + body[:80] if not ok else "")))
except Exception as e:
    results.append(test("4. OPTIONS /api/browser/diagnostics", False, str(e)))

# ─── 5. GET /api/browser/state ───────────────────────────────────────────────
try:
    r = urllib.request.urlopen("https://" + BASE + "/api/browser/state", timeout=15)
    data = json.loads(r.read())
    results.append(test("5. GET /api/browser/state (no auth)", True,
                        "connected=" + str(data.get("connected", data.get("browser_open", "?")))))
except urllib.error.HTTPError as e:
    if e.code == 401:
        results.append(test("5. GET /api/browser/state (no auth)", None,
                            "401 (auth required - need JWT token to access)"))
    else:
        results.append(test("5. GET /api/browser/state (no auth)", False, "HTTP " + str(e.code)))
except Exception as e:
    results.append(test("5. GET /api/browser/state (no auth)", False, str(e)))

# ─── 6. SambaNova provider key configured ─────────────────────────────────────
try:
    r = urllib.request.urlopen("https://" + BASE + "/api/health/full", timeout=20)
    data = json.loads(r.read())
    samba = data.get("providers", {}).get("sambanova", {})
    configured = samba.get("configured", False)
    results.append(test("6. SambaNova API key configured on Render",
                        configured,
                        "configured=" + str(configured) + " (if False, set SAMBANOVA_API_KEY in Render dashboard)"))
except Exception as e:
    results.append(test("6. SambaNova API key configured on Render", False, str(e)))

# ─── 7. NVIDIA API key configured ────────────────────────────────────────────
try:
    r = urllib.request.urlopen("https://" + BASE + "/api/health/full", timeout=20)
    data = json.loads(r.read())
    nvidia = data.get("providers", {}).get("nvidia", {})
    configured = nvidia.get("configured", False)
    results.append(test("7. NVIDIA API key configured on Render",
                        configured,
                        "configured=" + str(configured) + " (if False, set NVIDIA_API_KEYS in Render dashboard)"))
except Exception as e:
    results.append(test("7. NVIDIA API key configured on Render", False, str(e)))

# ─── 8. WebSocket connection test ────────────────────────────────────────────
# Tests that the WS endpoint exists and accepts upgrade
try:
    import socket
    sock = socket.create_connection((BASE, 443), timeout=10)
    ctx = ssl.create_default_context()
    wrapped = ctx.wrap_socket(sock, server_hostname=BASE)

    # Send WebSocket upgrade handshake
    import base64, os
    key = base64.b64encode(os.urandom(16)).decode()
    request = (
        "GET /api/browser/ws HTTP/1.1\r\n"
        "Host: " + BASE + "\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: " + key + "\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "Origin: https://" + BASE + "\r\n"
        "\r\n"
    )
    wrapped.send(request.encode())
    wrapped.settimeout(5)
    resp = wrapped.recv(4096).decode(errors="replace")
    wrapped.close()

    is_101 = "101 Switching Protocols" in resp
    results.append(test("8. WebSocket /api/browser/ws upgrade", is_101,
                        "101 upgrade" if is_101 else "resp=" + resp[:120]))
except Exception as e:
    results.append(test("8. WebSocket /api/browser/ws upgrade", False, str(e)))


# ─── Summary ──────────────────────────────────────────────────────────────────
passed = sum(1 for r in results if r is True)
failed = sum(1 for r in results if r is False)
total = len(results)
print()
print("=" * 65)
print("Results: " + str(passed) + "/" + str(total) + " passed, " + str(failed) + " failed")
print()
if failed > 0:
    print("IMPORTANT: Failed tests need attention.")
    print("  - CORS failures: fix middleware or check Render CORS_ORIGINS env var")
    print("  - Provider failures: set API keys in Render dashboard environment variables")
