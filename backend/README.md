# VITA INSURATECH Backend

This backend implements the claim processing and fraud detection pipeline for VITA-INSURATECH.

## Features
- FastAPI backend with claim, weather, payout, and secure auth endpoints
- One-Class SVM + DBSCAN + XGBoost inference pipeline
- Adaptive ARCE risk scoring with persistent zone history
- Live weather/AQI integration with multi-source consensus
- Optional Twitter/X social disruption signal
- Razorpay payout integration via environment-configurable credentials
- Claim persistence and auto-retraining on every claim

## Setup
1. Create a Python 3.10+ virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your API keys.
4. Optionally place your Firebase service account JSON at `firebase_key.json` or set `FIREBASE_KEY_PATH`.

## Run
From the `backend` folder:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Important Environment Variables
- `WEATHER_API_KEY`
- `AQI_API_KEY`
- `TWITTER_BEARER_TOKEN`
- `FIREBASE_KEY_PATH`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_DEFAULT_VPA`

## Notes
- The backend uses a local claim store at `ml/claim_store.json` and ARCE history at `ml/arce_history.json`.
- If model artifacts are missing, the system will initialize training from synthetic data.
