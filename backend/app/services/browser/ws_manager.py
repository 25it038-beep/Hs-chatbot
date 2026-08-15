import asyncio
import json
import logging
from typing import Optional, Any

logger = logging.getLogger("hsbot.browser.ws")

class BrowserWSManager:
    def __init__(self) -> None:
        self.active_ws: Optional[Any] = None
        self._state: dict = {
            "browser_open": False,
            "active_tab": None,
            "tabs": [],
            "current_action": None,
            "queued_actions": []
        }
        self._pending_responses: dict[str, asyncio.Future] = {}
        self._request_counter = 0

    def set_ws(self, ws: Any) -> None:
        self.active_ws = ws
        logger.info("[WS SERVER] Local browser agent WebSocket client connected.")

    def clear_ws(self) -> None:
        self.active_ws = None
        self._state = {
            "browser_open": False,
            "active_tab": None,
            "tabs": [],
            "current_action": None,
            "queued_actions": []
        }
        logger.info("[WS SERVER] Local browser agent WebSocket client disconnected.")

    def is_connected(self) -> bool:
        return self.active_ws is not None

    def update_state(self, state: dict) -> None:
        if isinstance(state, dict):
            self._state = state

    def get_state(self) -> dict:
        return self._state

    def handle_message(self, message_str: str) -> None:
        """Process messages received on the WebSocket server."""
        try:
            data = json.loads(message_str)
            mtype = data.get("type")
            logger.info("[WS SERVER] Received message type=%s payload=%s", mtype, json.dumps(data)[:400])
            if mtype == "state_update":
                self.update_state(data.get("state", {}))
            elif mtype == "tool_result":
                req_id = data.get("req_id")
                if req_id in self._pending_responses:
                    future = self._pending_responses.pop(req_id)
                    if not future.done():
                        future.set_result(data)
                    logger.info("[WS SERVER] Completed browser command request_id=%s success=%s", req_id, data.get("success"))
        except Exception as e:
            logger.error(f"[WS SERVER] Error handling WebSocket message: {e}")

    async def execute_action(self, action: str, **kwargs) -> dict:
        """Send a browser command to the local EXE client and await result."""
        if not self.is_connected():
            logger.warning("[WS CLIENT SEND] Local browser automation service is not connected; action=%s", action)
            return {
                "success": False,
                "error": "Local browser automation service is not connected."
            }

        self._request_counter += 1
        req_id = f"req_{self._request_counter}"
        future = asyncio.get_running_loop().create_future()
        self._pending_responses[req_id] = future

        payload = {
            "type": "browser_action",
            "request_id": req_id,
            "req_id": req_id,
            "action": action,
            **kwargs
        }

        try:
            logger.info("[WS CLIENT SEND] sending browser command action=%s request_id=%s payload=%s", action, req_id, json.dumps(payload)[:400])
            await self.active_ws.send_text(json.dumps(payload))
            result = await asyncio.wait_for(future, timeout=45.0)
            logger.info("[WS CLIENT SEND] browser command completed request_id=%s result=%s", req_id, json.dumps(result)[:400])
            return result
        except asyncio.TimeoutError:
            self._pending_responses.pop(req_id, None)
            logger.error("[WS CLIENT SEND] request timed out for request_id=%s action=%s", req_id, action)
            return {
                "success": False,
                "error": "Request to local browser timed out."
            }
        except Exception as e:
            self._pending_responses.pop(req_id, None)
            logger.error("[WS CLIENT SEND] local action failed request_id=%s action=%s error=%s", req_id, action, e)
            return {
                "success": False,
                "error": f"Failed to execute local action: {e}"
            }


ws_manager = BrowserWSManager()
