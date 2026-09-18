try:
    import pytest
except ImportError:
    pytest = None
from app.services.live_router import classify_live_intent, extract_location


def test_time_live_intent():
    intent, loc = classify_live_intent("What time is it?")
    assert intent == "TIME"
    assert loc is None

    intent, loc = classify_live_intent("What's the current time?")
    assert intent == "TIME"
    assert loc is None

    intent, loc = classify_live_intent("What is today's date?")
    assert intent == "TIME"
    assert loc is None


def test_timezone_live_intent():
    intent, loc = classify_live_intent("What time is it in Tokyo?")
    assert intent == "TIMEZONE"
    assert loc is not None
    assert "tokyo" in loc.lower()

    intent, loc = classify_live_intent("time in London")
    assert intent == "TIMEZONE"
    assert loc is not None
    assert "london" in loc.lower()


def test_weather_current_live_intent():
    intent, loc = classify_live_intent("What's the weather today?")
    assert intent == "WEATHER_CURRENT"

    intent, loc = classify_live_intent("Weather in Chennai")
    assert intent == "WEATHER_CURRENT"
    assert loc is not None
    assert "chennai" in loc.lower()


def test_weather_forecast_live_intent():
    intent, loc = classify_live_intent("Weather forecast for Paris tomorrow")
    assert intent == "WEATHER_FORECAST"
    assert loc is not None
    assert "paris" in loc.lower()

    intent, loc = classify_live_intent("Will it rain tomorrow in Seattle?")
    assert intent == "WEATHER_FORECAST"
    assert loc is not None
    assert "seattle" in loc.lower()


def test_location_live_intent():
    intent, loc = classify_live_intent("Where am I?")
    assert intent == "LOCATION"
    assert loc is None

    intent, loc = classify_live_intent("What is my location?")
    assert intent == "LOCATION"
    assert loc is None


def test_non_live_queries():
    intent, loc = classify_live_intent("Write a Python function to sort an array")
    assert intent is None
    assert loc is None

    intent, loc = classify_live_intent("Tell me a funny joke")
    assert intent is None
    assert loc is None


def test_tamil_availability_check():
    from app.live.tamil_provider import is_tamil_voice_available, TAMIL_LANGUAGE_CODE
    status = is_tamil_voice_available()
    assert status["language"] == TAMIL_LANGUAGE_CODE
    assert status["supported"] is True
    assert status["enabled"] is True


@pytest.mark.asyncio
async def test_tamil_provider_capabilities():
    from app.live.tamil_provider import TamilVoiceProvider
    provider = TamilVoiceProvider()
    assert provider.language == "ta"
    prompt = provider.get_prompt_instruction()
    assert prompt is not None
    assert "Tamil" in prompt
    # Languages list contains both en and ta
    langs = provider.get_supported_languages()
    assert "en" in langs
    assert "ta" in langs



@pytest.mark.asyncio
async def test_live_languages_endpoint():
    from app.live.router import live_languages
    res = await live_languages()
    assert res["default"] == "en"
    langs = {l["code"]: l for l in res["languages"]}

    # English must be supported and default
    assert "en" in langs
    assert langs["en"]["supported"] is True
    assert langs["en"]["default"] is True
    assert langs["en"]["voice"] == "Chatterbox-Multilingual"

    # Tamil must be present and supported
    assert "ta" in langs
    assert langs["ta"]["supported"] is True
    assert langs["ta"]["default"] is False
    assert langs["ta"]["native_name"] == "தமிழ்"


@pytest.mark.asyncio
async def test_live_health_endpoint_tamil_flag():
    from app.live.router import live_health
    health = await live_health()
    assert health["status"] == "healthy"
    assert health["subsystem"] == "live_voice"
    assert health["live_enabled"] is True
    # English pipeline healthy flags
    assert health["asr_configured"] is True
    assert health["llm_configured"] is True
    assert health["tts_configured"] is True
    # Tamil supported flag is now true
    assert health["tamil_supported"] is True


@pytest.mark.asyncio
async def test_session_language_switch_and_isolation():
    from app.live.session import LiveVoiceSession
    from app.live.tamil_provider import english_voice_engine, tamil_voice_engine

    class MockWS:
        def __init__(self):
            self.sent = []
        async def send_json(self, data):
            self.sent.append(data)

    ws = MockWS()
    session = LiveVoiceSession("test_isolation", ws)

    # Starts in English
    assert session.language == "en"
    assert session.voice_engine == english_voice_engine

    # Switch to Tamil
    import json
    await session.handle_message(json.dumps({"type": "set_language", "language": "ta"}))

    # Session switches smoothly to Tamil
    assert session.language == "ta"
    assert session.voice_engine == tamil_voice_engine
    lang_msgs = [m for m in ws.sent if m.get("type") == "language_changed"]
    assert len(lang_msgs) >= 1
    assert lang_msgs[-1]["language"] == "ta"

    # Switch back to English
    await session.handle_message(json.dumps({"type": "set_language", "language": "en"}))
    assert session.language == "en"
    assert session.voice_engine == english_voice_engine


@pytest.mark.asyncio
async def test_tamil_riva_health():
    from app.live.router import live_tamil_health
    h = await live_tamil_health()
    assert "enabled" in h
    assert h["language"] == "ta-IN"


@pytest.mark.asyncio
async def test_tamil_asr_handling():
    from app.live.tamil_provider import tamil_voice_engine
    assert tamil_voice_engine.language == "ta"
    # Empty audio returns empty
    res = await tamil_voice_engine.transcribe(b"")
    assert res == ""


@pytest.mark.asyncio
async def test_tamil_tts_stream():
    from app.live.tamil_provider import tamil_voice_engine
    # Empty text yields nothing without error
    chunks = []
    async for c in tamil_voice_engine.stream_synthesize(""):
        chunks.append(c)
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_tamil_roundtrip():
    from app.live.session import LiveVoiceSession
    from app.live.tamil_provider import tamil_voice_engine
    import json
    class MockWS:
        def __init__(self):
            self.sent = []
        async def send_json(self, data):
            self.sent.append(data)
    ws = MockWS()
    session = LiveVoiceSession("test_roundtrip", ws)
    # Switch to Tamil
    await session.handle_message(json.dumps({"type": "set_language", "language": "ta"}))
    assert session.language == "ta"
    assert session.voice_engine == tamil_voice_engine
    assert session.is_active is True


@pytest.mark.asyncio
async def test_english_after_tamil():
    from app.live.session import LiveVoiceSession
    from app.live.tamil_provider import english_voice_engine, tamil_voice_engine
    import json
    class MockWS:
        def __init__(self):
            self.sent = []
        async def send_json(self, data):
            self.sent.append(data)
    ws = MockWS()
    session = LiveVoiceSession("test_en_after_ta", ws)
    # Switch to Tamil
    await session.handle_message(json.dumps({"type": "set_language", "language": "ta"}))
    assert session.language == "ta"
    # Switch back to English
    await session.handle_message(json.dumps({"type": "set_language", "language": "en"}))
    assert session.language == "en"
    assert session.voice_engine == english_voice_engine


@pytest.mark.asyncio
async def test_tamil_after_english():
    from app.live.session import LiveVoiceSession
    from app.live.tamil_provider import english_voice_engine, tamil_voice_engine
    import json
    class MockWS:
        def __init__(self):
            self.sent = []
        async def send_json(self, data):
            self.sent.append(data)
    ws = MockWS()
    session = LiveVoiceSession("test_ta_after_en", ws)
    assert session.language == "en"
    assert session.voice_engine == english_voice_engine
    # Switch to Tamil
    await session.handle_message(json.dumps({"type": "set_language", "language": "ta"}))
    assert session.language == "ta"
    assert session.voice_engine == tamil_voice_engine



@pytest.mark.asyncio
async def test_language_switch_race():
    from app.live.session import LiveVoiceSession
    import json
    class MockWS:
        def __init__(self):
            self.sent = []
        async def send_json(self, data):
            self.sent.append(data)
    ws = MockWS()
    session = LiveVoiceSession("test_race", ws)
    gen0 = session.generation_id
    # Switch language increments generation_id
    await session.handle_message(json.dumps({"type": "set_language", "language": "ta"}))
    assert session.generation_id > gen0
    gen1 = session.generation_id
    await session.handle_message(json.dumps({"type": "set_language", "language": "en"}))
    assert session.generation_id > gen1


@pytest.mark.asyncio
async def test_tamil_failure_isolation():
    from app.live.session import LiveVoiceSession
    from app.live.tamil_provider import english_voice_engine, TamilVoiceEngine, TamilSpeechProvider
    from typing import Optional, AsyncGenerator, Dict, Any

    class FailingTamilProvider(TamilSpeechProvider):
        async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
            raise RuntimeError("Simulated crash in Tamil Riva driver")
        async def stream_synthesize(self, text: str, voice: Optional[str] = None) -> AsyncGenerator[bytes, None]:
            raise RuntimeError("Simulated crash in Tamil Riva driver")
            yield b""
        async def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[Dict[str, Any]]:
            raise RuntimeError("Simulated crash in Tamil Riva driver")
        async def health(self) -> Dict[str, Any]:
            return {"enabled": False, "language": "ta-IN", "reason": "Failed"}

    failing_engine = TamilVoiceEngine(provider=FailingTamilProvider())
    class MockWS:
        def __init__(self):
            self.sent = []
        async def send_json(self, data):
            self.sent.append(data)
    ws = MockWS()
    session = LiveVoiceSession("test_failure_isolation", ws)
    session.language = "ta"
    session.voice_engine = failing_engine

    # Executing turn in failing Tamil engine triggers controlled catch, not crash
    await session.execute_turn(text="வணக்கம்", turn_id="t_fail")
    # Live session recovers and English engine remains completely functional
    session.language = "en"
    session.voice_engine = english_voice_engine
    await session.execute_turn(text="Testing English after failure", turn_id="t_recover")
    user_transcripts = [m for m in ws.sent if m.get("type") == "transcript" and m.get("text") == "Testing English after failure"]
    assert len(user_transcripts) == 1


