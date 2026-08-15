import time
import random
import threading
import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from app.config import settings


class ProviderHealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"


@dataclass
class RequestLog:
    request_id: str
    message_id: str
    model: str
    start_time: float
    end_time: Optional[float] = None
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None
    error_type: Optional[str] = None
    retry_count: int = 0
    fallback_used: bool = False
    provider: str = "nvidia"


@dataclass
class APIKey:
    key: str
    is_active: bool = True
    rate_limit_until: float = 0
    total_requests: int = 0
    total_tokens: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    last_used: float = 0
    errors: list[dict] = field(default_factory=list)
    health_state: ProviderHealthState = ProviderHealthState.HEALTHY
    last_health_check: float = 0

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
        self.consecutive_failures = 0
        self._update_health_state()

    def record_failure(self, error: str):
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.errors.append({"time": time.time(), "error": error})
        if len(self.errors) > 100:
            self.errors.pop(0)
        self._update_health_state()

    def _update_health_state(self):
        now = time.time()
        if self.consecutive_failures >= settings.nvidia_circuit_breaker_threshold:
            self.health_state = ProviderHealthState.UNAVAILABLE
        elif self.is_rate_limited:
            self.health_state = ProviderHealthState.RATE_LIMITED
        elif self.consecutive_failures > 0:
            self.health_state = ProviderHealthState.DEGRADED
        else:
            self.health_state = ProviderHealthState.HEALTHY
        self.last_health_check = now

    def apply_rate_limit(self, duration: Optional[float] = None):
        if duration is None:
            duration = settings.nvidia_rate_limit_cooldown
        self.rate_limit_until = time.time() + duration
        self.is_active = False
        self.health_state = ProviderHealthState.RATE_LIMITED

    def reset_circuit_breaker(self):
        self.consecutive_failures = 0
        self.is_active = True
        self.rate_limit_until = 0
        self._update_health_state()


class KeyManager:
    _instance = None
    _lock = threading.Lock()
    _request_logs: list[RequestLog] = []
    _max_logs = 1000

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
            healthy = [k for k in self.keys if k.is_active and not k.is_rate_limited and k.health_state != ProviderHealthState.UNAVAILABLE]
            if not healthy:
                self._reset_rate_limited_keys()
                healthy = [k for k in self.keys if not k.is_rate_limited and k.health_state != ProviderHealthState.UNAVAILABLE]

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
                k._update_health_state()

    def record_success(self, key: APIKey, tokens: int = 0):
        key.record_success(tokens)

    def record_failure(self, key: APIKey, error: str, status_code: Optional[int] = None):
        key.record_failure(error)
        error_lower = error.lower()

        if "429" in error or "rate_limit" in error_lower or "quota" in error_lower or (status_code == 429):
            key.apply_rate_limit(settings.nvidia_rate_limit_cooldown)
        elif "401" in error or "unauthorized" in error_lower or "invalid" in error_lower or (status_code == 401):
            key.is_active = False
            key.health_state = ProviderHealthState.UNAVAILABLE
        elif "529" in error or "503" in error or "server_busy" in error_lower or "server_error" in error_lower or (status_code in (503, 529)):
            key.apply_rate_limit(15.0)
        elif status_code and status_code >= 500:
            key.apply_rate_limit(10.0)

    def log_request(self, log: RequestLog):
        with self._lock:
            self._request_logs.append(log)
            if len(self._request_logs) > self._max_logs:
                self._request_logs.pop(0)

    def get_recent_logs(self, limit: int = 100) -> list[Dict[str, Any]]:
        with self._lock:
            return [self._log_to_dict(l) for l in self._request_logs[-limit:]]

    def _log_to_dict(self, log: RequestLog) -> Dict[str, Any]:
        return {
            "request_id": log.request_id,
            "message_id": log.message_id,
            "model": log.model,
            "start_time": log.start_time,
            "end_time": log.end_time,
            "latency_ms": log.latency_ms,
            "status_code": log.status_code,
            "error_type": log.error_type,
            "retry_count": log.retry_count,
            "fallback_used": log.fallback_used,
            "provider": log.provider,
        }

    def get_usage_stats(self) -> dict:
        return {
            "total_keys": len(self.keys),
            "active_keys": sum(1 for k in self.keys if k.is_active),
            "healthy_keys": sum(1 for k in self.keys if k.health_state == ProviderHealthState.HEALTHY),
            "degraded_keys": sum(1 for k in self.keys if k.health_state == ProviderHealthState.DEGRADED),
            "rate_limited_keys": sum(1 for k in self.keys if k.health_state == ProviderHealthState.RATE_LIMITED),
            "unavailable_keys": sum(1 for k in self.keys if k.health_state == ProviderHealthState.UNAVAILABLE),
            "total_requests": sum(k.total_requests for k in self.keys),
            "total_tokens": sum(k.total_tokens for k in self.keys),
            "total_failures": sum(k.failed_requests for k in self.keys),
            "keys": [
                {
                    "key_preview": k.key[:12] + "...",
                    "active": k.is_active,
                    "health_state": k.health_state.value,
                    "requests": k.total_requests,
                    "tokens": k.total_tokens,
                    "failures": k.failed_requests,
                    "consecutive_failures": k.consecutive_failures,
                    "health": round(k.health_score, 3),
                    "rate_limited": k.is_rate_limited,
                    "health_score": round(k.health_score, 3),
                }
                for k in self.keys
            ],
        }

    def get_health_status(self) -> dict:
        healthy = sum(1 for k in self.keys if k.health_state == ProviderHealthState.HEALTHY)
        total = len(self.keys)
        if total == 0:
            return {"status": "no_keys", "healthy": 0, "total": 0}
        if healthy == total:
            return {"status": "healthy", "healthy": healthy, "total": total}
        if healthy > 0:
            return {"status": "degraded", "healthy": healthy, "total": total}
        return {"status": "unavailable", "healthy": healthy, "total": total}


key_manager = KeyManager()