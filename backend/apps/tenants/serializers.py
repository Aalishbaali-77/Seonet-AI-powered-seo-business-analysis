from rest_framework import serializers

from apps.tenants.models import Membership, Tenant
from apps.tenants.workspace import WORKSPACE_DEFAULTS, merge_workspace_settings, workspace_profile


class TenantSerializer(serializers.ModelSerializer):
    timezone = serializers.CharField(required=False, allow_blank=True, write_only=True)
    locale = serializers.CharField(required=False, allow_blank=True, write_only=True)
    currency = serializers.CharField(required=False, allow_blank=True, write_only=True)
    company_legal_name = serializers.CharField(required=False, allow_blank=True, write_only=True)
    company_website = serializers.CharField(required=False, allow_blank=True, write_only=True)
    industry = serializers.CharField(required=False, allow_blank=True, write_only=True)
    support_email = serializers.EmailField(required=False, allow_blank=True, write_only=True)
    reply_to_email = serializers.EmailField(required=False, allow_blank=True, write_only=True)
    notification_digest = serializers.CharField(required=False, allow_blank=True, write_only=True)
    primary_crm = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Tenant
        fields = (
            "id",
            "name",
            "slug",
            "status",
            "timezone",
            "locale",
            "currency",
            "company_legal_name",
            "company_website",
            "industry",
            "support_email",
            "reply_to_email",
            "notification_digest",
            "primary_crm",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "status", "created_at", "updated_at")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.update(workspace_profile(instance))
        return data

    def update(self, instance, validated_data):
        name = validated_data.pop("name", None)
        profile_payload = {key: validated_data.pop(key) for key in list(validated_data) if key in WORKSPACE_DEFAULTS}
        if name is not None:
            instance.name = name
        if profile_payload:
            instance.settings = merge_workspace_settings(instance, profile_payload)
        instance.save()
        return instance


class MembershipSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ("id", "email", "first_name", "last_name", "status", "is_default", "roles", "created_at")

    def get_roles(self, obj) -> list[str]:
        return list(obj.membership_roles.values_list("role__code", flat=True))


class MemberCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    role_code = serializers.CharField(max_length=64, required=False, default="viewer")
    password = serializers.CharField(write_only=True, min_length=8, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        return value.lower()


class MemberUpdateSerializer(serializers.Serializer):
    role_code = serializers.CharField(max_length=64, required=False)
    status = serializers.ChoiceField(choices=Membership.Status.choices, required=False)
