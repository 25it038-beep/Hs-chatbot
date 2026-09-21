"""Scope-aware caching for web search and research results."""

import hashlib
import time
from typing import Any, Dict, Optional


class SearchCache:
    def __init__(self, default_ttl_s: int = 1800):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl_s

    def _key(self, query: str, mode: str, region: Optional[str] = None) -> str:
        raw = f"{query.strip().lower()}:{mode}:{region or 'all'}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, query: str, mode: str, region: Optional[str] = None) -> Optional[Any]:
        k = self._key(query, mode, region)
        item = self._store.get(k)
        if not item:
            return None
        if time.time() > item["expires"]:
            del self._store[k]
            return None
        return item["val"]

    def set(self, query: str, mode: str, val: Any, ttl_s: Optional[int] = None, region: Optional[str] = None) -> None:
        k = self._key(query, mode, region)
        ttl = ttl_s or self._default_ttl
        self._store[k] = {
            "val": val,
            "expires": time.time() + ttl,
            "created": time.time(),
        }

    def clear(self) -> None:
        self._store.clear()


search_cache = SearchCache()
