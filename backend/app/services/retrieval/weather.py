"""Simple weather forecasting via Open-Meteo (free, no key)."""
import re
from typing import Optional
import httpx
from loguru import logger

WEATHER_KEYWORDS = re.compile(
    r"\b(weather|forecast|temperature|temp|rain|precipitation|humidity|wind|"
    r"cloud|sunny|cloudy|storm|snow|degree|c°|f°)\b",
    re.I,
)

# Simple city -> lat/lon map for demo; can be expanded or replaced with geocoding
CITY_COORDS = {
    "new york": (40.7128, -74.0060),
    "london": (51.5074, -0.1278),
    "tokyo": (35.6762, 139.6503),
    "paris": (48.8566, 2.3522),
    "dubai": (25.2048, 55.2708),
    "sydney": (-33.8688, 151.2093),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "singapore": (1.3521, 103.8198),
    "berlin": (52.5200, 13.4050),
}

async def geocode_city(city: Optional[str]) -> Optional[tuple[float,float]]:
    if not city:
        return None
    key = city.strip().lower()
    # try direct match
    if key in CITY_COORDS:
        return CITY_COORDS[key]
    # try contains
    for name, coord in CITY_COORDS.items():
        if name in key or key in name:
            return coord
    # fallback: try Open-Meteo geocoding (free)
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    r = results[0]
                    return float(r["latitude"]), float(r["longitude"])
    except Exception as e:
        logger.warning("geocode failed for {}: {}", city, e)
    return None

async def fetch_weather(lat: float, lon: float) -> str:
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                    "timezone": "auto",
                    "forecast_days": 3,
                },
            )
            if resp.status_code != 200:
                return ""
            data = resp.json()
    except Exception as e:
        logger.warning("weather fetch failed: {}", e)
        return ""

    current = data.get("current", {})
    daily = data.get("daily", {})
    # Build markdown
    lines = ["### Weather Forecast"]
    # Current
    temp = current.get("temperature_2m")
    apparent = current.get("apparent_temperature")
    humidity = current.get("relative_humidity_2m")
    wind = current.get("wind_speed_10m")
    code = current.get("weather_code")
    loc = data.get("timezone", "")
    if temp is not None:
        lines.append(f"**Now {loc}:** {temp}°C apparent {apparent}°C, humidity {humidity}%, wind {wind} km/h, code {code}")
    # Daily
    times = daily.get("time", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_probability_max", [])
    wcodes = daily.get("weather_code", [])
    for i, day in enumerate(times):
        if i >= 3:
            break
        lines.append(f"- {day}: {tmin[i] if i < len(tmin) else '?'}°C – {tmax[i] if i < len(tmax) else '?'}°C, precip chance {precip[i] if i < len(precip) else '?'}%, code {wcodes[i] if i < len(wcodes) else '?'}")
    return "\n".join(lines)

async def get_weather_for_query(query: str, location: Optional[str]) -> str:
    if not WEATHER_KEYWORDS.search(query):
        return ""
    # Try GPS lat,lon first
    coords = None
    if location:
        loc_str = location.strip()
        # try parse lat,lon
        m = re.match(r"\s*(-?\d+(\.\d+)?)\s*,\s*(-?\d+(\.\d+)?)\s*", loc_str)
        if m:
            try:
                lat = float(m.group(1))
                lon = float(m.group(3))
                coords = (lat, lon)
            except ValueError:
                coords = None
        else:
            # treat as city name
            coords = await geocode_city(loc_str)
    if not coords:
        # try to find city name in query
        qlow = query.lower()
        for name in CITY_COORDS.keys():
            if name in qlow:
                coords = await geocode_city(name)
                if coords:
                    break
    if not coords:
        return ""
    lat, lon = coords
    return await fetch_weather(lat, lon)
