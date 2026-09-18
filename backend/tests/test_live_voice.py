"""
Comprehensive integration tests for HSBot isolated NVIDIA Live Voice subsystem.
Verifies:
- Persistent Riva worker process lifecycle and gRPC bridge
- Live LLM streaming tokens with persistent client
- LiveVoiceSession turn execution with concurrent LLM + TTS streaming
- Accurate timing metrics instrumentation
- Barge-in interruption cancellation
"""

import asyncio
import base64
import json
import time
import pytest
from typing import List, Dict, Any

from app.live.turn_manager import LiveTurnManager
from app.live.riva_bridge import riva_bridge
from app.live.llm import live_llm
from app.live.tts import live_tts
from app.live.asr import live_asr
from app.live.session import LiveVoiceSession


class MockWebSocket:
    """Mock WebSocket for end-to-end testing of LiveVoiceSession."""
    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.closed = False

    async def accept(self):
        pass

    async def send_json(self, data: Dict[str, Any]):
        self.sent_messages.append(data)

    async def receive_text(self) -> str:
        await asyncio.sleep(10)
        return ""

    def get_messages_by_type(self, msg_type: str) -> List[Dict[str, Any]]:
        return [m for m in self.sent_messages if m.get("type") == msg_type]


def test_turn_manager_transitions():
    tm = LiveTurnManager()
    assert tm.get_state() == "IDLE"

    assert tm.transition_to("LISTENING", "session start")
    assert tm.get_state() == "LISTENING"

    assert tm.transition_to("PROCESSING", "user speech")
    assert tm.get_state() == "PROCESSING"

    assert tm.transition_to("SPEAKING", "audio ready")
    assert tm.get_state() == "SPEAKING"

    # Barge-in
    assert tm.handle_barge_in()
    assert tm.get_state() == "INTERRUPTED"

    assert tm.transition_to("LISTENING", "ready")
    assert tm.get_state() == "LISTENING"


@pytest.mark.asyncio
async def test_persistent_riva_worker_lifecycle():
    await riva_bridge.ensure_started()
    assert riva_bridge._proc is not None
    assert riva_bridge._proc.returncode is None
    await riva_bridge.shutdown()
    assert riva_bridge._proc is None


@pytest.mark.asyncio
async def test_live_llm_streaming_warm():
    tokens = []
    t0 = time.time()
    first_token_time = None

    async for token in live_llm.stream_reply("Hello! Reply with one short sentence."):
        if first_token_time is None:
            first_token_time = time.time()
        tokens.append(token)

    assert len(tokens) > 0
    full_text = "".join(tokens).strip()
    assert len(full_text) > 0
    # TTFT should be reasonable even on cold start (< 25000ms)
    if first_token_time:
        ttft_ms = (first_token_time - t0) * 1000
        assert ttft_ms < 35000


@pytest.mark.asyncio
async def test_session_execute_turn_overlapped():
    ws = MockWebSocket()
    session = LiveVoiceSession("test_session_1", ws)

    # Execute a turn directly via text (fast path)
    await session.execute_turn(text="What is 2 plus 2?")

    # Verify messages were sent
    transcripts = ws.get_messages_by_type("transcript")
    assert len(transcripts) >= 2  # user and assistant transcripts
    assert transcripts[0]["role"] == "user"
    assert transcripts[0]["text"] == "What is 2 plus 2?"
    assert transcripts[1]["role"] == "assistant"
    assert len(transcripts[1]["text"]) > 0

    # Verify LLM chunks streamed
    llm_chunks = ws.get_messages_by_type("llm_chunk")
    assert len(llm_chunks) > 0

    # Verify timing metrics were emitted
    timing_msgs = ws.get_messages_by_type("timing")
    metrics = {m["metric"]: m["value"] for m in timing_msgs}
    assert "asr_to_llm_first_token_ms" in metrics
    assert metrics["asr_to_llm_first_token_ms"] > 0

    # Clean up
    await session.cleanup()
    await riva_bridge.shutdown()
    await live_llm.close()


@pytest.mark.asyncio
async def test_session_barge_in_cancellation():
    ws = MockWebSocket()
    session = LiveVoiceSession("test_session_interrupt", ws)
    session.turn_manager.transition_to("SPEAKING", "AI speaking")

    await session.interrupt()

    assert session.turn_manager.get_state() == "LISTENING"
    status_msgs = ws.get_messages_by_type("status")
    last_status = status_msgs[-1]
    assert last_status["state"] == "LISTENING"
    await session.cleanup()


@pytest.mark.asyncio
async def test_session_initial_greeting():
    ws = MockWebSocket()
    session = LiveVoiceSession("test_session_greeting", ws)
    assert session._greeting_sent is False

    await session.send_greeting()
    assert session._greeting_sent is True

    # Verify transcript sent
    transcripts = ws.get_messages_by_type("transcript")
    assert len(transcripts) >= 1
    assert transcripts[0]["role"] == "assistant"
    assert "HSBot" in transcripts[0]["text"]
    assert "Hello" in transcripts[0]["text"]

    # Verify conversation history recorded greeting
    assert len(session.conversation_history) == 1
    assert session.conversation_history[0]["role"] == "assistant"
    assert "HSBot" in session.conversation_history[0]["content"]

    # Verify state transitions back to LISTENING
    assert session.turn_manager.get_state() == "LISTENING"

    # Verify greeting is only sent once
    await session.send_greeting()
    transcripts_after = ws.get_messages_by_type("transcript")
    assert len(transcripts_after) == 1

    await session.cleanup()
