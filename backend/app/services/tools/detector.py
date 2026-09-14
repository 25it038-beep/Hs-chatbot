"""Simple intent detector for Time/Weather tools."""

import re
from typing import Literal, Optional, Tuple

_TIME_PATTERNS = [
    r"\bwhat time is it\b",
    r"\bcurrent time\b",
    r"\btime now\b",
    r"\bwhat['’]?s the time\b",
    r"\btime in\b",
    r"\bwhat['’]?s the date\b",
    r"\bwhat day is it\b",
    r"\btoday['’]?s date\b",
]

_WEATHER_PATTERNS = [
    r"\bweather\b",
    r"\btemperature\b",
    r"\bforecast\b",
    r"\brain\b",
    r"\bsunrise\b",
    r"\bsunset\b",
    r"\bhumidity\b",
    r"\bwind\b",
    r"\bwill it rain\b",
    r"\bdo I need an umbrella\b",
    r"\bhow hot\b",
    r"\bhow cold\b",
]

def detect_intent(query: str) -> Tuple[Optional[Literal["time","weather"]], Optional[str]]:
    q = query.lower()
    for pat in _TIME_PATTERNS:
        if re.search(pat, q):
            # Try extract city after "time in"
            m = re.search(r"time in ([a-zA-Z\s]+)", q)
            location = m.group(1).strip() if m else None
            return "time", location
    for pat in _WEATHER_PATTERNS:
        if re.search(pat, q):
            # Extract city if present: "weather in X" or "weather X"
            m = re.search(r"weather (?:in|at|for)?\s*([a-zA-Z\s]+)", q)
            location = m.group(1).strip() if m else None
            # Clean location
            if location:
                location = re.sub(r"\b(weather|forecast|today|tomorrow)\b", "", location).strip()
            return "weather", location
    return None, None
