from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.platform.branding import ASSET_SLOTS
from apps.platform.landing import ITEM_SPECS, validate_item_list
from apps.platform.models import LeadSource, PlatformAppearance, PlatformLanding

User = get_user_model()


class PlatformAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "is_active", "is_superuser", "last_login", "date_joined")
        read_only_fields = fields


class PlatformAdminInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")


class PlatformAdminUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()

IDENTITY_FIELDS = (
    "product_name",
    "legal_name",
    "tagline",
    "description",
    "support_email",
    "support_url",
    "login_footer",
    "copyright_text",
    "default_theme",
    "primary_color",
    "secondary_color",
    "updated_at",
)


class PlatformAppearanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAppearance
        fields = IDENTITY_FIELDS
        read_only_fields = ("updated_at",)

    def _file_url(self, file_field) -> str | None:
        if not file_field:
            return None
        request = self.context.get("request")
        url = file_field.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def to_representation(self, instance: PlatformAppearance) -> dict:
        payload = super().to_representation(instance)
        for slot in ASSET_SLOTS:
            payload[f"{slot}_url"] = self._file_url(getattr(instance, slot))
        return payload


LANDING_FIELDS = (
    "nav",
    "hero_eyebrow",
    "hero_title",
    "hero_body",
    "hero_primary_cta",
    "hero_secondary_cta",
    "hero_secondary_href",
    "stats",
    "pains_eyebrow",
    "pains_title",
    "pains_body",
    "pains",
    "product_eyebrow",
    "product_title",
    "product_body",
    "steps_eyebrow",
    "steps_title",
    "steps_body",
    "steps",
    "workspace_eyebrow",
    "workspace_title",
    "workspace_body",
    "control_plane_eyebrow",
    "control_plane_title",
    "control_plane_body",
    "pricing_eyebrow",
    "pricing_title",
    "pricing_body",
    "security_eyebrow",
    "security_title",
    "security_body",
    "security",
    "faq_eyebrow",
    "faq_title",
    "faqs",
    "cta_title",
    "cta_body",
    "cta_primary",
    "cta_secondary",
    "updated_at",
)


class PlatformLandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformLanding
        fields = LANDING_FIELDS
        read_only_fields = ("updated_at",)

    def validate_nav(self, value):
        return validate_item_list(value, keys=ITEM_SPECS["nav"], label="Navigation")

    def validate_stats(self, value):
        return validate_item_list(value, keys=ITEM_SPECS["stats"], label="Stats")

    def validate_pains(self, value):
        return validate_item_list(value, keys=ITEM_SPECS["pains"], label="Pains")

    def validate_steps(self, value):
        return validate_item_list(value, keys=ITEM_SPECS["steps"], label="Steps")

    def validate_security(self, value):
        return validate_item_list(value, keys=ITEM_SPECS["security"], label="Security")

    def validate_faqs(self, value):
        return validate_item_list(value, keys=ITEM_SPECS["faqs"], label="FAQs")


class LeadSourceSerializer(serializers.ModelSerializer):
    credentials_configured = serializers.BooleanField(read_only=True)
    requires_key = serializers.BooleanField(read_only=True)
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    model = serializers.CharField(required=False, allow_blank=True)
    homepage_url = serializers.CharField(required=False, allow_blank=True)
    search_url = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = LeadSource
        fields = (
            "id",
            "code",
            "provider",
            "category",
            "display_name",
            "purpose",
            "is_enabled",
            "setup_hint",
            "sort_order",
            "credentials_configured",
            "requires_key",
            "api_key",
            "model",
            "homepage_url",
            "search_url",
            "updated_at",
        )
        read_only_fields = ("id", "code", "provider", "category", "updated_at")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        public = instance.public_config or {}
        data["model"] = instance.model
        data["requires_key"] = instance.requires_key
        data["homepage_url"] = public.get("homepage_url") or public.get("docs_url") or ""
        data["search_url"] = public.get("search_url") or ""
        return data

    def update(self, instance, validated_data):
        api_key = validated_data.pop("api_key", None)
        model = validated_data.pop("model", None)
        homepage_url = validated_data.pop("homepage_url", None)
        search_url = validated_data.pop("search_url", None)
        if api_key:
            encrypted = dict(instance.encrypted_config or {})
            encrypted["api_key"] = api_key
            instance.encrypted_config = encrypted
        public = dict(instance.public_config or {})
        if model is not None:
            public["model"] = model.strip()
        if homepage_url is not None:
            public["homepage_url"] = homepage_url.strip()
        if search_url is not None:
            public["search_url"] = search_url.strip()
        instance.public_config = public
        enabling = validated_data.get("is_enabled")
        if enabling and instance.requires_key and not instance.credentials_configured and not api_key:
            from apps.common.exceptions import APIError

            raise APIError("Store an API key before enabling this source.", code="VALIDATION_ERROR")
        return super().update(instance, validated_data)
