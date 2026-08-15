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
        logger.info("Local browser agent WebSocket client connected.")

    def clear_ws(self) -> None:
        self.active_ws = None
        self._state = {
            "browser_open": False,
            "active_tab": None,
            "tabs": [],
            "current_action": None,
            "queued_actions": []
        }
        logger.info("Local browser agent WebSocket client disconnected.")

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
            
            if mtype == "state_update":
                self.update_state(data.get("state", {}))
                
            elif mtype == "tool_result":
                req_id = data.get("req_id")
                if req_id in self._pending_responses:
                    future = self._pending_responses.pop(req_id)
                    if not future.done():
                        future.set_result(data)
                        
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    async def execute_action(self, action: str, **kwargs) -> dict:
        """Send a browser command to the local EXE client and await result."""
        if not self.is_connected():
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
            "req_id": req_id,
            "action": action,
            **kwargs
        }

        try:
            # send to websocket client
            await self.active_ws.send_text(json.dumps(payload))
            # wait with timeout (e.g. 45 seconds)
            result = await asyncio.wait_for(future, timeout=45.0)
            return result
        except asyncio.TimeoutError:
            self._pending_responses.pop(req_id, None)
            return {
                "success": False,
                "error": "Request to local browser timed out."
            }
        except Exception as e:
            self._pending_responses.pop(req_id, None)
            return {
                "success": False,
                "error": f"Failed to execute local action: {e}"
            }


ws_manager = BrowserWSManager()
