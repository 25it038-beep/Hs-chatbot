"""OS-Level Automation Engine for HS Bot

Provides deterministic, safe OS automation with intent detection,
command routing, and safety confirmation gates.
"""

from .engine import automation_engine

__all__ = ["automation_engine"]
