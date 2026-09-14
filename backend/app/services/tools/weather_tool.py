"""Weather tool with provider abstraction.

Default provider: Open-Meteo (free, no API key).
"""

from __future__ import annotations

import os
from typing import Optional, Dict, Any, List
import httpx
from loguru import logger

WEATHER_BASE = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


class WeatherProvider:
    async def get_weather(self, lat: float, lon: float, forecast_days: int = 7) -> Dict[str, Any]:
        raise NotImplementedError


class OpenMeteoProvider(WeatherProvider):
    async def get_weather(self, lat: float, lon: float, forecast_days: int = 7) -> Dict[str, Any]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,weather_code,relative_humidity_2m,wind_speed_10m,precipitation_probability",
            "hourly": "temperature_2m,precipitation_probability",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
            "timezone": "auto",
            "forecast_days": min(forecast_days, 16),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(WEATHER_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("Open-Meteo weather fetch failed: {}", e)
            raise

        current = data.get("current", {})
        daily = data.get("daily", {})
        # Map weather code to condition
        def code_to_condition(code: int) -> str:
            mapping = {
                0: "Clear sky",
                1: "Mainly clear",
                2: "Partly cloudy",
                3: "Overcast",
                45: "Fog",
                48: "Depositing rime fog",
                51: "Light drizzle",
                53: "Moderate drizzle",
                55: "Dense drizzle",
                61: "Slight rain",
                63: "Moderate rain",
                65: "Heavy rain",
                71: "Slight snow",
                73: "Moderate snow",
                75: "Heavy snow",
                80: "Slight rain showers",
                81: "Moderate rain showers",
                82: "Violent rain showers",
                95: "Thunderstorm",
                96: "Thunderstorm with hail",
                99: "Thunderstorm with heavy hail",
            }
            return mapping.get(code, "Unknown")

        current_condition = code_to_condition(current.get("weather_code", -1))

        # Build forecast list
        forecast: List[Dict[str, Any]] = []
        dates = daily.get("time", [])
        tmax = daily.get("temperature_2m_max", [])
        tmin = daily.get("temperature_2m_min", [])
        codes = daily.get("weather_code", [])
        precip = daily.get("precipitation_probability_max", [])
        for i, d in enumerate(dates):
            forecast.append({
                "date": d,
                "temp_max": tmax[i] if i < len(tmax) else None,
                "temp_min": tmin[i] if i < len(tmin) else None,
                "condition": code_to_condition(codes[i] if i < len(codes) else -1),
                "rain_probability": precip[i] if i < len(precip) else None,
            })

        return {
            "location": data.get("timezone"),
            "current": {
                "temperature": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "condition": current_condition,
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "rain_probability": current.get("precipitation_probability"),
            },
            "forecast": forecast,
            "daily": {
                "sunrise": daily.get("sunrise", [])[0] if daily.get("sunrise") else None,
                "sunset": daily.get("sunset", [])[0] if daily.get("sunset") else None,
            }
        }


class WeatherService:
    def __init__(self):
        provider_name = os.getenv("WEATHER_PROVIDER", "open-meteo").lower()
        if provider_name == "open-meteo":
            self.provider = OpenMeteoProvider()
        else:
            # Fallback
            self.provider = OpenMeteoProvider()

    async def get_weather_by_city(self, city: str, forecast_days: int = 7) -> Dict[str, Any]:
        # Geocode city
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(GEOCODING_URL, params={"name": city, "count": 1})
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        if not results:
            raise ValueError(f"City not found: {city}")
        r = results[0]
        lat = r["latitude"]
        lon = r["longitude"]
        location_name = f"{r.get('name')}, {r.get('admin1')}, {r.get('country')}"
        weather = await self.provider.get_weather(lat, lon, forecast_days)
        weather["location"] = location_name
        return weather
