"""Per-stage latency monitoring (section 15)."""

import time
from dataclasses import dataclass, field


@dataclass
class StageTimer:
    _start: dict[str, float] = field(default_factory=dict)
    elapsed: dict[str, float] = field(default_factory=dict)

    def start(self, stage: str) -> None:
        self._start[stage] = time.perf_counter()

    def stop(self, stage: str) -> float:
        s = self._start.pop(stage, None)
        if s is None:
            return 0.0
        ms = round((time.perf_counter() - s) * 1000, 1)
        self.elapsed[stage] = ms
        return ms

    def measure(self, stage: str, fn):
        self.start(stage)
        try:
            return fn()
        finally:
            self.stop(stage)

    async def ameasure(self, stage: str, fn):
        self.start(stage)
        try:
            return await fn()
        finally:
            self.stop(stage)

    def to_dict(self) -> dict:
        return dict(self.elapsed)

    def total_ms(self) -> float:
        return round(sum(self.elapsed.values()), 1)


def build_perf(timer: StageTimer, llm_ms: float = 0.0, extra: dict | None = None) -> dict:
    perf = {
        "routing_ms": timer.elapsed.get("routing", 0.0),
        "querygen_ms": timer.elapsed.get("querygen", 0.0),
        "search_ms": timer.elapsed.get("search", 0.0),
        "ranking_ms": timer.elapsed.get("ranking", 0.0),
        "fetch_ms": timer.elapsed.get("fetch", 0.0),
        "extraction_ms": timer.elapsed.get("extraction", 0.0),
        "reranking_ms": timer.elapsed.get("reranking", 0.0),
        "llm_ms": round(llm_ms, 1),
        "total_ms": round(timer.total_ms() + llm_ms, 1),
    }
    if extra:
        perf.update(extra)
    return perf
