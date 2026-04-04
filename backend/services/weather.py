import os
import requests

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
AIR_QUALITY_API_KEY = os.getenv("AQI_API_KEY")


def _get_aqi_from_waqi(lat: float, lon: float) -> float:
    if not AIR_QUALITY_API_KEY:
        return 50.0

    try:
        url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={AIR_QUALITY_API_KEY}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data.get("data", {}).get("aqi", 50) or 50)
    except Exception:
        return 50.0


def _get_weatherapi_data(lat: float, lon: float):
    if not WEATHER_API_KEY:
        return None

    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={lat},{lon}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return {
            "rain": float(data.get("current", {}).get("precip_mm", 0.0)),
            "temp": float(data.get("current", {}).get("temp_c", 25.0))
        }
    except Exception:
        return None


def _get_open_meteo_data(lat: float, lon: float):
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current_weather=true&hourly=precipitation&timezone=UTC"
        )
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        current = data.get("current_weather", {})
        rain = 0.0
        if "hourly" in data and isinstance(data["hourly"].get("precipitation"), list):
            precipitation = data["hourly"]["precipitation"]
            if precipitation:
                rain = float(precipitation[-1])

        return {
            "rain": rain,
            "temp": float(current.get("temperature", 25.0))
        }
    except Exception:
        return None


def _zone_from_conditions(rain: float, aqi: float) -> str:
    if rain > 15 or aqi > 200:
        return "RED"
    if rain > 8 or aqi > 150:
        return "ORANGE"
    if rain > 3 or aqi > 100:
        return "YELLOW"
    return "GREEN"


def get_weather(lat: float, lon: float) -> str:
    open_meteo = _get_open_meteo_data(lat, lon)
    weatherapi = _get_weatherapi_data(lat, lon)
    aqi = _get_aqi_from_waqi(lat, lon)

    if open_meteo is None and weatherapi is None:
        return "YELLOW"

    if open_meteo is None:
        return _zone_from_conditions(weatherapi["rain"], aqi)

    if weatherapi is None:
        return _zone_from_conditions(open_meteo["rain"], aqi)

    zone_primary = _zone_from_conditions(open_meteo["rain"], aqi)
    zone_secondary = _zone_from_conditions(weatherapi["rain"], aqi)

    if zone_primary == zone_secondary:
        return zone_primary

    return "YELLOW"
