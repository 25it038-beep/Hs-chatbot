"""
Live query and intent router for HSBot.

Classifies incoming messages into real-time operational intents:
- TIME: General current time and date inquiries.
- TIMEZONE: Time inquiries targeted at a specific location or city.
- WEATHER_CURRENT: Real-time weather and temperature checks.
- WEATHER_FORECAST: Multi-day or future precipitation and forecast checks.
- LOCATION: User location and geographic lookup queries.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

STOP_WORDS = {
    "is",
    "it",
    "now",
    "today",
    "tomorrow",
    "tonight",
    "yesterday",
    "please",
    "the",
    "a",
    "an",
    "here",
    "outside",
    "there",
    "my",
    "location",
    "me",
    "this",
    "current",
    "right",
    "tell",
    "what",
    "whats",
    "like",
    "how",
}

_LOCATION_PATTERNS = [
    r"\bwhere am i\b",
    r"\bwhat(?:['’]s| is) my location\b",
    r"\bmy current location\b",
    r"\bwhere is my location\b",
    r"\bwhat location am i in\b",
]

_FORECAST_PATTERNS = [
    r"\bforecast\b",
    r"\btomorrow\b",
    r"\bnext week\b",
    r"\bthis weekend\b",
    r"\bupcoming days\b",
    r"\b7[\s-]day\b",
    r"\bwill it rain\b",
]

_WEATHER_PATTERNS = [
    r"\bweather\b",
    r"\btemperature\b",
    r"\bforecast\b",
    r"\brain\b",
    r"\braining\b",
    r"\bsunrise\b",
    r"\bsunset\b",
    r"\bhumidity\b",
    r"\bwind speed\b",
    r"\bhow hot\b",
    r"\bhow cold\b",
    r"\bdo i need an umbrella\b",
    r"\bcarry an umbrella\b",
]

_TIME_PATTERNS = [
    r"\bwhat time is it\b",
    r"\bcurrent time\b",
    r"\btime now\b",
    r"\bwhat(?:['’]s| is) the time\b",
    r"\btell me the time\b",
    r"\bwhat time\b",
    r"\btime in\b",
    r"\bwhat(?:['’]s| is) the date\b",
    r"\bwhat day is it\b",
    r"\btoday(?:['’]s)? date\b",
    r"\bcurrent date\b",
    r"\bwhat(?:['’]s| is) today\b",
]


def extract_location(text: str) -> Optional[str]:
    """Extract location parameter from user queries."""
    m = re.search(r"\b(?:in|at|for)\s+([a-zA-Z\s\.\-]+?)(?:\?|$|\.|,|and\b)", text, re.I)
    if m:
        candidate = m.group(1).strip()
        words = [w for w in candidate.split() if w.lower() not in STOP_WORDS]
        if words:
            return " ".join(words).strip(" .?")

    m2 = re.search(
        r"\b(?:weather|forecast|temperature)\s+(?:of\s+)?([a-zA-Z\s\.\-]+?)(?:\?|$|\.|,)",
        text,
        re.I,
    )
    if m2:
        candidate = m2.group(1).strip()
        words = [w for w in candidate.split() if w.lower() not in STOP_WORDS]
        if words:
            return " ".join(words).strip(" .?")

    return None


def classify_live_intent(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Classify whether a user query requires real-time live tools (time, weather, location).
    Returns (intent, location). If no live intent is detected, returns (None, None).
    """
    q = (query or "").strip().lower()
    if not q:
        return None, None

    for pat in _LOCATION_PATTERNS:
        if re.search(pat, q):
            return "LOCATION", None

    for pat in _TIME_PATTERNS:
        if re.search(pat, q):
            loc = extract_location(query)
            if loc:
                return "TIMEZONE", loc
            return "TIME", None

    for pat in _WEATHER_PATTERNS:
        if re.search(pat, q):
            loc = extract_location(query)
            for fpat in _FORECAST_PATTERNS:
                if re.search(fpat, q):
                    return "WEATHER_FORECAST", loc
            return "WEATHER_CURRENT", loc

    return None, None


__all__ = ["classify_live_intent", "extract_location"]
