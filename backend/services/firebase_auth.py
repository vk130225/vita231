import os

import firebase_admin
from firebase_admin import auth, credentials

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
KEY_PATH = os.getenv("FIREBASE_KEY_PATH", os.path.join(BASE_DIR, "firebase_key.json"))

if not firebase_admin._apps:
    if os.path.exists(KEY_PATH):
        cred = credentials.Certificate(KEY_PATH)
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()


def verify_token(token: str):
    if not token:
        return None

    try:
        decoded = auth.verify_id_token(token)
        return {
            "uid": decoded.get("uid"),
            "email": decoded.get("email"),
            "phone_number": decoded.get("phone_number"),
        }
    except Exception:
        return None
