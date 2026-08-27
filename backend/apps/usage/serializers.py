from rest_framework import serializers

from apps.usage.models import UsageRecord


class UsageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageRecord
        fields = ("id", "event_type", "quantity", "metadata", "created_at")
