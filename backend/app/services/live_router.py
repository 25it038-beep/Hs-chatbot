"""Live intent router for real-time tools.

Classifies messages into NORMAL, TIME, TIMEZONE, LOCATION, WEATHER_CURRENT, WEATHER_FORECAST
before any RAG / web search.
"""

import re
from typing import Literal, Optional, Tuple

Intent = Literal["NORMAL","TIME","TIMEZONE","LOCATION","WEATHER_CURRENT","WEATHER_FORECAST"]

_TIME_PATTERNS = [
    r"\bwhat is the time\b",
    r"\bwhat time is it\b",
    r"\bcurrent time\b",
    r"\btime now\b",
    r"\bwhat['’]?s the time\b",
    r"\bwhat['’]?s today['’]?s date\b",
    r"\bwhat day is it\b",
    r"\btoday['’]?s date\b",
]

_TIMEZONE_PATTERNS = [
    r"\btime in\b",
    r"\btime for\b",
    r"\bwhat time is it in\b",
]

_WEATHER_CURRENT_PATTERNS = [
    r"\bweather here\b",
    r"\bweather near me\b",
    r"\bweather today\b",
    r"\btemperature\b",
    r"\bcurrent weather\b",
    r"\bhow hot\b",
    r"\bhow cold\b",
    r"\bweather in\b",
    r"\bweather at\b",
    r"\bweather for\b",
]

_WEATHER_FORECAST_PATTERNS = [
    r"\bwill it rain\b",
    r"\bwill it snow\b",
    r"\bweather tomorrow\b",
    r"\bforecast\b",
    r"\b7 day forecast\b",
    r"\b7-day forecast\b",
    r"\bdo I need an umbrella\b",
    r"\bcarry an umbrella\b",
]

_LOCATION_PATTERNS = [
    r"\bwhere am I\b",
    r"\bwhat is my location\b",
    r"\bmy location\b",
]

def _extract_location(text: str) -> Optional[str]:
    m = re.search(r"\b(?:in|at|for)\s+([a-zA-Z\s]+?)(?:\?|$|\.|,|and)", text)
    if m:
        loc = re.sub(r"\s+", " ", m.group(1).strip())
        loc = re.sub(r"\b(tomorrow|today|weather|forecast|temperature|the|my location|here|outside)\b", "", loc, flags=re.I).strip()
        loc = loc.split(" and ")[0].split(" or ")[0].strip()
        return loc if loc else None
    return None

def classify_live_intent(query: str) -> Tuple[Intent, Optional[str]]:
    q = query.lower()
    # TIMEZONE first
    for pat in _TIMEZONE_PATTERNS:
        if re.search(pat, q):
            loc = _extract_location(q)
            return "TIMEZONE", loc
    # TIME
    for pat in _TIME_PATTERNS:
        if re.search(pat, q):
            loc = _extract_location(q)
            return "TIME", loc
    # LOCATION
    for pat in _LOCATION_PATTERNS:
        if re.search(pat, q):
            return "LOCATION", None
    # WEATHER FORECAST
    for pat in _WEATHER_FORECAST_PATTERNS:
        if re.search(pat, q):
            loc = _extract_location(q)
            return "WEATHER_FORECAST", loc
    # WEATHER CURRENT
    for pat in _WEATHER_CURRENT_PATTERNS:
        if re.search(pat, q):
            loc = _extract_location(q)
            return "WEATHER_CURRENT", loc
    return "NORMAL", None
