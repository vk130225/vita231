import json
import os
import re
import smtplib
import urllib.request
from datetime import datetime
from email.message import EmailMessage
from typing import List, Optional
from urllib.error import HTTPError, URLError

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ml.arce import compute_arce
from ml.data import get_real_data
from ml.features import create_feature_vector
from ml.pipeline import reload_models, run_pipeline
from ml.train import retrain_with_claim
from services.firebase_auth import verify_token
from services.razorpay_service import send_payout
from services.twitter import get_social_signal
from services.zone_engine import get_zone

load_dotenv()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClaimRequest(BaseModel):
    lat: float = Field(..., description="Latitude of the claim location")
    lon: float = Field(..., description="Longitude of the claim location")
    movement: Optional[int] = Field(None, ge=0, le=100)
    activity: Optional[int] = Field(None, ge=0, le=100)
    location_valid: Optional[int] = Field(None, ge=0, le=1)
    reported_outcome: Optional[str] = Field(None, description="Optional truth label for supervised retraining")


class ClaimResponse(BaseModel):
    zone: str
    real_data: dict
    movement: int
    activity: int
    location_valid: int
    social_signal: dict
    svm_anomaly: int
    cluster_flag: int
    decision: str
    arce_score: float
    risk_level: str
    claims_in_zone: int
    reason: str


@app.on_event("startup")
def startup_event():
    reload_models()


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/secure")
def secure_route(authorization: str = Header(None)):
    user = verify_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"user": user}


@app.get("/")
def home():
    return {"message": "VITA Backend Running 🚀"}


SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT", "587")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@vita-insuratech.com")
EMAIL_TO = os.getenv("EMAIL_TO", "claims@vita-insuratech.com")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")


@app.get("/weather")
def weather(lat: float, lon: float):
    real = get_real_data(lat, lon)
    zone = get_zone(lat, lon)
    return {"zone": zone, "real_data": real, "aqi": real.get("aqi", 50)}


@app.get("/aqi")
def aqi(lat: float, lon: float):
    real = get_real_data(lat, lon)
    return {"aqi": real.get("aqi", 50)}


@app.get("/risk")
def risk(lat: float, lon: float):
    real = get_real_data(lat, lon)
    zone = get_zone(lat, lon)
    now = datetime.utcnow()
    hour = now.hour
    movement = 75 if 9 <= hour <= 18 else 45
    activity = 80 if 9 <= hour <= 18 else 35
    location_valid = 1
    social_signal = get_social_signal()

    return {
        "zone": zone,
        "real_data": real,
        "movement": movement,
        "activity": activity,
        "location_valid": location_valid,
        "social_signal": social_signal,
    }


@app.post("/claim", response_model=ClaimResponse)
def process_claim(request: ClaimRequest):
    social_signal = get_social_signal()
    zone = get_zone(request.lat, request.lon, social_signal)
    real = get_real_data(request.lat, request.lon)

    movement = request.movement if request.movement is not None else int(np.random.choice([70, 80, 85]))
    activity = request.activity if request.activity is not None else int(np.random.choice([60, 75, 85]))
    location = request.location_valid if request.location_valid in (0, 1) else 1

    features = create_feature_vector(real, movement, activity, location)
    ml_result = run_pipeline(features)

    arce_result = compute_arce(
        real,
        movement,
        activity,
        location,
        ml_result["svm_anomaly"],
        ml_result["cluster_flag"],
        zone,
        ml_result["decision"],
        social_signal,
    )

    reported = (request.reported_outcome or "").strip().lower()
    if reported == "approved":
        label = 1
    elif reported == "rejected":
        label = 0
    else:
        label = 1 if ml_result["decision"] == "APPROVED" and arce_result["decision"] == "APPROVED" else 0

    retrain_with_claim(
        rain=real["rain"],
        temp=real["temp"],
        aqi=real["aqi"],
        movement=movement,
        activity=activity,
        location=location,
        label=label,
        zone=zone,
        social_signal=social_signal,
        reported_outcome=request.reported_outcome,
    )

    reload_models()

    reason = (
        "Claim approved because the ARCE risk score and ML risk model both returned approval." 
        if arce_result["decision"] == "APPROVED" else
        "Claim rejected because the ARCE risk score indicates elevated fraud or risk with your submitted claim."
    )

    return {
        "zone": zone,
        "real_data": real,
        "movement": movement,
        "activity": activity,
        "location_valid": location,
        "social_signal": social_signal,
        **ml_result,
        **arce_result,
        "reason": reason,
    }


@app.post("/payout")
def payout(amount: int, vpa: Optional[str] = None):
    target_vpa = vpa or os.getenv("RAZORPAY_DEFAULT_VPA", "worker@upi")
    return send_payout(amount, target_vpa)
