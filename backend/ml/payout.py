from services.razorpay_service import send_payout

@app.post("/payout")
def payout(amount: int):
    return send_payout(amount)