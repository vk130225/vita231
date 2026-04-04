import json
import os

BASE_DIR = os.path.dirname(__file__)
HISTORY_FILE = os.path.join(BASE_DIR, "arce_history.json")

DEFAULT_HISTORY = {
    "RED": {"claims": 10, "risk_multiplier": 1.25},
    "ORANGE": {"claims": 7, "risk_multiplier": 1.1},
    "YELLOW": {"claims": 4, "risk_multiplier": 0.9},
    "GREEN": {"claims": 2, "risk_multiplier": 0.75},
}


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return data
    return DEFAULT_HISTORY.copy()


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2)


zone_history = load_history()


def compute_arce(
    real_data,
    movement,
    activity,
    location,
    svm_flag,
    cluster_flag,
    zone,
    model_decision,
    social_signal,
):
    rain = float(real_data.get("rain", 0))
    aqi = float(real_data.get("aqi", 0))

    rain_score = min(rain / 20.0, 1.0)
    aqi_score = min(aqi / 300.0, 1.0)
    movement_score = min(max(movement / 100.0, 0.0), 1.0)
    activity_score = min(max(activity / 100.0, 0.0), 1.0)
    location_score = 1.0 if location == 1 else 0.0

    zone_risk_map = {"RED": 1.0, "ORANGE": 0.8, "YELLOW": 0.5, "GREEN": 0.2}
    zone_risk = zone_risk_map.get(zone, 0.5)

    base_score = (
        0.22 * (1 - rain_score)
        + 0.18 * (1 - aqi_score)
        + 0.18 * movement_score
        + 0.18 * activity_score
        + 0.14 * location_score
        + 0.10 * (1 - zone_risk)
    )

    penalty = 0.0
    if svm_flag:
        penalty += 0.18
    if cluster_flag:
        penalty += 0.16
    if model_decision == "REJECTED":
        penalty += 0.12

    social_event = social_signal.get("event", "unknown")
    social_confidence = float(social_signal.get("confidence", 0))
    if social_event == "disruption" and social_confidence >= 0.6:
        penalty += 0.2
    elif social_event == "normal" and social_confidence >= 0.6:
        penalty -= 0.05

    zone_meta = zone_history.get(zone, DEFAULT_HISTORY.get(zone, {}))
    claims = int(zone_meta.get("claims", 1))
    multiplier = float(zone_meta.get("risk_multiplier", 1.0))

    historical_penalty = min((claims / 50.0) * multiplier, 0.25)
    penalty += historical_penalty

    score = max(0.0, min(base_score - penalty, 1.0))

    if score >= 0.70:
        risk_level = "LOW"
    elif score >= 0.50:
        risk_level = "MEDIUM"
    elif score >= 0.30:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    decision = "APPROVED" if score >= 0.5 else "REJECTED"

    zone_history[zone] = {
        "claims": claims + 1,
        "risk_multiplier": min(multiplier + 0.02, 1.5),
    }
    save_history(zone_history)

    return {
        "arce_score": round(score, 2),
        "risk_level": risk_level,
        "claims_in_zone": claims,
        "social_event": social_event,
        "model_decision": model_decision,
        "decision": decision,
    }
