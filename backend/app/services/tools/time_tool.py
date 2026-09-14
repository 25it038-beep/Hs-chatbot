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


async def get_current_time(location: Optional[str] = None) -> Dict[str, Any]:
    """Return current time/date for location or UTC if none.

    Returns dict with datetime ISO, timezone, date, time, day.
    """
    if location:
        geo = await _geocode_city(location)
        if geo and geo.get("timezone"):
            tz_name = geo["timezone"]
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = timezone.utc
            now = datetime.now(tz)
            location_str = f"{geo.get('name')}, {geo.get('admin1')}, {geo.get('country')}"
        else:
            # Fallback to UTC if geocode fails
            tz = timezone.utc
            now = datetime.now(timezone.utc)
            location_str = location
    else:
        tz = timezone.utc
        now = datetime.now(timezone.utc)
        location_str = "UTC"

    # Ensure aware
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)

    return {
        "datetime": now.isoformat(),
        "timezone": str(now.tzinfo),
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M"),
        "day": now.strftime("%A"),
        "location": location_str,
    }
