"""
Deterministic Turn Manager for Backend Live Voice Session
"""

import logging
from typing import Optional

logger = logging.getLogger("hsbot.live.turn_manager")

VALID_STATES = {"IDLE", "CONNECTING", "LISTENING", "PROCESSING", "SPEAKING", "INTERRUPTED", "ERROR"}


class LiveTurnManager:
    def __init__(self):
        self.state = "IDLE"
        self.error_count = 0
        self.max_errors = 3

    def get_state(self) -> str:
        return self.state

    def transition_to(self, new_state: str, reason: str = "") -> bool:
        if new_state not in VALID_STATES:
            logger.warning(f"Invalid state: {new_state}")
            return False

        if self.state == new_state:
            return True

        logger.info(f"Session state transition: {self.state} -> {new_state} ({reason})")
        self.state = new_state

        if new_state != "ERROR":
            self.error_count = 0

        return True

    def handle_barge_in(self) -> bool:
        if self.state in ("SPEAKING", "PROCESSING"):
            logger.info("Server detected barge-in interruption")
            self.transition_to("INTERRUPTED", "Barge-in")
            return True
        return False

    def handle_error(self, err: str) -> str:
        self.error_count += 1
        logger.error(f"Live error recorded ({self.error_count}/{self.max_errors}): {err}")
        if self.error_count >= self.max_errors:
            self.transition_to("ERROR", f"Trip circuit breaker: {err}")
            return "ERROR"
        else:
            self.transition_to("LISTENING", "Recover from transient error")
            return "LISTENING"

    def reset(self):
        self.state = "IDLE"
        self.error_count = 0
