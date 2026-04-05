from django.urls import path
from . import views

urlpatterns = [
    path('health', views.health, name='health'),
    path('', views.home, name='home'),
    path('signup', views.worker_signup, name='worker_signup'),
    path('weather', views.weather, name='weather'),
    path('aqi', views.aqi, name='aqi'),
    path('risk', views.risk, name='risk'),
    path('arce/evaluate', views.arce_evaluate, name='arce_evaluate'),
    path('claim', views.process_claim, name='process_claim'),
    path('status', views.status, name='status'),
    path('worker/<str:worker_id>', views.worker_detail, name='worker_detail'),
    path('claims/stats', views.claims_stats, name='claims_stats'),
    path('claims/history', views.claims_history, name='claims_history'),
    path('stream/sensors', views.stream_sensors_view, name='stream_sensors'),
    path('stream/pipeline', views.stream_pipeline_view, name='stream_pipeline'),
    path('trust', views.trust_score, name='api_trust'),
    path('payouts', views.payout_history, name='api_payouts'),
    path('zone/status', views.zone_status, name='api_zone_status'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('payouts_page', views.payouts, name='payouts'),
    path('pipeline', views.pipeline, name='pipeline'),
    path('profile', views.profile, name='profile'),
    path('sensors', views.sensors, name='sensors'),
    path('zonestatus', views.zonestatus, name='zonestatus'),
]