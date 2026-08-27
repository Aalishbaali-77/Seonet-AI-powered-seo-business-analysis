from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.rbac.services import user_permission_codes
from apps.tenants.models import Membership

from apps.tenants.members import infer_first_name, split_full_name, workspace_name_from_identity

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    company_name = serializers.CharField(max_length=255, allow_blank=True, required=False)

    def validate_email(self, value: str) -> str:
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate(self, attrs):
        name = (attrs.get("name") or "").strip()
        first_name = (attrs.get("first_name") or "").strip()
        last_name = (attrs.get("last_name") or "").strip()
        if name and not first_name:
            first_name, last_name = split_full_name(name)
        email = attrs["email"]
        first_name = infer_first_name(email=email, first_name=first_name, full_name=name)
        attrs["first_name"] = first_name
        attrs["last_name"] = last_name
        attrs["company_name"] = workspace_name_from_identity(
            company_name=attrs.get("company_name") or "",
            email=email,
            first_name=first_name,
        )
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value: str) -> str:
        return value.lower()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value


class TenantSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    status = serializers.CharField()
    is_default = serializers.BooleanField()
    roles = serializers.ListField(child=serializers.CharField())


class MeSerializer(serializers.ModelSerializer):
    tenants = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    is_platform_admin = serializers.SerializerMethodField()
    modules = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "email_verified_at",
            "mfa_enabled",
            "theme_preference",
            "tenants",
            "permissions",
            "is_platform_admin",
            "modules",
            "subscription",
        )

    def get_tenants(self, user):
        memberships = (
            Membership.objects.filter(user=user, status=Membership.Status.ACTIVE)
            .select_related("tenant")
            .prefetch_related("membership_roles__role")
        )
        payload = []
        for membership in memberships:
            payload.append(
                {
                    "id": membership.tenant_id,
                    "name": membership.tenant.name,
                    "slug": membership.tenant.slug,
                    "status": membership.tenant.status,
                    "is_default": membership.is_default,
                    "roles": list(membership.membership_roles.values_list("role__code", flat=True)),
                }
            )
        return payload

    def get_permissions(self, user):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        if tenant is None:
            tenant = self._default_tenant(user)
        return sorted(user_permission_codes(user, tenant))

    def get_is_platform_admin(self, user) -> bool:
        return bool(user.is_staff or user.is_superuser)

    def get_modules(self, user):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        if tenant is None:
            tenant = self._default_tenant(user)
        from apps.billing.entitlements import tenant_module_codes

        return sorted(tenant_module_codes(tenant))

    def get_subscription(self, user):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        if tenant is None:
            tenant = self._default_tenant(user)
        from apps.billing.entitlements import subscription_payload

        return subscription_payload(tenant)

    def _default_tenant(self, user):
        membership = (
            Membership.objects.filter(user=user, status=Membership.Status.ACTIVE)
            .select_related("tenant")
            .order_by("-is_default", "created_at")
            .first()
        )
        return membership.tenant if membership else None


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "theme_preference")
