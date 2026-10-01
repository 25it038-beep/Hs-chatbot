import time
from collections import defaultdict

class RateLimitMiddleware:
    def __init__(self, app, calls: int = 1200, period: int = 60):
        self.app = app
        self.calls = calls
        self.period = period
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.exempt_prefixes = (
            "/health",
            "/api/health",
            "/api/browser/state",
            "/api/browser/status",
            "/docs",
            "/openapi.json",
        )

    async def __call__(self, scope, receive, send):
        # Skip rate limiting for WebSocket connections
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip rate limiting for CORS preflight requests
        method = scope.get("method", "").upper()
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if any(path.startswith(prefix) for prefix in self.exempt_prefixes):
            await self.app(scope, receive, send)
            return

        # Extract real client IP from X-Forwarded-For or X-Real-IP when behind reverse proxy
        client_ip = None
        for name, value in scope.get("headers", []):
            lower_name = name.lower()
            if lower_name == b"x-forwarded-for":
                raw = value.decode("utf-8", errors="ignore")
                client_ip = raw.split(",")[0].strip()
                break
            elif lower_name == b"x-real-ip":
                client_ip = value.decode("utf-8", errors="ignore").strip()
                break

        if not client_ip:
            client = scope.get("client")
            client_ip = client[0] if client else "unknown"

        now = time.time()
        window = self.requests[client_ip]
        window[:] = [t for t in window if t > now - self.period]
        if len(window) >= self.calls:
            response_msg = b'{"detail": "Rate limit exceeded. Please wait a moment."}'
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(response_msg)).encode()),
                    (b"access-control-allow-origin", b"*"),
                    (b"access-control-allow-methods", b"*"),
                    (b"access-control-allow-headers", b"*"),
                ]
            })
            await send({
                "type": "http.response.body",
                "body": response_msg,
                "more_body": False
            })
            return

        window.append(now)
        await self.app(scope, receive, send)
