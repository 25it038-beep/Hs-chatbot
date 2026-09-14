import pytest
import asyncio
from app.realtime.session import live_session_manager, LiveSession
from app.realtime.processor import live_conversation_processor
from app.services.model_providers.base import StreamChunk


@pytest.mark.asyncio
async def test_session_lifecycle():
    conv_id = "test_conv_123"
    session = await live_session_manager.get_or_create(
        conversation_id=conv_id,
        language="en",
        timezone="Asia/Kolkata",
        location="Chennai",
    )
    assert session is not None
    assert session.conversation_id == conv_id
    assert session.language == "en"
    assert session.timezone == "Asia/Kolkata"
    assert session.location == "Chennai"
    assert session.status == "idle"

    # Status transitions
    session.set_status("listening")
    assert session.status == "listening"

    # Message addition
    session.add_user_message("Hello HSBot")
    session.add_assistant_message("Hello! How can I help you today?")
    assert len(session.history) == 2

    history_prompt = session.get_recent_history_prompt(max_turns=2)
    assert len(history_prompt) == 2
    assert history_prompt[0]["content"] == "Hello HSBot"

    # Session lookup
    lookup = await live_session_manager.get_by_conversation(conv_id)
    assert lookup.session_id == session.session_id

    # Interruption
    session.current_assistant_text = "I was about to say..."
    interrupted_text = session.interrupt()
    assert interrupted_text == "I was about to say..."
    assert session.status == "interrupted"
    assert session.history[-1].interrupted is True

    # End session
    ended = await live_session_manager.end_session(session.session_id)
    assert ended.status == "stopped"
    assert await live_session_manager.get_by_conversation(conv_id) is None


@pytest.mark.asyncio
async def test_live_tool_execution():
    session = LiveSession(
        session_id="test_tool_session",
        conversation_id="conv_tool",
        timezone="Asia/Kolkata",
        location="Chennai",
    )

    # Test TIME tool
    time_res = await live_conversation_processor.execute_live_tool("TIME", None, session)
    assert time_res is not None
    assert time_res["tool"] == "TIME"
    assert "The time is" in time_res["spoken"]

    # Test LOCATION tool
    loc_res = await live_conversation_processor.execute_live_tool("LOCATION", None, session)
    assert loc_res is not None
    assert loc_res["tool"] == "LOCATION"
    assert "Chennai" in loc_res["spoken"]


@pytest.mark.asyncio
async def test_stream_utterance_with_tool(monkeypatch):
    session = LiveSession(
        session_id="test_stream_session",
        conversation_id="conv_stream",
        timezone="Asia/Kolkata",
        location="Chennai",
    )

    events = []
    async for event in live_conversation_processor.stream_utterance_response(session, "what is the time right now?"):
        events.append(event)

    types = [e["type"] for e in events]
    assert "status" in types
    assert "tool_executed" in types
    assert "ai_text_chunk" in types
    assert "ai_text_done" in types
    assert session.status == "listening"


@pytest.mark.asyncio
async def test_stream_utterance_llm_interruption(monkeypatch):
    session = LiveSession(
        session_id="test_interrupt_session",
        conversation_id="conv_interrupt",
    )

    async def mock_generate_stream(*args, **kwargs):
        tokens = ["This", " is", " a", " long", " response", " that", " gets", " interrupted."]
        for tok in tokens:
            yield StreamChunk(type="content", content=tok)
            await asyncio.sleep(0.05)

    monkeypatch.setattr(live_conversation_processor.chat_provider, "generate_stream", mock_generate_stream)

    received_tokens = []

    async def consumer():
        async for event in live_conversation_processor.stream_utterance_response(session, "Tell me a long story"):
            if event["type"] == "ai_text_chunk":
                received_tokens.append(event["chunk"])
                if len(received_tokens) >= 3:
                    # Trigger barge-in interrupt mid-stream!
                    session.interrupt()

    await consumer()
    # Should have stopped early
    assert len(received_tokens) >= 3
    assert len(received_tokens) < 8
    assert session.abort_requested is True
