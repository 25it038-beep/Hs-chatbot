"""Location abstraction with privacy-first handling.

Supports user-provided city, browser geolocation, and manual selection.
Per-chat location is stored in the chat model metadata (no cross-chat leakage).
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import httpx

from loguru import logger

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
REVERSE_URL = "https://geocoding-api.open-meteo.com/v1/reverse"


async def resolve_city(city_query: str) -> Optional[Dict[str, Any]]:
    """Resolve city name to lat/lon/timezone."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(GEOCODING_URL, params={"name": city_query, "count": 5})
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        if not results:
            return None
        # Return best match
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
        logger.warning("resolve_city failed for {}: {}", city_query, e)
        return None


async def reverse_geocode(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Convert lat/lon to city name."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(REVERSE_URL, params={"latitude": lat, "longitude": lon})
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
            "latitude": lat,
            "longitude": lon,
            "timezone": r.get("timezone"),
        }
    except Exception as e:
        logger.warning("reverse_geocode failed for {},{}: {}", lat, lon, e)
        return None
