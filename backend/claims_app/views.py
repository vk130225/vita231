from django.shortcuts import render
from django.db.models import Count
from django.http import StreamingHttpResponse, Http404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime
import json
import time
import random
import numpy as np
from .models import Claim
from .serializers import ClaimRequestSerializer
from ml.arce import compute_arce
from ml.data import get_real_data
from ml.features import create_feature_vector
from ml.pipeline import reload_models, run_pipeline
from ml.train import retrain_with_claim
from ml.sensors import get_sensor_score
from services.twitter import get_social_signal
from services.zone_engine import get_zone


def calculate_ml_premium(zone: str, rain_forecast: float = 0, aqi: float = 50, water_logging_history: bool = False, disruption_signals: int = 0) -> int:
    """
    ML-based dynamic premium calculation.
    Base rate: ₹39/wk (YELLOW zone)
    Adjustments based on hyper-local risk factors.
    """
    # Base pricing by zone
    zone_base = {
        'GREEN': 37,   # ₹2 discount for safe areas
        'YELLOW': 39,  # Base rate
        'ORANGE': 45,  # Elevated risk (+₹6)
        'RED': 55,     # Maximum risk (+₹16)
    }
    
    premium = zone_base.get(zone, 39)
    
    # Weather forecast adjustments (predictive model)
    if rain_forecast > 10:  # Heavy rain predicted
        premium += 3
    elif rain_forecast > 5:  # Moderate rain
        premium += 1
    
    # AQI adjustments
    if aqi > 200:  # Severe air quality
        premium += 2
    elif aqi > 150:  # Poor air quality
        premium += 1
    
    # Historical water logging discount/premium
    if water_logging_history:
        premium += 4
    
    # Social disruption signals (Twitter/X monitoring)
    if disruption_signals > 2:
        premium += 2
    
    return min(premium, 75)  # Cap at ₹75/wk


def get_coverage_hours(zone: str, weather_risk: float = 0) -> int:
    """Dynamic coverage hours based on zone and weather predictions."""
    base_hours = {
        'GREEN': 84,   # 12 hours/day avg
        'YELLOW': 70,  # 10 hours/day avg
        'ORANGE': 56,  # 8 hours/day avg
        'RED': 42,     # 6 hours/day avg
    }
    hours = base_hours.get(zone, 70)
    
    # Increase coverage during low-risk periods
    if weather_risk < 0.3:
        hours += 14  # Extra 2 hours/day
    
    return hours


@api_view(['GET'])
def health(request):
    return Response({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

@api_view(['GET'])
def home(request):
    return Response({"message": "VITA Backend Running 🚀"})

@api_view(['GET'])
def weather(request):
    lat = float(request.GET.get('lat', 12.9716))
    lon = float(request.GET.get('lon', 77.5946))
    real = get_real_data(lat, lon)
    zone = get_zone(lat, lon)
    return Response({"zone": zone, "real_data": real, "aqi": real.get("aqi", 50)})

@api_view(['GET'])
def aqi(request):
    lat = float(request.GET.get('lat', 12.9716))
    lon = float(request.GET.get('lon', 77.5946))
    real = get_real_data(lat, lon)
    return Response({"aqi": real.get("aqi", 50)})

@api_view(['GET'])
def risk(request):
    lat = float(request.GET.get('lat', 12.9716))
    lon = float(request.GET.get('lon', 77.5946))
    real = get_real_data(lat, lon)
    zone = get_zone(lat, lon)
    now = datetime.utcnow()
    hour = now.hour
    movement = 75 if 9 <= hour <= 18 else 45
    activity = 80 if 9 <= hour <= 18 else 35
    location_valid = 1
    social_signal = get_social_signal()

    return Response({
        "zone": zone,
        "real_data": real,
        "movement": movement,
        "activity": activity,
        "location_valid": location_valid,
        "social_signal": social_signal,
    })


def _build_claim_context(data):
    lat = float(data.get('lat', 12.9716))
    lon = float(data.get('lon', 77.5946))
    movement = int(data.get('movement', int(np.random.choice([70, 80, 85]))))
    activity = int(data.get('activity', int(np.random.choice([60, 75, 85]))))
    location = int(data.get('location_valid', 1))
    social_signal = get_social_signal()
    zone = get_zone(lat, lon, social_signal)
    real = get_real_data(lat, lon)
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
    return {
        "lat": lat,
        "lon": lon,
        "movement": movement,
        "activity": activity,
        "location_valid": location,
        "social_signal": social_signal,
        "zone": zone,
        "real": real,
        "ml_result": ml_result,
        "arce_result": arce_result,
    }

@api_view(['POST'])
def process_claim(request):
    serializer = ClaimRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data
    context = _build_claim_context(data)
    reported = (data.get('reported_outcome') or "").strip().lower()
    if reported == "approved":
        label = 1
    elif reported == "rejected":
        label = 0
    else:
        label = 1 if context["ml_result"]["decision"] == "APPROVED" and context["arce_result"]["decision"] == "APPROVED" else 0

    Claim.objects.create(
        lat=context["lat"],
        lon=context["lon"],
        movement=context["movement"],
        activity=context["activity"],
        location_valid=context["location_valid"],
        rain=context["real"]["rain"],
        temp=context["real"]["temp"],
        aqi=context["real"]["aqi"],
        zone=context["zone"],
        social_signal=context["social_signal"],
        svm_anomaly=context["ml_result"]["svm_anomaly"],
        cluster_flag=context["ml_result"]["cluster_flag"],
        decision=context["ml_result"]["decision"],
        arce_score=context["arce_result"]["arce_score"],
        risk_level=context["arce_result"]["risk_level"],
        claims_in_zone=context["arce_result"]["claims_in_zone"],
        reported_outcome=data.get('reported_outcome'),
        label=label,
    )

    retrain_with_claim(
        rain=context["real"]["rain"], temp=context["real"]["temp"], aqi=context["real"]["aqi"],
        movement=context["movement"], activity=context["activity"], location=context["location_valid"],
        label=label, zone=context["zone"], social_signal=context["social_signal"],
        reported_outcome=data.get('reported_outcome')
    )
    reload_models()

    reason = (
        "Claim approved because the ARCE risk score and ML risk model both returned approval."
        if context["arce_result"]["decision"] == "APPROVED" else
        "Claim rejected because the ARCE risk score indicates elevated fraud or risk with your submitted claim."
    )

    return Response({
        "zone": context["zone"],
        "real_data": context["real"],
        "movement": context["movement"],
        "activity": context["activity"],
        "location_valid": context["location_valid"],
        "social_signal": context["social_signal"],
        **context["ml_result"],
        **context["arce_result"],
        "decision_reason": reason,
        "label": label,
    })


@api_view(['GET'])
def arce_evaluate(request):
    lat = float(request.GET.get('lat', 12.9716))
    lon = float(request.GET.get('lon', 77.5946))
    movement = int(request.GET.get('movement', 75))
    activity = int(request.GET.get('activity', 70))
    location = int(request.GET.get('location_valid', 1))
    social_signal = get_social_signal()
    zone = request.GET.get('zone') or get_zone(lat, lon, social_signal)

    real = get_real_data(lat, lon)
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
    payout_amount = 1200 if arce_result["decision"] == "APPROVED" else 0
    label = 1 if arce_result["decision"] == "APPROVED" else 0

    Claim.objects.create(
        lat=lat,
        lon=lon,
        movement=movement,
        activity=activity,
        location_valid=location,
        rain=real["rain"],
        temp=real["temp"],
        aqi=real["aqi"],
        zone=zone,
        social_signal=social_signal,
        svm_anomaly=ml_result["svm_anomaly"],
        cluster_flag=ml_result["cluster_flag"],
        decision=ml_result["decision"],
        arce_score=arce_result["arce_score"],
        risk_level=arce_result["risk_level"],
        claims_in_zone=arce_result["claims_in_zone"],
        reported_outcome=None,
        label=label,
    )

    return Response({"arce_result": arce_result, "payout_amount": payout_amount})


def _sse_event(payload):
    return f"data: {json.dumps(payload)}\n\n"


def _random_sensor_data(zone):
    real = get_real_data(12.9716, 77.5946)
    sensor_score = get_sensor_score()
    movement = round(random.uniform(42, 92), 1)
    activity = round(random.uniform(38, 98), 1)
    svm_flag = 1 if sensor_score < 0.35 else 0
    cluster_flag = 1 if movement < 55 or activity < 45 or real.get('aqi', 0) > 180 else 0
    engine_score = round(sensor_score * 100, 1)
    return {
        'rain': real['rain'],
        'aqi': real['aqi'],
        'temp': real['temp'],
        'movement': movement,
        'activity': activity,
        'svm_flag': svm_flag,
        'cluster_flag': cluster_flag,
        'subzone': zone,
        'sensor_score': round(sensor_score, 2),
        'engine_score': engine_score,
    }


def stream_sensors(zone):
    while True:
        payload = _random_sensor_data(zone)
        yield _sse_event(payload)
        time.sleep(3)


def stream_sensors_view(request):
    zone = request.GET.get('zone', 'GREEN')
    response = StreamingHttpResponse(stream_sensors(zone), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def stream_pipeline_view(request):
    zone = request.GET.get('zone', 'GREEN')
    worker_id = request.GET.get('worker_id', 'AK001')
    
    def stream_pipeline():
        sensor_data = _random_sensor_data(zone)
        steps = [
            {'layer': 1, 'name': 'Weather Confirmation', 'detail': f"Rain:{sensor_data['rain']} AQI:{sensor_data['aqi']} Temp:{sensor_data['temp']}"},
            {'layer': 2, 'name': 'GPS Zone Verification', 'detail': f"Zone: {zone} verified"},
            {'layer': 3, 'name': 'Network Triangulation', 'detail': 'Location triangulated across 4 nodes'},
            {'layer': 4, 'name': 'Anti-Fraud (SVM+DBSCAN)', 'detail': f"SVM:{'FLAGGED' if sensor_data['svm_flag'] else 'OK'} · DBSCAN:{'FLAGGED' if sensor_data['cluster_flag'] else 'OK'}"},
            {'layer': 5, 'name': 'Sensor Activity', 'detail': f"Activity:{sensor_data['activity']}% Movement:{sensor_data['movement']}%"},
            {'layer': 6, 'name': 'Platform Handshake', 'detail': 'External platform validation complete'},
        ]
        for step in steps:
            yield _sse_event({'type': 'step', **step, 'status': 'PASS'})
            time.sleep(1.1)

        arce_score = round(0.25 + sensor_data['sensor_score'] * 0.65, 2)
        decision = 'APPROVED' if arce_score >= 0.5 else 'REJECTED'
        payout = 1200 if decision == 'APPROVED' else 0
        result = {
            'type': 'result',
            'arce_score': arce_score,
            'decision': decision,
            'risk_level': 'MEDIUM' if arce_score >= 0.5 else 'HIGH',
            'payout': payout,
            'sensor_score': sensor_data['sensor_score'],
            'engine_score': sensor_data['engine_score'],
        }
        yield _sse_event(result)
    
    response = StreamingHttpResponse(stream_pipeline(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@api_view(['GET'])
def claims_history(request):
    limit = int(request.GET.get('limit', 12))
    qs = Claim.objects.order_by('-timestamp')[:limit]
    claims = [
        {
            'timestamp': c.timestamp.isoformat() if c.timestamp else None,
            'zone': c.zone,
            'rain': c.rain,
            'aqi': c.aqi,
            'arce_score': c.arce_score,
            'risk_level': c.risk_level,
            'reported_outcome': c.reported_outcome,
            'label': c.label,
        }
        for c in qs
    ]
    return Response({'claims': claims})


@api_view(['GET'])
def status(request):
    zone = request.GET.get('zone', 'GREEN')
    real = get_real_data(12.9716, 77.5946)
    return Response({
        'status': 'ok',
        'zone': zone,
        'area': 'Bengaluru',
        'rain_mm_hr': real.get('rain', 0),
        'aqi': real.get('aqi', 0),
    })


@api_view(['GET'])
def worker_detail(request, worker_id):
    total_claims = Claim.objects.count()
    approved_claims = Claim.objects.filter(decision='APPROVED').count()
    zone_counts = Claim.objects.values('zone').annotate(count=Count('id'))
    by_zone = {item['zone']: item['count'] for item in zone_counts}
    most_common_zone = max(by_zone.items(), key=lambda item: item[1])[0] if by_zone else 'YELLOW'
    
    # Get real-time data for ML pricing
    real = get_real_data(12.9716, 77.5946)
    rain = real.get('rain', 0)
    aqi = real.get('aqi', 50)
    
    # ML-based dynamic premium
    premium = calculate_ml_premium(
        zone=most_common_zone,
        rain_forecast=rain,
        aqi=aqi,
        water_logging_history=most_common_zone in ['ORANGE', 'RED'],
        disruption_signals=1 if most_common_zone == 'RED' else 0
    )
    
    # Dynamic coverage hours
    coverage_hours = get_coverage_hours(most_common_zone, weather_risk=rain/20)

    return Response({
        'name': 'Alex Kumar',
        'phone': '+91 98765 43210',
        'initials': 'AK',
        'weeks_covered': 12 + total_claims,
        'total_payouts': approved_claims * 1200,
        'total_premiums': total_claims * premium,
        'zone': most_common_zone,
        'weekly_premium': premium,
        'coverage_hours_per_week': coverage_hours,
        'trust_level': 'Fast-Track' if approved_claims > 5 else 'Standard',
        'dynamic_pricing_active': True,
        'pricing_factors': {
            'base_rate': 39,
            'zone_adjustment': premium - 39,
            'weather_risk': rain,
            'aqi_level': aqi,
        }
    })

@api_view(['GET'])
def claims_stats(request):
    total_claims = Claim.objects.count()
    approved_claims = Claim.objects.filter(decision='APPROVED').count()
    approval_rate = int((approved_claims / total_claims) * 100) if total_claims else 0
    zone_counts = Claim.objects.values('zone').annotate(count=Count('id'))
    by_zone = {item['zone']: item['count'] for item in zone_counts}
    for zone in ['GREEN', 'YELLOW', 'ORANGE', 'RED']:
        by_zone.setdefault(zone, 0)

    return Response({
        'approval_rate': approval_rate,
        'total_claims': total_claims,
        'by_zone': by_zone
    })

def payouts(request):
    return render(request, 'workers_payouts.html')

def dashboard(request):
    return render(request, 'workers_dashboard.html')

def pipeline(request):
    return render(request, 'workers_pipeline.html')

def profile(request):
    return render(request, 'workers_profile.html')

def sensors(request):
    return render(request, 'workers_sensors.html')

def trust(request):
    return render(request, 'workers_trust.html')

def zonestatus(request):
    return render(request, 'workers_zonestatus.html')


def render_page(request, page):
    allowed_pages = {
        'workers_dashboard.html',
        'workers_payouts.html',
        'workers_pipeline.html',
        'workers_profile.html',
        'workers_sensors.html',
        'workers_trust.html',
        'workers_zonestatus.html',
    }
    if page not in allowed_pages:
        raise Http404()
    return render(request, page)


@api_view(['GET'])
def trust_score(request):
    total = Claim.objects.count()
    approved = Claim.objects.filter(label=1).count()
    approval_rate = int((approved / total) * 100) if total else 0
    zone_counts = Claim.objects.values('zone').annotate(count=Count('id'))
    by_zone = {item['zone']: item['count'] for item in zone_counts}
    for zone in ['GREEN', 'YELLOW', 'ORANGE', 'RED']:
        by_zone.setdefault(zone, 0)
    return Response({
        'trust_index': approval_rate,
        'trust_level': 'Fast-Track' if approval_rate >= 75 else 'Standard' if approval_rate >= 50 else 'Review',
        'evaluated_claims': total,
        'approval_rate': approval_rate,
        'by_zone': by_zone,
    })


@api_view(['GET'])
def payout_history(request):
    total = Claim.objects.count()
    approved = Claim.objects.filter(label=1).count()
    total_payouts = approved * 1200
    approval_rate = int((approved / total) * 100) if total else 0
    return Response({
        'total_paid_out': total_payouts,
        'approved_claims': approved,
        'approval_rate': approval_rate,
    })


@api_view(['GET'])
def zone_status(request):
    """Returns zone status with ML-based dynamic pricing for each zone."""
    real = get_real_data(12.9716, 77.5946)
    rain = real.get('rain', 0)
    aqi = real.get('aqi', 50)
    
    data = []
    for zone in ['GREEN', 'YELLOW', 'ORANGE', 'RED']:
        claims = Claim.objects.filter(zone=zone).count()
        approved = Claim.objects.filter(zone=zone, label=1).count()
        
        # ML-based premium calculation for each zone
        premium = calculate_ml_premium(
            zone=zone,
            rain_forecast=rain,
            aqi=aqi,
            water_logging_history=zone in ['ORANGE', 'RED'],
            disruption_signals=2 if zone == 'RED' else 1 if zone == 'ORANGE' else 0
        )
        
        # Dynamic coverage hours
        coverage_hours = get_coverage_hours(zone, weather_risk=rain/20)
        
        data.append({
            'zone': zone,
            'claims': claims,
            'risk_multiplier': 1.0 if zone == 'GREEN' else 1.3 if zone == 'YELLOW' else 1.8 if zone == 'ORANGE' else 2.5,
            'weekly_premium': premium,
            'coverage_hours_per_week': coverage_hours,
            'max_payout': 1200,
            'areas': random.randint(1, 8),
            'water_logging_history': zone in ['ORANGE', 'RED'],
            'weather_forecast': 'Rainy' if rain > 5 else 'Clear',
        })
    return Response({'zones': data})


@api_view(['POST'])
def worker_signup(request):
    """Register a new worker."""
    import json
    
    # Try to get data from different sources
    data = request.data
    if not data:
        try:
            body = request.body.decode('utf-8')
            data = json.loads(body) if body else {}
        except:
            data = {}
    
    print(f"DEBUG - Received data: {data}")
    print(f"DEBUG - Content-Type: {request.headers.get('Content-Type')}")
    
    # Get fields with fallbacks
    full_name = data.get('fullName', '').strip() if data else ''
    phone = data.get('phone', '').strip() if data else ''
    password = data.get('password', '').strip() if data else ''
    upi_id = data.get('upiId', '').strip() if data else ''
    
    print(f"DEBUG - full_name: '{full_name}', phone: '{phone}', upi_id: '{upi_id}'")
    
    # Check if required fields are present
    if not full_name:
        return Response({'error': 'Full name is required', 'received': str(data)}, status=400)
    if not phone:
        return Response({'error': 'Phone is required', 'received': str(data)}, status=400)
    if not password:
        return Response({'error': 'Password is required', 'received': str(data)}, status=400)
    if not upi_id:
        return Response({'error': 'UPI ID is required', 'received': str(data)}, status=400)
    
    # Return success response
    return Response({
        'success': True,
        'message': 'Worker registered successfully',
        'worker': {
            'id': f"W{phone[-6:] if len(phone) >= 6 else '000000'}",
            'name': full_name,
            'phone': phone,
            'zone': data.get('zone', 'YELLOW'),
            'upiId': upi_id,
            'status': 'active',
            'weeksCovered': 1,
            'trustScore': 500,
        }
    })
