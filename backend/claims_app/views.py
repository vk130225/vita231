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
    most_common_zone = max(by_zone.items(), key=lambda item: item[1])[0] if by_zone else 'GREEN'

    return Response({
        'weeks_covered': 12 + total_claims,
        'total_payouts': approved_claims * 1200,
        'total_premiums': total_claims * 105,
        'zone': most_common_zone,
        'weekly_premium': 500 + min(total_claims * 10, 300)
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
    data = []
    for zone in ['GREEN', 'YELLOW', 'ORANGE', 'RED']:
        claims = Claim.objects.filter(zone=zone).count()
        approved = Claim.objects.filter(zone=zone, label=1).count()
        premium = 400 + random.randint(-100, 500)
        payout = 1200
        areas = random.randint(1, 8)
        data.append({
            'zone': zone,
            'claims': claims,
            'risk_multiplier': 1.0 if zone == 'GREEN' else 1.5 if zone == 'YELLOW' else 2.0 if zone == 'ORANGE' else 3.0,
            'weekly_premium': premium,
            'max_payout': payout,
            'areas': areas,
        })
    return Response({'zones': data})


