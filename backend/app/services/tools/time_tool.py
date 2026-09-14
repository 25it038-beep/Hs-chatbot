"""Time tool - native time/date queries with timezone support.

Uses Open-Meteo geocoding for timezone resolution, no API key required.
"""

from __future__ import annotations

import httpx
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any

from loguru import logger


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


async def _geocode_city(city: str) -> Optional[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(GEOCODING_URL, params={"name": city, "count": 1})
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        if not results:
            return None
        r = results[0]
        return {
            "name": r.get("name"),
            "country": r.get("country"),
            "admin1": r.get("admin1"),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "timezone": r.get("timezone"),
        }
    except Exception as e:
        logger.warning("geocode failed for {}: {}", city, e)
        return None


async def get_current_time_server() -> Dict[str, Any]:
    """Return actual current server time in UTC."""
    now = datetime.now(timezone.utc)
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%B %d, %Y"),
        "day": now.strftime("%A"),
        "timezone": "UTC",
        "utc_offset": "+00:00",
        "datetime_iso": now.isoformat(),
    }


async def get_time_by_timezone(tz_name: str) -> Dict[str, Any]:
    """Return current time for given IANA timezone."""
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
        tz_name = "UTC"
    now = datetime.now(tz)
    offset = now.strftime("%z")
    offset_fmt = f"{offset[:3]}:{offset[3:]}" if len(offset) == 5 else "+00:00"
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%B %d, %Y"),
        "day": now.strftime("%A"),
        "timezone": tz_name,
        "utc_offset": offset_fmt,
        "datetime_iso": now.isoformat(),
    }


async def get_current_time(location: Optional[str] = None) -> Dict[str, Any]:
    """Return current time/date for location or UTC if none.

    Returns dict with datetime ISO, timezone, date, time, day.
    """
    if location:
        geo = await _geocode_city(location)
        if geo and geo.get("timezone"):
            tz_name = geo["timezone"]
            data = await get_time_by_timezone(tz_name)
            data["location"] = f"{geo.get('name')}, {geo.get('admin1')}, {geo.get('country')}"
            return data
    # Fallback
    data = await get_current_time_server()
    data["location"] = location or "UTC"
    # Ensure common fields
    data.setdefault("time", data.get("datetime_iso",""))
    data.setdefault("date", "")
    data.setdefault("day", "")
    return data
