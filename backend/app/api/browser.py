"""Browser Automation Agent REST surface.

GET /api/browser/state — global assistant/browser state snapshot used by
the desktop overlay to render tab status in real time (sections 11/13).
Commands themselves stay inside the chat streaming paths; this endpoint is
read-only polling (titles/urls of tabs the user's own agent opened).
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.config import settings
from app.services.browser.agent import browser_agent
from app.services.browser.ws_manager import ws_manager

logger = logging.getLogger("hsbot.api.browser")
router = APIRouter(prefix="/api/browser", tags=["browser"])


def _browser_ws_auth_error() -> dict[str, Any]:
    return {"type": "browser.result", "success": False, "error": "Unauthorized browser client."}


@router.get("/state")
async def browser_state() -> dict:
    """Return browser agent state. Always returns a valid response even if browser is not running."""
    try:
        if ws_manager.is_connected():
            return ws_manager.get_state()
        return browser_agent.state()
    except Exception as e:
        logger.error(f"Error getting browser state: {e}")
        # Return a valid default state instead of failing
        return {
            "browser_open": False,
            "current_url": None,
            "current_title": None,
            "active_service": None,
            "persistent_session": False,
            "active_tab": None,
            "tabs": [],
            "current_action": None,
            "queued_actions": [],
            "error": str(e)
        }


@router.websocket("/ws")
async def browser_ws(websocket: WebSocket):
    token = websocket.query_params.get("token") or websocket.headers.get("x-browser-token") or websocket.headers.get("authorization", "").replace("Bearer ", "", 1)
    expected = settings.browser_ws_auth_token
    if not expected:
        logger.warning("[WS AUTH] No browser token configured; rejecting browser client.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if token != expected:
        logger.warning("[WS AUTH] Browser WS rejected: invalid token.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    logger.info("[WS AUTH] Browser WS authenticated; accepting connection.")
    await websocket.accept()
    ws_manager.set_ws(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    logger.info("[WS HEARTBEAT] pong sent for browser client.")
                    continue
                if msg.get("type") == "browser.result":
                    logger.info("[WS RESULT] Received browser result request_id=%s success=%s", msg.get("request_id"), msg.get("success"))
                    continue
            except Exception:
                pass
            logger.info("[WS MESSAGE] Browser client sent message: %s", data[:256])
            ws_manager.handle_message(data)
    except WebSocketDisconnect:
        logger.info("[WS DISCONNECT] Browser WS disconnected normally.")
    except Exception as e:
        logger.error(f"[WS ERROR] WebSocket connection error: {e}")
    finally:
        ws_manager.clear_ws()


@router.get("/diagnostics")
async def get_browser_diagnostics() -> dict:
    """Return diagnostic information. Always returns valid JSON, never 400."""
    try:
        from app.services.browser.ws_manager import ws_manager
        ws_connected = ws_manager.is_connected()
        
        if ws_connected:
            state = ws_manager.get_state()
            browser_agent_status = state.get("browser_agent", "FAILED")
            chrome_status = state.get("chrome", "NOT CONNECTED")
        else:
            from app.services.browser.diagnostics import run_browser_diagnostics
            diag = run_browser_diagnostics()
            browser_agent_status = "READY" if diag["selenium"] == "READY" and diag["driver"] == "READY" else "FAILED"
            chrome_status = "READY" if diag["chrome"] == "FOUND" and diag["driver"] == "READY" else "NOT CONNECTED"

        return {
            "Backend": "CONNECTED",
            "WebSocket": "CONNECTED" if ws_connected else "NOT CONNECTED",
            "Browser Agent": browser_agent_status,
            "Chrome": chrome_status
        }
    except Exception as e:
        logger.error(f"Error getting browser diagnostics: {e}")
        return {
            "Backend": "CONNECTED",
            "WebSocket": "ERROR",
            "Browser Agent": "FAILED",
            "Chrome": "ERROR",
            "error": str(e)
        }


@router.post("/test_google")
async def post_test_google() -> dict:
    from app.services.browser.diagnostics import run_simple_google_test
    return await run_simple_google_test()
