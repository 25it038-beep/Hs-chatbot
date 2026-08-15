"""
Test executing a real browser action (open YouTube) via Render WebSocket!
"""
import asyncio
import json
import time

async def run_action_test():
    from app.config import settings
    settings.browser_agent_mode = "client"
    settings.remote_backend_url = "https://hs-chatbot-2.onrender.com"

    from app.services.browser.ws_client import ws_client_loop
    from app.services.browser.agent import BrowserIntent

    print("[1] Starting local agent connected to Render...")
    client_task = asyncio.create_task(ws_client_loop())
    await asyncio.sleep(2)

    intent = BrowserIntent(intent="OPEN_WEBSITE", service="youtube", url="https://www.youtube.com")
    print(f"[2] Testing action execution for intent: {intent.intent} ({intent.url})...")

    from app.services.browser.agent import browser_agent
    events = await browser_agent.run_plan(intent)
    
    print("[3] Action execution finished! Events received:")
    for ev in events:
        print("   -", json.dumps(ev, ensure_ascii=True))

    client_task.cancel()

if __name__ == "__main__":
    asyncio.run(run_action_test())
