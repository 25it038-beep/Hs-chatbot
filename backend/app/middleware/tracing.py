"""
Request tracing middleware.
Adds a unique request_id to every HTTP request and logs structured
request metadata (method, path, status, latency). Never logs secrets.
"""
import time
import uuid
import logging
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("hsbot.request")


class RequestTracingMiddleware:
    """Pure ASGI middleware: assign request_id, log timing + status."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())[:8]
        method = scope.get("method", "?")
        path = scope.get("path", "?")
        start = time.perf_counter()

        # Inject request_id into scope so downstream handlers can read it
        scope["request_id"] = request_id

        status_code = 0

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "[REQUEST] id=%s method=%s path=%s status=%d latency=%.1fms",
                request_id,
                method,
                path,
                status_code,
                latency_ms,
            )
