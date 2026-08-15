import asyncio
import json
import logging
from typing import Optional
import websockets
from app.config import settings
from app.services.browser.agent import browser_agent, BrowserIntent

logger = logging.getLogger("hsbot.browser.ws_client")
_client_task: Optional[asyncio.Task] = None


def _ws_uri() -> str:
    base = settings.remote_backend_url.rstrip("/")
    return base.replace("https://", "wss://").replace("http://", "ws://") + "/api/browser/ws?token=" + settings.browser_ws_auth_token


async def ws_client_loop():
    if not settings.remote_backend_url:
        logger.info("[WS Client] No remote_backend_url configured. WebSocket client disabled.")
        return

    uri = _ws_uri()
    logger.info("[WS Client] Starting remote browser agent WebSocket client pointing to: %s", uri)

    headers = {
        "User-Agent": "HS-Bot-Desktop/1.0",
        "Origin": settings.remote_backend_url,
        "x-browser-token": settings.browser_ws_auth_token,
    }
    backoff = 1
    while True:
        try:
            async with websockets.connect(
                uri,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=40,
                open_timeout=20,
            ) as websocket:
                backoff = 1
                logger.info("[WS Client] Connected to remote server at %s", uri)

                async def send_state_updates():
                    from app.services.browser.diagnostics import run_browser_diagnostics
                    while True:
                        try:
                            diag = run_browser_diagnostics()
                            current_state = browser_agent.state()
                            current_state["chrome"] = "READY" if diag["chrome"] == "FOUND" and diag["driver"] == "READY" else "NOT CONNECTED"
                            current_state["browser_agent"] = "READY" if diag["selenium"] == "READY" and diag["driver"] == "READY" else "FAILED"
                            await websocket.send(json.dumps({"type": "state_update", "state": current_state}))
                        except Exception as e:
                            logger.error("[WS Client] Error sending state update: %s", e)
                        await asyncio.sleep(15)

                state_task = asyncio.create_task(send_state_updates())

                try:
                    async for message_str in websocket:
                        try:
                            data = json.loads(message_str)
                            mtype = data.get("type")
                            logger.info("[WS Client] Received message type=%s payload=%s", mtype, json.dumps(data)[:400])
                            if mtype == "browser_action":
                                req_id = data.get("request_id") or data.get("req_id")
                                action = data.get("action")
                                if action == "run_plan":
                                    intent_dict = data.get("intent", {})
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
                                    logger.info("[WS Client] Executing local browser action plan for %s request_id=%s", intent.intent, req_id)
                                    events = []
                                    async for ev in browser_agent.run_plan(intent):
                                        events.append(ev)
                                    res_payload = {
                                        "type": "browser.result",
                                        "request_id": req_id,
                                        "success": True,
                                        "data": {"events": events}
                                    }
                                    await websocket.send(json.dumps(res_payload))
                                    logger.info("[WS Client] Sent browser result for request_id=%s success=%s", req_id, True)
                        except Exception as e:
                            logger.error("[WS Client] Error handling server message: %s", e)
                finally:
                    state_task.cancel()
        except Exception as e:
            err_str = str(e)
            is_dns_error = "getaddrinfo" in err_str or "Name or service not known" in err_str
            wait = min(backoff, 30)
            if is_dns_error:
                wait = min(max(backoff, 1), 30)
            logger.error("[WS Client] Connection lost or failed: %s. Retrying in %ss...", e, wait)
            await asyncio.sleep(wait)
            backoff = min(max(backoff * 2, 1), 30)


def start_ws_client():
    global _client_task
    import sys
    import os

    is_render = bool(os.environ.get("RENDER") or os.environ.get("RENDER_SERVICE_ID") or os.environ.get("RENDER_INSTANCE_ID"))
    is_client = (settings.browser_agent_mode == "client" or getattr(sys, "frozen", False) or settings.app_env == "development") and not is_render

    if is_client and settings.remote_backend_url:
        _client_task = asyncio.create_task(ws_client_loop())
        logger.info("[WS Client] Local agent started, mode=client remote_backend_url=%s", settings.remote_backend_url)
    else:
        logger.info("[WS Client] disabled (is_render=%s, mode=%s). Running as server-side backend.", is_render, settings.browser_agent_mode)


def stop_ws_client():
    global _client_task
    if _client_task:
        _client_task.cancel()
        logger.info("WS Client background task stopped.")
