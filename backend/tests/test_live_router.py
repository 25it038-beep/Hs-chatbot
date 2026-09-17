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


def test_tamil_availability_check_default():
    from app.live.tamil_provider import is_tamil_voice_available, TAMIL_LANGUAGE_CODE
    status = is_tamil_voice_available()
    assert status["language"] == TAMIL_LANGUAGE_CODE
    assert status["supported"] is False
    assert status["code"] == "TAMIL_TTS_NOT_SUPPORTED_BY_SELECTED_NVIDIA_MODEL"
    assert "Tamil Riva" in status["reason"] or "unavailable" in status["reason"]


@pytest.mark.asyncio
async def test_tamil_provider_raises_when_unsupported():
    from app.live.tamil_provider import TamilVoiceProvider, TamilVoiceUnavailableError
    provider = TamilVoiceProvider()

    with pytest.raises(TamilVoiceUnavailableError) as exc_asr:
        await provider.transcribe(b"fake_pcm")
    assert exc_asr.value.code in ("TAMIL_VOICE_UNAVAILABLE", "TAMIL_ASR_UNAVAILABLE")

    with pytest.raises(TamilVoiceUnavailableError) as exc_tts:
        async for _ in provider.stream_synthesize("வணக்கம்"):
            pass
    assert exc_tts.value.code in ("TAMIL_VOICE_UNAVAILABLE", "TAMIL_TTS_UNAVAILABLE")


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

    # Tamil must be present, unsupported, and not default
    assert "ta" in langs
    assert langs["ta"]["supported"] is False
    assert langs["ta"]["default"] is False
    assert langs["ta"]["voice"] == "UNAVAILABLE"
    assert "Tamil Riva" in langs["ta"]["reason"] or "unavailable" in langs["ta"]["reason"]


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
    # Tamil supported flag is accurately false
    assert health["tamil_supported"] is False


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

    # User attempts to switch to Tamil (which is unprovisioned)
    import json
    await session.handle_message(json.dumps({"type": "set_language", "language": "ta"}))

    # Error message emitted, session remains safely on English
    errors = [m for m in ws.sent if m.get("type") == "error"]
    assert len(errors) == 1
    assert errors[0]["code"] == "TAMIL_VOICE_UNAVAILABLE"
    assert session.language == "en"
    assert session.voice_engine == english_voice_engine

    # Switch explicitly to English works cleanly
    await session.handle_message(json.dumps({"type": "set_language", "language": "en"}))
    lang_changes = [m for m in ws.sent if m.get("type") == "language_changed"]
    assert len(lang_changes) >= 1
    assert session.language == "en"
    assert session.voice_engine == english_voice_engine


@pytest.mark.asyncio
async def test_tamil_riva_health():
    from app.live.router import live_tamil_health
    from app.live.tamil_provider import tamil_riva_provider
    h = await live_tamil_health()
    assert "enabled" in h
    assert h["language"] == "ta-IN"
    if not h["enabled"]:
        assert "reason" in h
        assert "Tamil Riva" in h["reason"]
    else:
        assert h["asr"] == "healthy"
        assert h["tts"] == "healthy"
        assert h["riva"] == "healthy"


@pytest.mark.asyncio
async def test_tamil_asr():
    from app.live.tamil_provider import tamil_riva_provider, TamilVoiceUnavailableError
    with pytest.raises(TamilVoiceUnavailableError) as exc:
        await tamil_riva_provider.transcribe(b"dummy_pcm_bytes")
    assert exc.value.code == "TAMIL_ASR_UNAVAILABLE"


@pytest.mark.asyncio
async def test_tamil_tts():
    from app.live.tamil_provider import tamil_riva_provider, TamilVoiceUnavailableError
    with pytest.raises(TamilVoiceUnavailableError) as exc:
        async for _ in tamil_riva_provider.stream_synthesize("வணக்கம்"):
            pass
    assert exc.value.code == "TAMIL_TTS_UNAVAILABLE"


@pytest.mark.asyncio
async def test_tamil_roundtrip():
    from app.live.session import LiveVoiceSession
    import json
    class MockWS:
        def __init__(self):
            self.sent = []
        async def send_json(self, data):
            self.sent.append(data)
    ws = MockWS()
    session = LiveVoiceSession("test_roundtrip", ws)
    # Attempt switch to Tamil
    await session.handle_message(json.dumps({"type": "set_language", "language": "ta"}))
    errs = [m for m in ws.sent if m.get("type") == "error"]
    assert len(errs) >= 1
    assert errs[0]["code"] == "TAMIL_VOICE_UNAVAILABLE"
    # Live session remains intact and responsive
    assert session.is_active is True
    assert session.language == "en"


@pytest.mark.asyncio
async def test_english_after_tamil():
    from app.live.session import LiveVoiceSession
    from app.live.tamil_provider import english_voice_engine
    import json
    class MockWS:
        def __init__(self):
            self.sent = []
        async def send_json(self, data):
            self.sent.append(data)
    ws = MockWS()
    session = LiveVoiceSession("test_en_after_ta", ws)
    # Try switching to Tamil
    await session.handle_message(json.dumps({"type": "set_language", "language": "ta"}))
    # Then execute English text turn
    await session.execute_turn(text="Hello world", turn_id="t_en_after")
    assert session.language == "en"
    assert session.voice_engine == english_voice_engine
    transcripts = [m for m in ws.sent if m.get("type") == "transcript" and m.get("role") == "user"]
    assert len(transcripts) >= 1
    assert transcripts[0]["text"] == "Hello world"


@pytest.mark.asyncio
async def test_tamil_after_english():
    from app.live.session import LiveVoiceSession
    from app.live.tamil_provider import english_voice_engine
    import json
    class MockWS:
        def __init__(self):
            self.sent = []
        async def send_json(self, data):
            self.sent.append(data)
    ws = MockWS()
    session = LiveVoiceSession("test_ta_after_en", ws)
    # Execute English turn first
    await session.execute_turn(text="What time is it?", turn_id="t_en_first")
    assert session.language == "en"
    # Try switching to Tamil
    await session.handle_message(json.dumps({"type": "set_language", "language": "ta"}))
    # English pipeline remains untouched
    assert session.language == "en"
    assert session.voice_engine == english_voice_engine


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


