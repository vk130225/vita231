import os

import joblib
import numpy as np
from sklearn.cluster import DBSCAN

BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "saved_models")

scaler = None
svm = None
xgb = None


def load_models():
    global scaler, svm, xgb
    required_files = [
        os.path.join(MODEL_DIR, "scaler.pkl"),
        os.path.join(MODEL_DIR, "svm.pkl"),
        os.path.join(MODEL_DIR, "xgb.pkl"),
    ]
    if not all(os.path.exists(path) for path in required_files):
        from ml.train import initialize_training

        initialize_training()

    scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
    svm = joblib.load(os.path.join(MODEL_DIR, "svm.pkl"))
    xgb = joblib.load(os.path.join(MODEL_DIR, "xgb.pkl"))


def reload_models():
    load_models()


def run_pipeline(features):
    if scaler is None or svm is None or xgb is None:
        load_models()

    X = np.array([features])
    X_scaled = scaler.transform(X)

    svm_result = svm.predict(X_scaled)[0]

    points = np.vstack([X_scaled, X_scaled + 0.01, X_scaled + 0.02])
    labels = DBSCAN(eps=0.5, min_samples=2).fit(points).labels_
    cluster_flag = 1 if any(label == -1 for label in labels) or len(set(labels)) > 1 else 0

    decision = xgb.predict(X_scaled)[0]

    return {
        "svm_anomaly": int(svm_result == -1),
        "cluster_flag": cluster_flag,
        "decision": "APPROVED" if int(decision) == 1 else "REJECTED"
    }
