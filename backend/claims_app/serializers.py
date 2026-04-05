from rest_framework import serializers
from .models import Claim, ArceHistory

class ClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = Claim
        fields = '__all__'

class ArceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ArceHistory
        fields = '__all__'

class ClaimRequestSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    movement = serializers.IntegerField(required=False)
    activity = serializers.IntegerField(required=False)
    location_valid = serializers.IntegerField(required=False)
    reported_outcome = serializers.CharField(required=False)