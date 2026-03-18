from app.config.settings import settings
from app.config.logging import get_logger
import requests

logger = get_logger(__name__)
BASE_URL = "http://api.weatherapi.com/v1"
API_KEY = settings.WEATHER_API_KEY


def _get(endpoint: str, params: dict) -> dict:
    params["key"] = API_KEY
    response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_current_weather(city: str) -> str:
    """Get current weather conditions for a city."""
    try:
        data = _get("current.json", {"q": city, "aqi": "no"})
        c = data["current"]
        loc = data["location"]
        return (
            f"Current weather in {loc['name']}, {loc['country']}:\n"
            f"  Condition: {c['condition']['text']}\n"
            f"  Temperature: {c['temp_c']}°C (feels like {c['feelslike_c']}°C)\n"
            f"  Humidity: {c['humidity']}%\n"
            f"  Wind: {c['wind_kph']} kph {c['wind_dir']}\n"
            f"  Visibility: {c['vis_km']} km\n"
            f"  UV Index: {c['uv']}\n"
            f"  Cloud Cover: {c['cloud']}%\n"
            f"  Pressure: {c['pressure_mb']} mb"
        )
    except Exception as e:
        logger.error(f"get_current_weather failed for {city}: {e}")
        return f"Error fetching weather for {city}: {str(e)}"


def get_weather_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for next N days (1-10) for a city."""
    try:
        days = max(1, min(10, int(days)))
        data = _get("forecast.json", {"q": city, "days": days, "aqi": "no", "alerts": "no"})
        loc = data["location"]
        lines = [f"Weather forecast for {loc['name']}, {loc['country']} ({days} days):\n"]
        for day_data in data["forecast"]["forecastday"]:
            d = day_data["day"]
            lines.append(
                f"  📅 {day_data['date']}:\n"
                f"     Condition: {d['condition']['text']}\n"
                f"     Max: {d['maxtemp_c']}°C | Min: {d['mintemp_c']}°C | Avg: {d['avgtemp_c']}°C\n"
                f"     Chance of Rain: {d['daily_chance_of_rain']}%\n"
                f"     Precipitation: {d['totalprecip_mm']} mm\n"
                f"     Sunrise: {day_data['astro']['sunrise']} | Sunset: {day_data['astro']['sunset']}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"get_weather_forecast failed for {city}: {e}")
        return f"Error fetching forecast for {city}: {str(e)}"


def get_air_quality(city: str) -> str:
    """Get current air quality index for a city."""
    try:
        data = _get("current.json", {"q": city, "aqi": "yes"})
        loc = data["location"]
        aqi = data["current"].get("air_quality", {})
        aqi_index = aqi.get("us-epa-index", "N/A")
        aqi_labels = {1: "Good", 2: "Moderate", 3: "Unhealthy for Sensitive", 4: "Unhealthy", 5: "Very Unhealthy", 6: "Hazardous"}
        label = aqi_labels.get(aqi_index, "Unknown")
        return (
            f"Air Quality in {loc['name']}, {loc['country']}:\n"
            f"  Overall AQI: {aqi_index} - {label}\n"
            f"  CO: {aqi.get('co', 'N/A')} μg/m³\n"
            f"  NO2: {aqi.get('no2', 'N/A')} μg/m³\n"
            f"  O3: {aqi.get('o3', 'N/A')} μg/m³\n"
            f"  SO2: {aqi.get('so2', 'N/A')} μg/m³\n"
            f"  PM2.5: {aqi.get('pm2_5', 'N/A')} μg/m³\n"
            f"  PM10: {aqi.get('pm10', 'N/A')} μg/m³"
        )
    except Exception as e:
        logger.error(f"get_air_quality failed for {city}: {e}")
        return f"Error fetching air quality for {city}: {str(e)}"


def get_astronomy(city: str, date: str) -> str:
    """Get astronomy data (sunrise, sunset, moon phase) for a city and date (YYYY-MM-DD)."""
    try:
        data = _get("astronomy.json", {"q": city, "dt": date})
        loc = data["location"]
        astro = data["astronomy"]["astro"]
        return (
            f"Astronomy data for {loc['name']}, {loc['country']} on {date}:\n"
            f"  Sunrise: {astro['sunrise']}\n"
            f"  Sunset: {astro['sunset']}\n"
            f"  Moonrise: {astro['moonrise']}\n"
            f"  Moonset: {astro['moonset']}\n"
            f"  Moon Phase: {astro['moon_phase']}\n"
            f"  Moon Illumination: {astro['moon_illumination']}%"
        )
    except Exception as e:
        logger.error(f"get_astronomy failed for {city} on {date}: {e}")
        return f"Error fetching astronomy data for {city}: {str(e)}"


def get_historical_weather(city: str, date: str) -> str:
    """Get historical weather for a city on a specific date (YYYY-MM-DD)."""
    try:
        data = _get("history.json", {"q": city, "dt": date})
        loc = data["location"]
        day = data["forecast"]["forecastday"][0]["day"]
        return (
            f"Historical weather in {loc['name']}, {loc['country']} on {date}:\n"
            f"  Condition: {day['condition']['text']}\n"
            f"  Max Temp: {day['maxtemp_c']}°C\n"
            f"  Min Temp: {day['mintemp_c']}°C\n"
            f"  Avg Temp: {day['avgtemp_c']}°C\n"
            f"  Precipitation: {day['totalprecip_mm']} mm\n"
            f"  Avg Humidity: {day['avghumidity']}%"
        )
    except Exception as e:
        logger.error(f"get_historical_weather failed for {city} on {date}: {e}")
        return f"Error fetching historical weather for {city}: {str(e)}"


def search_timezone(city: str) -> str:
    """Get current local time and timezone information for a city."""
    try:
        data = _get("timezone.json", {"q": city})
        loc = data["location"]
        return (
            f"Timezone info for {loc['name']}, {loc['country']}:\n"
            f"  Local Time: {loc['localtime']}\n"
            f"  Timezone ID: {loc['tz_id']}\n"
            f"  UTC Offset: {loc['utc_offset']}"
        )
    except Exception as e:
        logger.error(f"search_timezone failed for {city}: {e}")
        return f"Error fetching timezone for {city}: {str(e)}"
