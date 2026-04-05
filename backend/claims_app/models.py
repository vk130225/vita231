from django.db import models

class Claim(models.Model):
    lat = models.FloatField()
    lon = models.FloatField()
    movement = models.IntegerField()
    activity = models.IntegerField()
    location_valid = models.IntegerField()
    rain = models.FloatField()
    temp = models.FloatField()
    aqi = models.FloatField()
    zone = models.CharField(max_length=10)
    social_signal = models.JSONField()
    svm_anomaly = models.IntegerField()
    cluster_flag = models.IntegerField()
    decision = models.CharField(max_length=10)
    arce_score = models.FloatField()
    risk_level = models.CharField(max_length=10)
    claims_in_zone = models.IntegerField()
    reported_outcome = models.CharField(max_length=20, null=True, blank=True)
    label = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

class ArceHistory(models.Model):
    zone = models.CharField(max_length=10)
    arce_score = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
