import os
import requests

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")


def send_payout(amount: int, vpa: str = "worker@upi"):
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        return {"status": "skipped", "message": "Razorpay keys are not configured."}

    url = "https://api.razorpay.com/v1/payouts"
    headers = {
        "Content-Type": "application/json",
    }
    auth = (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)

    payout_data = {
        "account_number": "232323008",
        "fund_account": {
            "account_type": "vpa",
            "vpa": {
                "address": vpa
            }
        },
        "amount": amount * 100,
        "currency": "INR",
        "mode": "UPI",
        "purpose": "payout"
    }

    try:
        response = requests.post(url, json=payout_data, headers=headers, auth=auth, timeout=8)
        if response.status_code == 200:
            return response.json()
        return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}
