"""
Test the WebSocket connection to Render directly, simulating what ws_client.py does.
Run: python scratch/test_ws_live.py
"""
import asyncio
import json
import time
import websockets


async def test_ws():
    uri = "wss://hs-chatbot-2.onrender.com/api/browser/ws"
    headers = {
        "User-Agent": "HS-Bot-Desktop/1.0",
        "Origin": "https://hs-chatbot-2.onrender.com"
    }

    print("[TEST] Connecting to", uri)
    start = time.time()

    try:
        async with websockets.connect(
            uri,
            additional_headers=headers,
            ping_interval=20,       # send WS-level ping every 20s
            ping_timeout=30,        # wait 30s for pong before giving up
            open_timeout=15,
        ) as ws:
            elapsed = time.time() - start
            print("[TEST] Connected in", round(elapsed, 2), "s")

            # Send state update (same as ws_client.py)
            state = {
                "browser_open": False,
                "chrome": "READY",
                "browser_agent": "READY",
                "tabs": [],
                "current_action": None
            }
            await ws.send(json.dumps({"type": "state_update", "state": state}))
            print("[TEST] Sent state_update")

            # Wait for any response for 10s
            print("[TEST] Waiting for messages (10s)...")
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                print("[TEST] Got message:", msg[:200])
            except asyncio.TimeoutError:
                print("[TEST] No message in 10s (expected — server only sends browser_action commands)")

            # Keep alive for 30s to check Render doesn't kill the connection
            print("[TEST] Keeping connection alive for 30s...")
            for i in range(6):
                await asyncio.sleep(5)
                await ws.send(json.dumps({"type": "state_update", "state": state}))
                print("[TEST] Sent heartbeat", i+1, "/ 6")

            print("[TEST] Connection survived 30s! Browser automation WS is working.")
    except Exception as e:
        elapsed = time.time() - start
        print("[FAIL] Connection failed after", round(elapsed, 2), "s:", type(e).__name__, "-", e)


asyncio.run(test_ws())
