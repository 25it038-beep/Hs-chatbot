import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("hsbot.chat_context.watchdog")


class StreamWatchdog:
    """
    Streaming inactivity and watchdog monitor.
    Protects against hanging connections, silent stalls, and tracks streaming progress.
    """

    def __init__(
        self,
        request_id: str,
        ttft_timeout_s: float = 60.0,
        inactivity_timeout_s: float = 25.0
    ):
        self.request_id = request_id
        self.ttft_timeout_s = ttft_timeout_s
        self.inactivity_timeout_s = inactivity_timeout_s
        self.started_at = time.time()
        self.first_token_at: Optional[float] = None
        self.last_chunk_at: float = self.started_at
        self.partial_chunks: list[str] = []
        self.total_chars = 0
        self.is_completed = False
        self.error: Optional[str] = None

    def record_chunk(self, chunk: str) -> None:
        now = time.time()
        if self.first_token_at is None:
            self.first_token_at = now
        self.last_chunk_at = now
        self.partial_chunks.append(chunk)
        self.total_chars += len(chunk)

    def check_stall(self) -> Optional[str]:
        """
        Returns an error message if the stream is stalled, else None.
        """
        now = time.time()
        # 1. Check TTFT stall before first token arrives
        if self.first_token_at is None:
            if now - self.started_at > self.ttft_timeout_s:
                return f"Model initial response timed out after {self.ttft_timeout_s:.1f}s (TTFT timeout)."
        else:
            # 2. Check inactivity stall between subsequent tokens
            if not self.is_completed and (now - self.last_chunk_at > self.inactivity_timeout_s):
                return f"Model stream stalled: no tokens received for {self.inactivity_timeout_s:.1f}s."
        return None

    def get_partial_content(self) -> str:
        return "".join(self.partial_chunks)

    def complete(self) -> None:
        self.is_completed = True

    def get_metrics(self) -> Dict[str, Any]:
        now = time.time()
        ttft = (self.first_token_at - self.started_at) if self.first_token_at else None
        duration = now - self.started_at
        return {
            "request_id": self.request_id,
            "duration_s": round(duration, 2),
            "ttft_s": round(ttft, 2) if ttft is not None else None,
            "total_chars": self.total_chars,
            "chunks_received": len(self.partial_chunks),
            "completed": self.is_completed
        }
