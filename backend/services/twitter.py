import os
import requests

BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
TWITTER_QUERY = os.getenv("TWITTER_QUERY", "strike OR protest OR curfew")


def get_social_signal():
    if not BEARER_TOKEN:
        return {"event": "unknown", "confidence": 0.0}

    try:
        url = "https://api.twitter.com/2/tweets/search/recent"
        headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
        params = {"query": TWITTER_QUERY, "max_results": 10}
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code != 200:
            return {"event": "unknown", "confidence": 0.0}

        tweets = response.json().get("data", [])
        if len(tweets) > 5:
            return {"event": "disruption", "confidence": 0.9}
        return {"event": "normal", "confidence": 0.3}
    except Exception:
        return {"event": "unknown", "confidence": 0.0}
