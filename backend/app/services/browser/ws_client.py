import asyncio
import json
import logging
from typing import Optional
import websockets
from app.config import settings
from app.services.browser.agent import browser_agent, BrowserIntent

logger = logging.getLogger("hsbot.browser.ws_client")
_client_task: Optional[asyncio.Task] = None


async def ws_client_loop():
    if not settings.remote_backend_url:
        logger.info("No remote_backend_url configured. WebSocket client disabled.")
        return

    # Convert HTTPS/HTTP to WSS/WS
    uri = settings.remote_backend_url.replace("https://", "wss://").replace("http://", "ws://") + "/api/browser/ws"
    logger.info(f"Starting remote browser agent WebSocket client pointing to: {uri}")

    headers = {
        "User-Agent": "HS-Bot-Desktop/1.0",
        "Origin": "https://hs-chatbot-2.onrender.com"
    }
    backoff = 2
    while True:
        try:
            async with websockets.connect(
                uri,
                additional_headers=headers,
                ping_interval=20,   # WS-level ping every 20s to keep connection alive through Render's proxy
                ping_timeout=40,    # wait 40s for pong before declaring connection dead
                open_timeout=20,
            ) as websocket:
                backoff = 2  # Reset backoff on success
                logger.info(f"[WS Client] Connected to remote server at {uri}")

                # Task to send local state updates to the server periodically
                async def send_state_updates():
                    from app.services.browser.diagnostics import run_browser_diagnostics
                    while True:
                        try:
                            diag = run_browser_diagnostics()
                            current_state = browser_agent.state()
                            current_state["chrome"] = "READY" if diag["chrome"] == "FOUND" and diag["driver"] == "READY" else "NOT CONNECTED"
                            current_state["browser_agent"] = "READY" if diag["selenium"] == "READY" and diag["driver"] == "READY" else "FAILED"
                            # ALWAYS send — not just on change — to keep the Render proxy alive.
                            # Render's load balancer closes idle WebSocket connections after ~55s.
                            await websocket.send(json.dumps({
                                "type": "state_update",
                                "state": current_state
                            }))
                        except Exception as e:
                            logger.error(f"[WS Client] Error sending state update: {e}")
                        await asyncio.sleep(15)  # every 15s (well within Render's 55s idle timeout)

                state_task = asyncio.create_task(send_state_updates())

                try:
                    async for message_str in websocket:
                        try:
                            data = json.loads(message_str)
                            mtype = data.get("type")
                            
                            if mtype == "browser_action":
                                req_id = data.get("req_id")
                                action = data.get("action")
                                
                                if action == "run_plan":
                                    intent_dict = data.get("intent", {})
                                    # reconstruct BrowserIntent
                                    intent = BrowserIntent(
                                        intent=intent_dict.get("intent"),
                                        service=intent_dict.get("service"),
                                        query=intent_dict.get("query"),
                                        url=intent_dict.get("url"),
                                        target=intent_dict.get("target"),
                                        text=intent_dict.get("text"),
                                        direction=intent_dict.get("direction"),
                                        new_tab=intent_dict.get("new_tab", False),
                                        requires_confirmation=intent_dict.get("requires_confirmation", False),
                                    )
                                    
                                    logger.info(f"[WS Client] Executing local browser action plan for {intent.intent}")
                                    events = await browser_agent.run_plan(intent)
                                    
                                    # Send results back
                                    res_payload = {
                                        "type": "tool_result",
                                        "req_id": req_id,
                                        "success": True,
                                        "events": events
                                    }
                                    await websocket.send(json.dumps(res_payload))
                        except Exception as e:
                            logger.error(f"[WS Client] Error handling server message: {e}")
                finally:
                    state_task.cancel()
                    
        except Exception as e:
            logger.error(f"[WS Client] Connection lost or failed: {e}. Retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


def start_ws_client():
    global _client_task
    import sys
    import os

    # Auto-detect client mode:
    # 1. On Render cloud: RENDER or RENDER_SERVICE_ID env var is present → SERVER mode (accepts WS connections).
    # 2. On user's local machine: PyInstaller EXE (sys.frozen), local dev (app_env=="development"), or explicit BROWSER_AGENT_MODE=client → CLIENT mode (connects to Render WS).
    is_render = bool(os.environ.get("RENDER") or os.environ.get("RENDER_SERVICE_ID") or os.environ.get("RENDER_INSTANCE_ID"))
    is_client = (settings.browser_agent_mode == "client" or getattr(sys, "frozen", False) or settings.app_env == "development") and not is_render

    if is_client and settings.remote_backend_url:
        _client_task = asyncio.create_task(ws_client_loop())
        logger.info("WS Client (local agent) started, connecting to %s", settings.remote_backend_url)
    else:
        logger.info("WS Client disabled (is_render=%s, mode=%s). Running as server-side backend.", is_render, settings.browser_agent_mode)


def stop_ws_client():
    global _client_task
    if _client_task:
        _client_task.cancel()
        logger.info("WS Client background task stopped.")
