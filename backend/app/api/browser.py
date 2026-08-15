"""Browser Automation Agent REST surface.

GET /api/browser/state — global assistant/browser state snapshot used by
the desktop overlay to render tab status in real time (sections 11/13).
Commands themselves stay inside the chat streaming paths; this endpoint is
read-only polling (titles/urls of tabs the user's own agent opened).
"""

from fastapi import APIRouter

from app.services.browser.agent import browser_agent

router = APIRouter(prefix="/api/browser", tags=["browser"])


@router.get("/state")
async def browser_state() -> dict:
    return browser_agent.state()
