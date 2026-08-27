from rest_framework import serializers

from apps.ai.models import AIRequest, AskQuery
from apps.auditlog.models import PageView


def _actor(user) -> str:
    if user is None:
        return ""
    return ((user.first_name or "") + " " + (user.last_name or "")).strip() or user.email


class PromptLogSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = AIRequest
        fields = (
            "id",
            "tenant",
            "tenant_name",
            "user_email",
            "provider",
            "model",
            "task",
            "status",
            "prompt",
            "untrusted_input",
            "response_text",
            "prompt_tokens",
            "completion_tokens",
            "duration_ms",
            "error",
            "created_at",
        )

    def get_user_email(self, obj) -> str:
        return _actor(obj.user)


class AskQuerySerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = AskQuery
        fields = ("id", "tenant", "tenant_name", "user_email", "question", "intent", "origin", "facts", "why", "created_at")

    def get_user_email(self, obj) -> str:
        return _actor(obj.user)


class PageViewSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = PageView
        fields = ("id", "tenant", "tenant_name", "user_email", "path", "title", "referrer", "ip_address", "user_agent", "created_at")

    def get_user_email(self, obj) -> str:
        return _actor(obj.user)
