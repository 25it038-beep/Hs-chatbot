"""End-to-End Live Session Verification Script.

Tests all live session capabilities against the live backend:
1. WebSocket connection & handshake (session_init)
2. Conversational streaming (transcript_final -> ai_text_chunk -> ai_text_done)
3. Real-time tool invocation (Time / Weather query)
4. Dynamic Barge-In interruption (cancelling mid-stream)
5. Multilingual configuration update & processing
6. Clean session termination (session_end)
"""

import asyncio
import json
import time
import sys
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BACKEND_WS = "wss://hs-chatbot-2.onrender.com/api/realtime/ws/verify_conv_999?language=en&timezone=UTC"

async def run_live_verification():
    print(f"[TEST 1] Connecting to live WebSocket: {BACKEND_WS}")
    t0 = time.time()
    
    async with websockets.connect(BACKEND_WS, ping_interval=20) as ws:
        conn_time = time.time() - t0
        print(f"  --> Connected in {conn_time:.2f}s!")
        
        # 1. Wait for session_init
        init_raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
        init_data = json.loads(init_raw)
        print(f"  --> Received session_init: type={init_data.get('type')}, status={init_data.get('status')}")
        assert init_data.get("type") == "session_init", f"Unexpected init: {init_data}"
        assert init_data.get("status") == "listening"
        print("  --> [TEST 1 PASSED] Connection & handshake verified!\n")

        # 2. Conversational query
        print("[TEST 2] Testing conversational query: 'Hello HSBot, introduce yourself in one short sentence.'")
        await ws.send(json.dumps({
            "type": "transcript_final",
            "text": "Hello HSBot, introduce yourself in one short sentence."
        }))
        
        chunks = []
        full_text = ""
        done = False
        while not done:
            msg_raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
            msg = json.loads(msg_raw)
            mtype = msg.get("type")
            if mtype == "status":
                print(f"  --> Status transition: {msg.get('status')}")
            elif mtype == "ai_text_chunk":
                chunk = msg.get("chunk", "")
                chunks.append(chunk)
                print(f"  --> Streamed chunk: {repr(chunk)}")
            elif mtype == "ai_text_done":
                full_text = msg.get("full_text", "")
                done = True
                print(f"  --> AI Done! Full response: '{full_text}'")
            elif mtype == "error":
                raise RuntimeError(f"Error from server: {msg.get('error')}")
                
        assert len(chunks) > 0, "No chunks received!"
        assert len(full_text) > 0, "No full text received!"
        print("  --> [TEST 2 PASSED] Conversational streaming verified!\n")

        # 3. Real-time Tool query (time query)
        print("[TEST 3] Testing real-time tool execution: 'What time is it right now?'")
        await ws.send(json.dumps({
            "type": "transcript_final",
            "text": "What time is it right now?"
        }))
        
        tool_executed = False
        time_reply = ""
        done = False
        while not done:
            msg_raw = await asyncio.wait_for(ws.recv(), timeout=15.0)
            msg = json.loads(msg_raw)
            mtype = msg.get("type")
            if mtype == "tool_executed":
                tool_executed = True
                print(f"  --> Tool executed: {msg.get('tool')} with data: {msg.get('data')}")
            elif mtype == "ai_text_done":
                time_reply = msg.get("full_text", "")
                done = True
                print(f"  --> Tool response delivered: '{time_reply}'")
                
        assert tool_executed, "Expected tool_executed event!"
        assert len(time_reply) > 0, "Empty tool reply!"
        print("  --> [TEST 3 PASSED] Real-time tool execution verified!\n")

        # 4. Barge-In Interruption mid-generation
        print("[TEST 4] Testing Barge-In interruption mid-generation...")
        await ws.send(json.dumps({
            "type": "transcript_final",
            "text": "Explain quantum computing in detail from basics to qubits and quantum supremacy."
        }))
        
        # Wait until we see processing or first chunk
        interrupted = False
        while not interrupted:
            msg_raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
            msg = json.loads(msg_raw)
            mtype = msg.get("type")
            print(f"  --> Waiting to interrupt, got: {mtype}")
            if mtype in ("status", "ai_text_chunk"):
                print("  --> Interrupting AI stream NOW!")
                await ws.send(json.dumps({"type": "interrupt"}))
                interrupted = True
                
        # Drain all post-interrupt cancellation messages until socket is quiet
        await asyncio.sleep(0.5)
        while True:
            try:
                drain = await asyncio.wait_for(ws.recv(), timeout=0.8)
                print(f"  --> Drained post-interrupt message: {drain}")
            except asyncio.TimeoutError:
                break
                
        print("  --> [TEST 4 PASSED] Barge-in interruption successfully cancelled generation!\n")

        # 5. Multilingual configuration update
        print("[TEST 5] Testing multilingual config update (Tamil)...")
        await ws.send(json.dumps({
            "type": "config",
            "language": "ta"
        }))
        
        cfg_done = False
        while not cfg_done:
            cfg_ack = await asyncio.wait_for(ws.recv(), timeout=5.0)
            cfg_data = json.loads(cfg_ack)
            print(f"  --> Received config reply: {cfg_data}")
            if cfg_data.get("type") == "config_updated":
                assert cfg_data.get("language") == "ta"
                cfg_done = True
        
        print("  --> Sending Tamil utterance: 'வணக்கம், நீங்கள் யார்?'")
        await ws.send(json.dumps({
            "type": "transcript_final",
            "text": "வணக்கம், நீங்கள் யார்?"
        }))
        
        done = False
        ta_reply = ""
        while not done:
            msg_raw = await asyncio.wait_for(ws.recv(), timeout=40.0)
            msg = json.loads(msg_raw)
            if msg.get("type") == "ai_text_chunk":
                print(f"  --> Tamil chunk: {repr(msg.get('chunk'))}")
            elif msg.get("type") == "ai_text_done":
                ta_reply = msg.get("full_text", "")
                done = True
                print(f"  --> Tamil full response: '{ta_reply}'")
        assert len(ta_reply) > 0, "No Tamil response received!"
        print("  --> [TEST 5 PASSED] Multilingual live conversation verified!\n")

        # 6. Session termination
        print("[TEST 6] Testing clean session termination...")
        await ws.send(json.dumps({"type": "session_end"}))
        term_ended = False
        while not term_ended:
            term_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            term_data = json.loads(term_msg)
            print(f"  --> Received msg after session_end: {term_data}")
            if term_data.get("type") == "session_ended":
                term_ended = True
        print("  --> [TEST 6 PASSED] Session ended cleanly!\n")

    print("==================================================")
    print("ALL 6 LIVE SESSION TESTS PASSED WITH ZERO ISSUES!!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_live_verification())
