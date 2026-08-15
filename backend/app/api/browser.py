"""Browser Automation Agent REST surface.

GET /api/browser/state — global assistant/browser state snapshot used by
the desktop overlay to render tab status in real time (sections 11/13).
Commands themselves stay inside the chat streaming paths; this endpoint is
read-only polling (titles/urls of tabs the user's own agent opened).
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.browser.agent import browser_agent
from app.services.browser.ws_manager import ws_manager
import logging

logger = logging.getLogger("hsbot.api.browser")
router = APIRouter(prefix="/api/browser", tags=["browser"])


@router.get("/state")
async def browser_state() -> dict:
    if ws_manager.is_connected():
        return ws_manager.get_state()
    return browser_agent.state()


@router.websocket("/ws")
async def browser_ws(websocket: WebSocket):
    await websocket.accept()
    ws_manager.set_ws(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                import json
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue
            except Exception:
                pass
            ws_manager.handle_message(data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        ws_manager.clear_ws()


@router.get("/diagnostics")
async def get_browser_diagnostics() -> dict:
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


@router.post("/test_google")
async def post_test_google() -> dict:
    from app.services.browser.diagnostics import run_simple_google_test
    return await run_simple_google_test()
