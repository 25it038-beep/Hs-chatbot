"""Real-time voice conversation session manager.

Tracks live session state, user context (language, timezone, location),
conversation turns, active worker tasks (cancellable on interrupt),
and WebSocket connection references.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional
from loguru import logger

SessionStatus = Literal[
    "idle",
    "listening",
    "processing",
    "speaking",
    "interrupted",
    "error",
    "stopped",
]


@dataclass
class LiveMessageTurn:
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: float = field(default_factory=time.time)
    interrupted: bool = False
    tool_used: Optional[str] = None


@dataclass
class LiveSession:
    session_id: str
    conversation_id: str
    user_id: Optional[str] = None
    status: SessionStatus = "idle"
    language: str = "en"  # "en", "ta", "hi"
    timezone: str = "UTC"
    location: Optional[str] = None
    history: List[LiveMessageTurn] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    
    # Background generation/synthesis task that can be cancelled immediately on barge-in
    current_task: Optional[asyncio.Task] = None
    # Current active utterance accumulated so far
    current_assistant_text: str = ""
    # Flag to signal generation loop to abort
    abort_requested: bool = False

    def touch(self) -> None:
        self.last_activity = time.time()

    def set_status(self, new_status: SessionStatus) -> None:
        self.status = new_status
        self.touch()

    def add_user_message(self, text: str) -> None:
        if text.strip():
            self.history.append(LiveMessageTurn(role="user", content=text.strip()))
            self.touch()

    def add_assistant_message(self, text: str, interrupted: bool = False, tool_used: Optional[str] = None) -> None:
        if text.strip():
            self.history.append(
                LiveMessageTurn(
                    role="assistant",
                    content=text.strip(),
                    interrupted=interrupted,
                    tool_used=tool_used,
                )
            )
            self.touch()

    def interrupt(self) -> str:
        """Cancel current worker task immediately and mark status as interrupted."""
        self.abort_requested = True
        interrupted_text = self.current_assistant_text
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            logger.info("Cancelled ongoing generation task for session {}", self.session_id)
        
        if interrupted_text:
            self.add_assistant_message(interrupted_text, interrupted=True)
            self.current_assistant_text = ""
        
        self.set_status("interrupted")
        return interrupted_text

    def get_recent_history_prompt(self, max_turns: int = 6) -> List[Dict[str, str]]:
        """Return the last N message turns formatted for LLM completion context."""
        recent = self.history[-max_turns:]
        return [{"role": t.role, "content": t.content} for t in recent]


class LiveSessionManager:
    """Singleton session registry managing active live conversation sessions."""

    def __init__(self):
        self._sessions: Dict[str, LiveSession] = {}
        self._conv_to_session: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        conversation_id: str,
        user_id: Optional[str] = None,
        language: str = "en",
        timezone: str = "UTC",
        location: Optional[str] = None,
    ) -> LiveSession:
        async with self._lock:
            existing_session_id = self._conv_to_session.get(conversation_id)
            if existing_session_id and existing_session_id in self._sessions:
                session = self._sessions[existing_session_id]
                session.touch()
                if language:
                    session.language = language
                if timezone:
                    session.timezone = timezone
                if location:
                    session.location = location
                return session

            session_id = f"live_{int(time.time()*1000)}"
            session = LiveSession(
                session_id=session_id,
                conversation_id=conversation_id,
                user_id=user_id,
                language=language or "en",
                timezone=timezone or "UTC",
                location=location,
            )
            self._sessions[session_id] = session
            self._conv_to_session[conversation_id] = session_id
            logger.info("Created LiveSession {} for conv {}", session_id, conversation_id)
            return session

    async def get_by_conversation(self, conversation_id: str) -> Optional[LiveSession]:
        async with self._lock:
            sid = self._conv_to_session.get(conversation_id)
            return self._sessions.get(sid) if sid else None

    async def get_by_id(self, session_id: str) -> Optional[LiveSession]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def end_session(self, session_id: str) -> Optional[LiveSession]:
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session.interrupt()
                session.set_status("stopped")
                self._conv_to_session.pop(session.conversation_id, None)
                logger.info("Ended LiveSession {}", session_id)
                return session
            return None


live_session_manager = LiveSessionManager()
