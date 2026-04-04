import os

import requests

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
AIR_QUALITY_API_KEY = os.getenv("AQI_API_KEY")


def get_real_data(lat: float, lon: float):
    if WEATHER_API_KEY:
        try:
            url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={lat},{lon}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            current = data.get("current", {})
            rain = current.get("precip_mm", 0)
            temp = current.get("temp_c", 25)
            aqi = current.get("air_quality", {}).get("pm2_5", 50)
            return {"rain": rain, "temp": temp, "aqi": aqi}
        except Exception:
            pass

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
        temp = float(current.get("temperature", 25.0))
        aqi = 50.0
        if AIR_QUALITY_API_KEY:
            try:
                aqi_url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={AIR_QUALITY_API_KEY}"
                aqi_response = requests.get(aqi_url, timeout=5)
                aqi_response.raise_for_status()
                aqi_data = aqi_response.json()
                aqi = float(aqi_data.get("data", {}).get("aqi", 50) or 50)
            except Exception:
                aqi = 50.0

        return {"rain": rain, "temp": temp, "aqi": aqi}
    except Exception:
        return {"rain": 0.0, "temp": 25.0, "aqi": 50.0}
