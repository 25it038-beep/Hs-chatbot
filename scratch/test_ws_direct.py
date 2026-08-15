import asyncio
import json
import ssl
import sys
import websockets

async def run_direct_test(uri):
    print("Connecting...")
    
    # Setup standard TLS/SSL verification
    if uri.startswith("wss://"):
        ssl_context = ssl.create_default_context()
        print("TLS: OK")
    else:
        ssl_context = None
        print("TLS: Not required (HTTP/WS)")
        
    headers = {
        "User-Agent": "HS-Bot-Desktop/1.0",
        "Origin": "https://hs-chatbot-2.onrender.com"
    }
    
    try:
        async with websockets.connect(uri, additional_headers=headers, ssl=ssl_context) as ws:
            print("Handshake: OK")
            print("WebSocket: CONNECTED")
            
            ping_msg = {"type": "ping"}
            print("Sending ping...")
            await ws.send(json.dumps(ping_msg))
            
            response_str = await ws.recv()
            try:
                resp = json.loads(response_str)
                print(f"Received: {resp.get('type')}")
            except Exception:
                print(f"Received raw: {response_str}")
                
            print("Closing...")
            print("SUCCESS")
            return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    uri = "wss://hs-chatbot-2.onrender.com/api/browser/ws"
    if len(sys.argv) > 1:
        uri = sys.argv[1]
    
    asyncio.run(run_direct_test(uri))
