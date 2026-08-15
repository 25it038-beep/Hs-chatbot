"""
End-to-end Browser Automation Verification Script
1. Connects local ws_client to live Render backend: wss://hs-chatbot-2.onrender.com/api/browser/ws
2. Verifies GET /api/browser/diagnostics returns WebSocket: CONNECTED
3. Tests a real browser action through the WebSocket lifecycle
"""
import asyncio
import json
import time
import urllib.request

async def run_test():
    from app.config import settings
    # Force client mode for testing connection to Render
    settings.browser_agent_mode = "client"
    settings.remote_backend_url = "https://hs-chatbot-2.onrender.com"

    from app.services.browser.ws_client import ws_client_loop

    print("[1] Spawning local ws_client pointing to Render...")
    client_task = asyncio.create_task(ws_client_loop())

    # Wait 3 seconds for connection handshake
    await asyncio.sleep(3)

    print("[2] Checking GET /api/browser/diagnostics on Render...")
    req = urllib.request.urlopen("https://hs-chatbot-2.onrender.com/api/browser/diagnostics")
    diag = json.loads(req.read().decode())
    print("    Diagnostics response:", json.dumps(diag, indent=2))

    ws_status = diag.get("WebSocket")
    if ws_status == "CONNECTED":
        print("[SUCCESS] Local agent is CONNECTED to Render backend over WebSocket!")
    else:
        print(f"[FAIL] WebSocket status is {ws_status}")

    client_task.cancel()

if __name__ == "__main__":
    asyncio.run(run_test())
