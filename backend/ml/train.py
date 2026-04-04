import datetime
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM
from xgboost import XGBClassifier

from .dataset import generate_dataset

BASE_DIR = os.path.dirname(__file__)
SAVE_DIR = os.path.join(BASE_DIR, "saved_models")
STORE_PATH = os.path.join(BASE_DIR, "claim_store.json")

os.makedirs(SAVE_DIR, exist_ok=True)


def load_claim_store() -> pd.DataFrame:
    if os.path.exists(STORE_PATH):
        with open(STORE_PATH, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
            if data:
                return pd.DataFrame(data)

    df = generate_dataset()
    save_claim_store(df)
    return df


def save_claim_store(df: pd.DataFrame):
    required_columns = ["rain", "temp", "aqi", "movement", "activity", "location", "label"]
    df = df.copy()
    for column in required_columns:
        if column not in df.columns:
            df[column] = 0

    if "timestamp" not in df.columns:
        df["timestamp"] = pd.Series([datetime.datetime.utcnow().isoformat()] * len(df))

    records = df.to_dict(orient="records")
    with open(STORE_PATH, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)


def train_models(df: pd.DataFrame):
    df = df.copy()
    required_columns = ["rain", "temp", "aqi", "movement", "activity", "location", "label"]
    for column in required_columns:
        if column not in df.columns:
            df[column] = 0

    X = df[["rain", "temp", "aqi", "movement", "activity", "location"]].astype(float)
    y = df["label"].astype(int)

    scaler = StandardScaler().fit(X)
    X_scaled = scaler.transform(X)

    normal_data = X_scaled[y == 1]
    if normal_data.shape[0] < 2:
        normal_data = X_scaled

    svm = OneClassSVM(gamma="auto").fit(normal_data)
    xgb = XGBClassifier(use_label_encoder=False, eval_metric="logloss", random_state=42)
    xgb.fit(X_scaled, y)

    joblib.dump(scaler, os.path.join(SAVE_DIR, "scaler.pkl"))
    joblib.dump(svm, os.path.join(SAVE_DIR, "svm.pkl"))
    joblib.dump(xgb, os.path.join(SAVE_DIR, "xgb.pkl"))

    return scaler, svm, xgb


def retrain_with_claim(
    rain: float,
    temp: float,
    aqi: float,
    movement: float,
    activity: float,
    location: int,
    label: int,
    zone: str,
    social_signal: dict,
    reported_outcome: str = None,
):
    df = load_claim_store()
    claim_record = {
        "rain": float(rain),
        "temp": float(temp),
        "aqi": float(aqi),
        "movement": float(movement),
        "activity": float(activity),
        "location": int(location),
        "label": int(label),
        "zone": zone,
        "social_event": social_signal.get("event"),
        "social_confidence": float(social_signal.get("confidence", 0)),
        "reported_outcome": reported_outcome,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }

    df = pd.concat([df, pd.DataFrame([claim_record])], ignore_index=True)
    if len(df) > 2000:
        df = df.tail(2000).reset_index(drop=True)

    save_claim_store(df)
    return train_models(df)


def initialize_training():
    df = load_claim_store()
    return train_models(df)


if __name__ == "__main__":
    initialize_training()
    print("✅ Models trained and saved")
