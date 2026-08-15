"""BrowserService — chat-facing facade for the Browser Automation Agent.

Routing rules (sections 5/16/17/21):
- SEARCH_WEB → fast retrieval pipeline (delegated back to the chat flow, no
  Selenium) — marker event `{"type": "delegate_web_search"}`.
- Consequential intents (buy/checkout/delete/send/pay...) are queued and
  require an explicit user confirmation in chat; only then do they execute.
- Everything else streams browser_status/content/image/done events.

One pending action per user; a "yes/confirm" message executes it, any other
browser intent replaces it.
"""

from typing import AsyncIterator, Optional

from . import intent as bi
from .agent import AuthRequired, browser_agent
from .config import browser_config as cfg


class BrowserService:
    def __init__(self) -> None:
        self._pending: dict[str, dict] = {}

    # ── detection ──

    def detect(self, message: str) -> Optional[bi.BrowserIntent]:
        """Returns a BrowserIntent if the message is a browser action (or
        a confirmation of a pending one), else None (normal chat)."""
        if not cfg.BROWSER_ENABLED:
            return None
        return bi.classify_browser_intent(message, current_service=browser_agent.active_service)

    def has_pending(self, user_id: str) -> bool:
        return user_id in self._pending

    def pending_description(self, user_id: str) -> Optional[str]:
        p = self._pending.get(user_id)
        if not p:
            return None
        intent: bi.BrowserIntent = p["intent"]
        return f"{intent.intent} on {intent.service or 'the browser'}" + (f' for "{intent.query}"' if intent.query else "")

    # ── main entry ──

    async def stream_for_message(self, message: str, user_id: str = "default") -> AsyncIterator[dict]:
        intent = self.detect(message)
        if intent is None:
            return

        # Fast web search → the retrieval pipeline owns it (section 17).
        if intent.intent == bi.SEARCH_WEB:
            yield {"type": "browser_status", "content": "🔎 Using the fast web search for this one."}
            yield {"type": "delegate_web_search", "content": ""}
            return

        # User confirmed a queued consequential action → execute it now.
        if intent.intent == bi.CONFIRM_ACTION:
            pending = self._pending.pop(user_id, None)
            if pending is None:
                yield {"type": "browser_status", "content": "I don't have a pending action to confirm."}
                yield {"type": "content", "content": "Tell me what you'd like me to do and I'll take care of it."}
                yield {"type": "done", "success": False}
                return
            yield {"type": "browser_status", "content": "✅ Confirmed — executing."}
            async for ev in self._run_plan(pending["intent"]):
                yield ev
            return

        # Consequential action → queue for explicit confirmation (section 16).
        if intent.requires_confirmation and not cfg.BROWSER_AUTO_CONFIRM:
            self._pending[user_id] = {"intent": intent}
            desc = f"{intent.intent.lower().replace('_', ' ')}" + (
                f" on {intent.service}" if intent.service else ""
            )
            yield {
                "type": "browser_status",
                "content": f"⚠️ That would {desc} in the browser — it can't be undone easily.",
            }
            yield {
                "type": "content",
                "content": f"**Confirm?** This action has consequences. Reply *yes* to proceed, or anything else to cancel.",
            }
            yield {"type": "done", "success": False, "awaiting_confirmation": True}
            return

        # Ordinary browser action → execute immediately.
        async for ev in self._run_plan(intent):
            yield ev

    async def _run_plan(self, intent: bi.BrowserIntent) -> AsyncIterator[dict]:
        from .ws_manager import ws_manager
        if ws_manager.is_connected():
            res = await ws_manager.execute_action("run_plan", intent=intent.to_dict())
            if res.get("success"):
                for ev in res.get("events", []):
                    yield ev
            else:
                yield {
                    "type": "browser_status",
                    "content": f"❌ Action failed: {res.get('error', 'unknown error')}"
                }
                yield {
                    "type": "content",
                    "content": f"I couldn't complete the request: {res.get('error', 'unknown error')}"
                }
                yield {"type": "done", "success": False}
        else:
            async for ev in browser_agent.run_plan(intent):
                yield ev

    def clear_pending(self, user_id: str) -> None:
        self._pending.pop(user_id, None)


browser_service = BrowserService()
