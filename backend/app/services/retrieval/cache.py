"""Cache layer (section 7): Redis when available, in-memory fallback otherwise.

TTL tiers:
- news / current  -> short
- general web     -> medium
- docs            -> long
Explicit latest/current queries bypass stale reads but still write short-TTL entries.
"""

import asyncio
import json
import time
from typing import Any, Optional

from loguru import logger

from .config import retrieval_config as cfg

_TTL_BY_SCOPE = {
    "news": cfg.TTL_NEWS_S,
    "current": cfg.TTL_CURRENT_S,
    "general": cfg.TTL_GENERAL_S,
    "docs": cfg.TTL_DOCS_S,
}


class _MemoryStore:
    """Thread-safe in-process store with expiry (fallback when Redis is down)."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires, value = item
            if time.monotonic() > expires:
                self._data.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        async with self._lock:
            self._data[key] = (time.monotonic() + ttl, value)


class RetrievalCache:
    def __init__(self) -> None:
        self._memory = _MemoryStore()
        self._redis = None
        self._redis_state: str = "untested"  # untested | ok | down

    async def _ensure_redis(self):
        if self._redis_state != "untested":
            return self._redis
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(
                cfg.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=1.0, decode_responses=True
            )
            await asyncio.wait_for(client.ping(), timeout=1.0)
            self._redis = client
            self._redis_state = "ok"
            logger.info("Retrieval cache: Redis connected ({})", cfg.REDIS_URL)
        except Exception as e:
            self._redis_state = "down"
            logger.warning("Retrieval cache: Redis unavailable ({}), using in-memory fallback", e)
        return self._redis

    def _key(self, scope: str, normalized: str) -> str:
        return f"hsretr:{scope}:{normalized}"

    def ttl_for(self, scope: str) -> int:
        return _TTL_BY_SCOPE.get(scope, cfg.TTL_GENERAL_S)

    async def get(self, normalized: str, scope: str) -> Optional[Any]:
        if not cfg.CACHE_ENABLED:
            return None
        key = self._key(scope, normalized)
        redis = await self._ensure_redis()
        if redis is not None:
            try:
                raw = await redis.get(key)
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
            return None
        return await self._memory.get(key)

    async def set(self, normalized: str, scope: str, value: Any) -> None:
        if not cfg.CACHE_ENABLED:
            return
        ttl = self.ttl_for(scope)
        key = self._key(scope, normalized)
        redis = await self._ensure_redis()
        if redis is not None:
            try:
                await redis.set(key, json.dumps(value, default=str), ex=ttl)
                return
            except Exception:
                pass
        await self._memory.set(key, value, ttl)


retrieval_cache = RetrievalCache()
