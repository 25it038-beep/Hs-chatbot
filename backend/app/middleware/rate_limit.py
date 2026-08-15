import time
from collections import defaultdict

class RateLimitMiddleware:
    def __init__(self, app, calls: int = 300, period: int = 60):
        self.app = app
        self.calls = calls
        self.period = period
        self.requests: dict[str, list[float]] = defaultdict(list)

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

        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        now = time.time()
        window = self.requests[client_ip]
        window[:] = [t for t in window if t > now - self.period]
        if len(window) >= self.calls:
            response_msg = b'{"detail": "Rate limit exceeded"}'
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(response_msg)).encode()),
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
