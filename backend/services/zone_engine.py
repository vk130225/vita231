from services.twitter import get_social_signal
from services.weather import get_weather


def get_zone(lat: float, lon: float, social_signal: dict = None) -> str:
    zone = get_weather(lat, lon)
    if social_signal is None:
        social_signal = get_social_signal()

    event = social_signal.get("event", "unknown")
    confidence = float(social_signal.get("confidence", 0))

    if event == "disruption" and confidence >= 0.6:
        if zone == "GREEN":
            return "YELLOW"
        if zone == "YELLOW":
            return "ORANGE"
        return "RED"

    return zone
