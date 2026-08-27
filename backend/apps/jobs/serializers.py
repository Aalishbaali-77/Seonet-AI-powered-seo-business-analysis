from rest_framework import serializers

from apps.jobs.models import Job


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = (
            "id",
            "job_type",
            "status",
            "progress",
            "payload",
            "result",
            "error",
            "retry_count",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        )
