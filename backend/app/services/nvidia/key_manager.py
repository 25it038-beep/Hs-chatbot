import time
import random
import threading
from typing import Optional
from dataclasses import dataclass, field
from app.config import settings


@dataclass
class APIKey:
    key: str
    is_active: bool = True
    rate_limit_until: float = 0
    total_requests: int = 0
    total_tokens: int = 0
    failed_requests: int = 0
    last_used: float = 0
    errors: list[dict] = field(default_factory=list)

    @property
    def is_rate_limited(self) -> bool:
        return time.time() < self.rate_limit_until

    @property
    def health_score(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return 1.0 - (self.failed_requests / max(self.total_requests, 1))

    def record_success(self, tokens: int = 0):
        self.total_requests += 1
        self.total_tokens += tokens
        self.last_used = time.time()

    def record_failure(self, error: str):
        self.failed_requests += 1
        self.errors.append({"time": time.time(), "error": error})
        if len(self.errors) > 100:
            self.errors.pop(0)

    def apply_rate_limit(self, duration: float = 60.0):
        self.rate_limit_until = time.time() + duration
        self.is_active = False


class KeyManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.keys: list[APIKey] = []
        self._init_keys()
        self._current_index = 0

    def _init_keys(self):
        from app.config import settings
        raw_keys = getattr(settings, 'nvidia_api_keys', "") or ""
        for k in raw_keys.split(","):
            k = k.strip()
            if k:
                self.keys.append(APIKey(key=k))

    def get_key(self) -> Optional[APIKey]:
        if not self.keys:
            return None

        with self._lock:
            healthy = [k for k in self.keys if k.is_active and not k.is_rate_limited]
            if not healthy:
                self._reset_rate_limited_keys()
                healthy = [k for k in self.keys if not k.is_rate_limited]

            if not healthy:
                return None

            healthy.sort(key=lambda k: (k.health_score, -k.last_used), reverse=True)
            chosen = healthy[0]
            self._current_index = (self._current_index + 1) % len(self.keys)
            return chosen

    def _reset_rate_limited_keys(self):
        now = time.time()
        for k in self.keys:
            if k.is_rate_limited and now >= k.rate_limit_until:
                k.is_active = True

    def record_success(self, key: APIKey, tokens: int = 0):
        key.record_success(tokens)

    def record_failure(self, key: APIKey, error: str):
        key.record_failure(error)
        if "429" in error or "rate_limit" in error.lower() or "quota" in error.lower():
            key.apply_rate_limit(30.0)
        elif "401" in error or "unauthorized" in error.lower() or "invalid" in error.lower():
            key.is_active = False
        elif "529" in error or "503" in error or "server_busy" in error.lower() or "server_error" in error.lower():
            key.apply_rate_limit(15.0)

    def get_usage_stats(self) -> dict:
        return {
            "total_keys": len(self.keys),
            "active_keys": sum(1 for k in self.keys if k.is_active),
            "total_requests": sum(k.total_requests for k in self.keys),
            "total_tokens": sum(k.total_tokens for k in self.keys),
            "total_failures": sum(k.failed_requests for k in self.keys),
            "keys": [
                {
                    "key_preview": k.key[:12] + "...",
                    "active": k.is_active,
                    "requests": k.total_requests,
                    "tokens": k.total_tokens,
                    "failures": k.failed_requests,
                    "health": round(k.health_score, 3),
                    "rate_limited": k.is_rate_limited,
                }
                for k in self.keys
            ],
        }


key_manager = KeyManager()
