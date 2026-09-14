"""Location service with privacy-first modes.

Mode A: Browser geolocation via frontend → sent to backend per request.
Mode B: Manual city stored per user/chat.
Mode C: IP fallback via ipapi.co (no key).
"""

from __future__ import annotations
from typing import Optional, Dict, Any
import httpx
from loguru import logger

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
IP_LOCATION_URL = "https://ipapi.co/json/"


async def resolve_city_to_location(city: str) -> Optional[Dict[str, Any]]:
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
            "city": r.get("name"),
            "state": r.get("admin1"),
            "country": r.get("country"),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "timezone": r.get("timezone"),
        }
    except Exception as e:
        logger.warning("resolve_city_to_location failed: {}", e)
        return None


async def ip_fallback_location() -> Optional[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(IP_LOCATION_URL)
        resp.raise_for_status()
        data = resp.json()
        return {
            "city": data.get("city"),
            "state": data.get("region"),
            "country": data.get("country_name"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "timezone": data.get("timezone"),
        }
    except Exception as e:
        logger.warning("IP fallback failed: {}", e)
        return None


class LocationService:
    """Per-chat location context holder.

    In this minimal implementation, location is passed explicitly.
    For full per-chat persistence, store in Chat.metadata JSON.
    """
    def __init__(self, chat_id: Optional[str] = None):
        self.chat_id = chat_id

    async def get_location(self, manual_city: Optional[str] = None, browser_coords: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        if browser_coords:
            lat, lon = browser_coords
            # Reverse geocode
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get("https://geocoding-api.open-meteo.com/v1/reverse", params={"latitude": lat, "longitude": lon})
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results") or []
                if results:
                    r = results[0]
                    return {
                        "city": r.get("name"),
                        "state": r.get("admin1"),
                        "country": r.get("country"),
                        "latitude": lat,
                        "longitude": lon,
                        "timezone": r.get("timezone"),
                    }
            except Exception as e:
                logger.warning("reverse geocode failed: {}", e)

        if manual_city:
            return await resolve_city_to_location(manual_city)

        # Fallback IP
        return await ip_fallback_location()
