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
    r"\bcarry an umbrella\b",
    r"\bhow hot\b",
    r"\bhow cold\b",
]

def detect_intent(query: str) -> Tuple[Optional[Literal["time","weather"]], Optional[str]]:
    q = query.lower()
    # Helper to extract location after in/at/for
    def extract_location(text: str) -> Optional[str]:
        # Try in/at/for first
        m = re.search(r"\b(?:in|at|for)\s+([a-zA-Z\s]+?)(?:\?|$|\.|,|and)", text)
        if m:
            loc = m.group(1).strip()
            # Remove trailing words
            loc = re.sub(r"\b(tomorrow|today|weather|forecast|temperature|the|my location|here|outside)\b", "", loc, flags=re.I).strip()
            loc = re.sub(r"\s+", " ", loc)
            # Normalize empty / here / my location
            if not loc or loc in ("here", "my location"):
                return None
            # Take first city before 'and'
            loc = loc.split(" and ")[0].split(" or ")[0].strip()
            return loc if loc else None
        return None

    for pat in _TIME_PATTERNS:
        if re.search(pat, q):
            location = extract_location(q)
            return "time", location
    for pat in _WEATHER_PATTERNS:
        if re.search(pat, q):
            location = extract_location(q)
            # Fallback for "weather X" pattern
            if not location:
                m = re.search(r"weather\s+(?:in|at|for)?\s*([a-zA-Z\s]+)", q)
                if m:
                    loc = m.group(1).strip()
                    loc = re.sub(r"\b(tomorrow|today|weather|forecast|temperature|the|my location|here|outside)\b", "", loc, flags=re.I).strip()
                    if loc and loc not in ("here", "my location"):
                        location = loc.split(" and ")[0]
            return "weather", location
    return None, None
