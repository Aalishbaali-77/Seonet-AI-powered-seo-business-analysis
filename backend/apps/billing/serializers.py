from rest_framework import serializers

from apps.billing.models import (
    Invoice,
    InvoiceLine,
    ModuleFeature,
    PaymentGateway,
    Plan,
    ProductModule,
    Subscription,
    TenantModule,
)
from apps.tenants.models import Tenant


class ModuleFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleFeature
        fields = ("id", "code", "name", "description", "is_active")


class ProductModuleSerializer(serializers.ModelSerializer):
    features = ModuleFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = ProductModule
        fields = ("id", "code", "name", "description", "category", "is_active", "sort_order", "features")
        read_only_fields = ("id",)


class PlanSerializer(serializers.ModelSerializer):
    modules = serializers.SerializerMethodField()
    module_codes = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta:
        model = Plan
        fields = (
            "id",
            "code",
            "name",
            "description",
            "price_amount",
            "currency",
            "interval",
            "trial_days",
            "max_pages",
            "max_audits_per_month",
            "ai_credits",
            "max_users",
            "is_active",
            "is_public",
            "is_featured",
            "cta_label",
            "cta_href",
            "sort_order",
            "modules",
            "module_codes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_modules(self, plan: Plan) -> list[dict]:
        return [
            {"id": str(item.module_id), "code": item.module.code, "name": item.module.name, "is_included": item.is_included}
            for item in plan.plan_modules.select_related("module").all()
        ]

    def create(self, validated_data):
        module_codes = validated_data.pop("module_codes", [])
        plan = super().create(validated_data)
        from apps.billing.entitlements import set_plan_modules

        if module_codes:
            set_plan_modules(plan, module_codes)
        return plan

    def update(self, instance, validated_data):
        module_codes = validated_data.pop("module_codes", None)
        plan = super().update(instance, validated_data)
        if module_codes is not None:
            from apps.billing.entitlements import set_plan_modules

            set_plan_modules(plan, module_codes)
        return plan


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    tenant_id = serializers.UUIDField(source="tenant.id", read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    gateway_name = serializers.CharField(source="gateway.display_name", read_only=True, default=None)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "status",
            "plan",
            "tenant_id",
            "tenant_name",
            "seats",
            "current_period_end",
            "gateway_name",
            "created_at",
        )


class TenantModuleSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="module.code", read_only=True)
    name = serializers.CharField(source="module.name", read_only=True)
    category = serializers.CharField(source="module.category", read_only=True)

    class Meta:
        model = TenantModule
        fields = ("id", "code", "name", "category", "is_enabled", "source", "limits")


class PaymentGatewaySerializer(serializers.ModelSerializer):
    credentials_configured = serializers.BooleanField(read_only=True)
    secret_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    publishable_key = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = PaymentGateway
        fields = (
            "id",
            "code",
            "provider",
            "display_name",
            "is_enabled",
            "is_default",
            "test_mode",
            "public_config",
            "credentials_configured",
            "secret_key",
            "publishable_key",
            "updated_at",
        )
        read_only_fields = ("id",)

    def update(self, instance, validated_data):
        validated_data.pop("code", None)
        validated_data.pop("provider", None)
        secret_key = validated_data.pop("secret_key", None)
        publishable_key = validated_data.pop("publishable_key", None)
        if instance.is_default is False and validated_data.get("is_default") is True:
            PaymentGateway.objects.exclude(pk=instance.pk).update(is_default=False)
        if publishable_key:
            public = dict(instance.public_config or {})
            public["publishable_key"] = publishable_key
            instance.public_config = public
        if secret_key:
            encrypted = dict(instance.encrypted_config or {})
            encrypted["secret_key"] = secret_key
            instance.encrypted_config = encrypted
        return super().update(instance, validated_data)

    def create(self, validated_data):
        secret_key = validated_data.pop("secret_key", None)
        publishable_key = validated_data.pop("publishable_key", None)
        if validated_data.get("is_default"):
            PaymentGateway.objects.update(is_default=False)
        if publishable_key:
            public = dict(validated_data.get("public_config") or {})
            public["publishable_key"] = publishable_key
            validated_data["public_config"] = public
        if secret_key:
            validated_data["encrypted_config"] = {"secret_key": secret_key}
        return super().create(validated_data)


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = ("id", "description", "quantity", "unit_amount", "amount")


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)
    tenant_id = serializers.UUIDField(source="tenant.id", read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    gateway_name = serializers.CharField(source="gateway.display_name", read_only=True, default=None)
    plan_id = serializers.UUIDField(read_only=True, allow_null=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True, default=None, allow_null=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "number",
            "status",
            "currency",
            "subtotal",
            "tax",
            "total",
            "due_at",
            "issued_at",
            "paid_at",
            "notes",
            "tenant_id",
            "tenant_name",
            "gateway_name",
            "plan_id",
            "plan_name",
            "lines",
            "created_at",
        )


class SubscribeSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()


class InvoiceCreateSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    description = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True)


class InvoiceUpdateSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=255, required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class TenantModuleAssignSerializer(serializers.Serializer):
    module_code = serializers.CharField()
    is_enabled = serializers.BooleanField()


class SubscriptionAssignSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(choices=Subscription.Status.choices, required=False)
    seats = serializers.IntegerField(min_value=1, required=False)


class SubscriptionCreateSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    plan_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=Subscription.Status.choices, required=False)
    seats = serializers.IntegerField(min_value=1, required=False)


class PlatformTenantCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    owner_email = serializers.EmailField()
    owner_first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    owner_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    owner_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    plan_id = serializers.UUIDField(required=False)


class PlatformTenantSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    subscription = serializers.SerializerMethodField()
    modules = serializers.SerializerMethodField()
    ai_usage = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = (
            "id",
            "name",
            "slug",
            "status",
            "feature_flags",
            "member_count",
            "subscription",
            "modules",
            "ai_usage",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "created_at", "updated_at")

    def get_subscription(self, tenant: Tenant):
        subscription = getattr(tenant, "prefetched_subscription", None)
        if subscription is None:
            subscription = Subscription.objects.filter(tenant=tenant).select_related("plan", "gateway").first()
        return SubscriptionSerializer(subscription).data if subscription else None

    def get_modules(self, tenant: Tenant):
        assignments = TenantModule.objects.filter(tenant=tenant).select_related("module")
        return TenantModuleSerializer(assignments, many=True).data

    def get_ai_usage(self, tenant: Tenant):
        from apps.ai.credits import usage_snapshot

        snapshot = usage_snapshot(tenant)
        return {
            "credits_used": snapshot["credits_used"],
            "credits_limit": snapshot["credits_limit"],
            "credits_remaining": snapshot["credits_remaining"],
            "tokens": snapshot["tokens"],
            "requests": snapshot["requests"],
        }
