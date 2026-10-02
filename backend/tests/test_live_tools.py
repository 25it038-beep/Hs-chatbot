"""
Unit and integration tests for HSBot Live Voice Tool Layer.
Verifies:
- Zero-latency smalltalk / reasoning bypass (no tools triggered)
- Precise tool classification (time, weather, web search, location, rag)
- Compound queries (multi-tool concurrent execution)
- Safe fallback / timeout handling without crashing
- Short-TTL in-memory caching
- Session barge-in cancellation of pending tool task
"""

import asyncio
import time
import pytest
from unittest.mock import patch, AsyncMock

from app.live.tools import LiveToolRouter, LiveToolResult, _LIVE_CACHE
from app.live.session import LiveVoiceSession


class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
        self.closed = False

    async def accept(self):
        pass

    async def send_json(self, data):
        self.sent_messages.append(data)

    async def receive_text(self) -> str:
        await asyncio.sleep(10)
        return ""


# 1. Non-Tool Bypass for Smalltalk & General Reasoning
def test_smalltalk_and_reasoning_bypass():
    chatter_queries = [
        "Hello",
        "hi there",
        "how are you",
        "good morning!",
        "who are you?",
        "tell me a joke",
        "Explain Python lists",
        "tell me about quantum entanglement",
        "write a poem about the sea",
        "how does a car engine work",
        "thanks a lot",
    ]
    for q in chatter_queries:
        tools = LiveToolRouter.classify_tools(q)
        assert len(tools) == 0, f"Expected 0 tools for '{q}', got {tools}"


# 2. Time Tool Classification & Execution
@pytest.mark.asyncio
async def test_time_tool_classification_and_execution():
    time_queries = [
        "What time is it in Tokyo?",
        "what is the time",
        "what is the current time",
        "tell me the time",
        "time in London",
    ]
    for q in time_queries:
        tools = LiveToolRouter.classify_tools(q)
        assert len(tools) == 1, f"Expected 1 tool for '{q}', got {tools}"
        assert tools[0][0] == "time"

    res = await LiveToolRouter.execute_tool("time", "What time is it in Tokyo?", location="Tokyo")
    assert res.success is True
    assert res.tool_name == "time"
    assert "REAL-TIME TIME DATA" in res.context_text
    assert "Tokyo" in res.context_text or "UTC" in res.context_text


# 2.1 Capability Inquiry Classification & Execution
@pytest.mark.asyncio
async def test_capabilities_inquiry():
    cap_queries = [
        "can you do web searches and time access",
        "can you search the web",
        "can you access the time",
        "do you have web search",
    ]
    for q in cap_queries:
        tools = LiveToolRouter.classify_tools(q)
        assert len(tools) == 1, f"Expected capabilities tool for '{q}', got {tools}"
        assert tools[0][0] == "capabilities"

    res = await LiveToolRouter.execute_tool("capabilities", "can you do web searches and time access")
    assert res.success is True
    assert "Live Web Search: ACTIVE" in res.context_text
    assert "Live Time Access: ACTIVE" in res.context_text


# 3. Weather Tool Classification, Execution & Caching
@pytest.mark.asyncio
async def test_weather_tool_and_cache():
    q = "What's the weather in Chennai?"
    tools = LiveToolRouter.classify_tools(q)
    assert any(t[0] == "weather" for t in tools)

    mock_weather = {
        "location": "Chennai",
        "current": {
            "temperature": 31,
            "condition": "Partly Cloudy",
            "humidity": 70,
            "wind_speed": 14,
            "rain_probability": 10,
        }
    }

    with patch("app.services.tools.weather_tool.WeatherService.get_weather_by_city", new_callable=AsyncMock) as m_w:
        m_w.return_value = mock_weather
        
        # 1st call: fetch
        res1 = await LiveToolRouter.execute_tool("weather", q, location="Chennai")
        assert res1.success is True
        assert "31°C" in res1.context_text
        assert m_w.call_count == 1

        # 2nd call: should hit cache
        res2 = await LiveToolRouter.execute_tool("weather", q, location="Chennai")
        assert res2.success is True
        assert "31°C" in res2.context_text
        assert m_w.call_count == 1  # No extra network call due to cache


# 4. Web Search Tool Classification & Execution
@pytest.mark.asyncio
async def test_web_search_tool():
    q = "Search the web for latest AI news today"
    tools = LiveToolRouter.classify_tools(q)
    assert any(t[0] == "web_search" for t in tools)

    with patch("app.services.websearch.WebSearchService.search", new_callable=AsyncMock) as m_s:
        m_s.return_value = "Latest AI models were released today with improved reasoning."
        res = await LiveToolRouter.execute_tool("web_search", q)
        assert res.success is True
        assert "CURRENT REAL-TIME WEB SEARCH RESULTS" in res.context_text
        assert "improved reasoning" in res.context_text


# 5. Compound Multi-Tool Query Concurrent Execution
@pytest.mark.asyncio
async def test_compound_query_concurrent_execution():
    q = "What's the weather in Chennai and what's the latest news today?"
    tools = LiveToolRouter.classify_tools(q)
    
    tool_names = [t[0] for t in tools]
    assert "weather" in tool_names
    assert "web_search" in tool_names

    with patch("app.services.tools.weather_tool.WeatherService.get_weather_by_city", new_callable=AsyncMock) as m_w, \
         patch("app.services.websearch.WebSearchService.search", new_callable=AsyncMock) as m_s:
        
        m_w.return_value = {"location": "Chennai", "current": {"temperature": 32, "condition": "Sunny"}}
        m_s.return_value = "Major tech breakthrough announced."

        results = await LiveToolRouter.execute_tools_concurrently(tools, q, timeout_s=3.5)
        assert len(results) == 2
        assert all(r.success for r in results)


# 6. Location Tool Classification & Execution
@pytest.mark.asyncio
async def test_location_tool():
    _LIVE_CACHE.clear()
    q = "Where am I right now?"
    tools = LiveToolRouter.classify_tools(q)
    assert any(t[0] == "location" for t in tools)

    with patch("app.live.tools.ip_fallback_location", new_callable=AsyncMock) as m_loc:
        m_loc.return_value = {"city": "Bengaluru", "state": "Karnataka", "country": "India"}
        res = await LiveToolRouter.execute_tool("location", q)
        assert res.success is True
        assert "Bengaluru" in res.context_text


# 7. Uploaded Documents / RAG Tool Classification
def test_rag_tool_classification():
    q = "What does my uploaded document say about revenue?"
    tools = LiveToolRouter.classify_tools(q)
    assert any(t[0] == "rag" for t in tools)


# 8. Timeout Graceful Degradation
@pytest.mark.asyncio
async def test_tool_timeout_graceful_handling():
    _LIVE_CACHE.clear()
    async def _slow_call(*args, **kwargs):
        await asyncio.sleep(2.0)
        return {}

    with patch("app.services.tools.weather_tool.WeatherService.get_weather_by_city", side_effect=_slow_call):
        res = await LiveToolRouter.execute_tool("weather", "weather in London", location="London", timeout_s=0.05)
        assert res.success is False
        assert "temporarily unavailable" in res.context_text


# 9. Session Barge-In Tool Cancellation
@pytest.mark.asyncio
async def test_session_barge_in_cancels_tool_task():
    ws = MockWebSocket()
    session = LiveVoiceSession("test_tool_session", ws)

    async def _long_tool():
        await asyncio.sleep(5.0)
        return [LiveToolResult("weather", "context", "status")]

    session._tool_task = asyncio.create_task(_long_tool())
    assert not session._tool_task.done()

    # User barges in
    await session.interrupt()
    await asyncio.sleep(0)  # Yield to event loop to let task catch CancelledError
    assert session._tool_task.cancelled() or session._tool_task.done()
