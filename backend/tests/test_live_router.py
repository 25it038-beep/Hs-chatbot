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
    assert "Chatterbox-Multilingual" in status["reason"]


@pytest.mark.asyncio
async def test_tamil_provider_raises_when_unsupported():
    from app.live.tamil_provider import TamilVoiceProvider, TamilVoiceUnavailableError
    provider = TamilVoiceProvider()

    with pytest.raises(TamilVoiceUnavailableError) as exc_asr:
        await provider.transcribe(b"fake_pcm")
    assert exc_asr.value.code in ("TAMIL_VOICE_UNAVAILABLE", "TAMIL_ASR_UNAVAILABLE")

    with pytest.raises(TamilVoiceUnavailableError) as exc_tts:
        await provider.stream_synthesize("வணக்கம்")
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
    assert "Chatterbox" in langs["ta"]["reason"]


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

