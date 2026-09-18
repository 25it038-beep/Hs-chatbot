import os
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api import auth, chats, models, files, nvidia_api, browser, documents, live, agent
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.tracing import RequestTracingMiddleware
from app.services.nvidia.warmup import start_warmup, stop_warmup


def _current_commit() -> str:
    for var in ("RENDER_GIT_COMMIT", "GIT_COMMIT"):
        value = os.environ.get(var)
        if value:
            return value[:12]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()[:12]
    except Exception:
        pass
    return "unknown"


_CURRENT_COMMIT = _current_commit()

os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs("./data", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await start_warmup()
    from app.services.browser.ws_client import start_ws_client, stop_ws_client
    start_ws_client()
    yield
    await stop_warmup()
    stop_ws_client()
    from app.services.retrieval.selenium_fetcher import shutdown as _selenium_shutdown
    from app.services.browser.agent import browser_agent as _browser_agent
    from app.live.riva_bridge import riva_bridge as _riva_bridge
    from app.live.llm import live_llm as _live_llm

    await _selenium_shutdown()
    await _browser_agent.shutdown()
    await _riva_bridge.shutdown()
    await _live_llm.close()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

import logging
_logger = logging.getLogger("hsbot.main")

class SafeCORSMiddleware(CORSMiddleware):
    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "websocket":
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)

# Always use wildcard CORS.
# Auth is JWT Bearer tokens (not cookies) so allow_credentials=False is correct
# and allow_origins=["*"] is safe. The previous branch logic caused Render to
# run with specific allowed origins that excluded the frontend URL.
app.add_middleware(
    SafeCORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestTracingMiddleware)

app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(models.router)
app.include_router(files.router)
app.include_router(nvidia_api.router)
app.include_router(browser.router)
app.include_router(documents.router)
app.include_router(live.router)
app.include_router(agent.router)


@app.get("/api/health")
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "env": settings.app_env,
        "commit": _CURRENT_COMMIT,
    }


@app.get("/api/health/full")
async def health_full():
    """Detailed health check: provider config status and browser WS status. Never exposes keys."""
    from app.services.browser.ws_manager import ws_manager

    def _provider_status(name: str, key_attr: str) -> dict:
        configured = bool(getattr(settings, key_attr, None))
        return {"configured": configured}

    return {
        "status": "ok",
        "version": settings.app_version,
        "env": settings.app_env,
        "commit": _CURRENT_COMMIT,
        "providers": {
            "nvidia": {"configured": bool(settings.nvidia_api_keys)},
            "sambanova": _provider_status("sambanova", "sambanova_api_key"),
            "openai": _provider_status("openai", "openai_api_key"),
            "anthropic": _provider_status("anthropic", "anthropic_api_key"),
            "gemini": _provider_status("gemini", "google_api_key"),
            "groq": _provider_status("groq", "groq_api_key"),
            "openrouter": _provider_status("openrouter", "openrouter_api_key"),
        },
        "browser": {
            "websocket_connected": ws_manager.is_connected(),
            "agent_mode": settings.browser_agent_mode,
        },
    }


@app.get("/")
async def root():
    return {"name": settings.app_name, "version": settings.app_version, "docs": "/docs"}


@app.get("/api/download/windows")
@app.get("/api/download/hsbot-setup.exe")
@app.get("/api/download/desktop")
async def download_windows_setup():
    """Download the HSBot Windows Desktop setup installer."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "desktop", "src-tauri", "target", "release", "bundle", "nsis", "HSBot_1.0.0_x64-setup.exe"),
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", "downloads", "HSBot_1.0.0_x64-setup.exe"),
    ]
    for p in candidates:
        abs_p = os.path.abspath(p)
        if os.path.exists(abs_p):
            return FileResponse(
                path=abs_p,
                filename="HSBot_1.0.0_x64-setup.exe",
                media_type="application/vnd.microsoft.portable-executable",
            )
    raise HTTPException(status_code=404, detail="Desktop setup executable not found")


