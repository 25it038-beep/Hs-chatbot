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
