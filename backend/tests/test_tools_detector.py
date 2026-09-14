import pytest
from app.services.tools.detector import detect_intent

def test_time_detection():
    intent, loc = detect_intent("What time is it?")
    assert intent == "time"
    assert loc is None

    intent, loc = detect_intent("What time is it in Tokyo?")
    assert intent == "time"
    assert "tokyo" in loc.lower()

def test_weather_detection():
    intent, loc = detect_intent("What's the weather today?")
    assert intent == "weather"
    
    intent, loc = detect_intent("Weather in Chennai")
    assert intent == "weather"
    assert "chennai" in loc.lower()

def test_no_intent():
    intent, loc = detect_intent("Tell me a joke")
    assert intent is None
