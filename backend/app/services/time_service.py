"""Time service with timezone-aware datetime.

Uses Python zoneinfo, Open-Meteo geocoding for city -> timezone.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any
import httpx
from loguru import logger

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

async def resolve_timezone(location: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(GEOCODING_URL, params={"name": location, "count": 1})
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        if results:
            return results[0].get("timezone")
    except Exception as e:
        logger.warning("resolve_timezone failed for {}: {}", location, e)
    return None

def get_current_time() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%B %d, %Y"),
        "day": now.strftime("%A"),
        "timezone": "UTC",
        "utc_offset": "+00:00",
        "datetime_iso": now.isoformat(),
    }

def get_time_for_timezone(tz_name: str) -> Dict[str, Any]:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
        tz_name = "UTC"
    now = datetime.now(tz)
    offset = now.strftime("%z")
    offset_fmt = f"{offset[:3]}:{offset[3:]}" if len(offset)==5 else "+00:00"
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%B %d, %Y"),
        "day": now.strftime("%A"),
        "timezone": tz_name,
        "utc_offset": offset_fmt,
        "datetime_iso": now.isoformat(),
    }

async def get_time_for_location(location: str) -> Dict[str, Any]:
    tz_name = await resolve_timezone(location)
    if not tz_name:
        return get_current_time()
    return get_time_for_timezone(tz_name)
