"""Weather service wrapper for live intent routing."""

from app.services.tools.weather_tool import WeatherService

def get_current_weather(location: str):
    ws = WeatherService()
    import asyncio
    return asyncio.run(ws.get_weather_by_city(location, forecast_days=1))

def get_weather_forecast(location: str, days: int = 7):
    ws = WeatherService()
    import asyncio
    return asyncio.run(ws.get_weather_by_city(location, forecast_days=days))
