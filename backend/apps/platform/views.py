from decimal import Decimal

from django.db.models import Count, F, Sum
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.models import AIRequest, AskQuery
from apps.auditlog.models import PageView
from apps.auditlog.services import platform_activity, serialize_activity, write_audit
from apps.billing.entitlements import (
    apply_plan_to_tenant,
    create_invoice,
    ensure_billing_catalog,
    issue_invoice,
    mark_invoice_paid,
    set_tenant_module,
    update_draft_invoice,
    void_invoice,
)
from apps.billing.models import Invoice, ModuleFeature, PaymentGateway, Plan, ProductModule, Subscription
from apps.billing.serializers import (
    InvoiceCreateSerializer,
    InvoiceSerializer,
    InvoiceUpdateSerializer,
    ModuleFeatureSerializer,
    PaymentGatewaySerializer,
    PlanSerializer,
    PlatformTenantCreateSerializer,
    PlatformTenantSerializer,
    ProductModuleSerializer,
    SubscriptionAssignSerializer,
    SubscriptionCreateSerializer,
    SubscriptionSerializer,
    TenantModuleAssignSerializer,
)
from apps.common.exceptions import APIError
from apps.platform.admins import (
    force_platform_admin_password_reset,
    invite_platform_admin,
    platform_admins,
    remove_platform_admin,
    set_platform_admin_active,
)
from apps.platform.branding import ASSET_SLOTS, clear_asset, replace_asset, validate_brand_asset
from apps.platform.lead_sources import ensure_lead_sources, test_lead_source
from apps.platform.models import LeadSource, PlatformAppearance, PlatformLanding
from apps.platform.permissions import IsPlatformAdmin
from apps.platform.serializers import (
    LeadSourceSerializer,
    PlatformAdminInviteSerializer,
    PlatformAdminSerializer,
    PlatformAdminUpdateSerializer,
    PlatformAppearanceSerializer,
    PlatformLandingSerializer,
)
from apps.tenants.models import Tenant
from apps.tenants.services import create_tenant_for_owner
from apps.users.models import User


def _conflict(request, message: str) -> Response:
    return Response(
        {
            "error": {
                "code": "CONFLICT",
                "message": message,
                "details": {},
                "request_id": getattr(request, "request_id", ""),
            }
        },
        status=status.HTTP_409_CONFLICT,
    )


class PlatformAdminListView(generics.ListAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PlatformAdminSerializer

    def get_queryset(self):
        return platform_admins()

    def post(self, request, *args, **kwargs):
        serializer = PlatformAdminInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        admin = invite_platform_admin(**serializer.validated_data)
        write_audit(action="PLATFORM_ADMIN_INVITED", request=request, resource_type="user", resource_id=admin.id)
        return Response(PlatformAdminSerializer(admin).data, status=status.HTTP_201_CREATED)


class PlatformAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PlatformAdminSerializer
    queryset = platform_admins()
    lookup_field = "id"

    def patch(self, request, *args, **kwargs):
        admin = self.get_object()
        serializer = PlatformAdminUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        admin = set_platform_admin_active(admin=admin, actor=request.user, is_active=serializer.validated_data["is_active"])
        action = "PLATFORM_ADMIN_REACTIVATED" if admin.is_active else "PLATFORM_ADMIN_SUSPENDED"
        write_audit(action=action, request=request, resource_type="user", resource_id=admin.id)
        return Response(PlatformAdminSerializer(admin).data)

    def delete(self, request, *args, **kwargs):
        admin = self.get_object()
        remove_platform_admin(admin=admin, actor=request.user)
        write_audit(action="PLATFORM_ADMIN_REMOVED", request=request, resource_type="user", resource_id=admin.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformAdminResetPasswordView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, id):
        admin = get_object_or_404(platform_admins(), id=id)
        force_platform_admin_password_reset(admin)
        write_audit(action="PLATFORM_ADMIN_PASSWORD_RESET_FORCED", request=request, resource_type="user", resource_id=admin.id)
        return Response({"ok": True})


class PlatformOverviewView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        ensure_billing_catalog()
        ensure_lead_sources()
        tenants = Tenant.objects.all()
        invoices = Invoice.objects.all()
        ai_period = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ai_completed = AIRequest.objects.filter(created_at__gte=ai_period, status="completed")
        return Response(
            {
                "tenants": {
                    "total": tenants.count(),
                    "active": tenants.filter(status=Tenant.Status.ACTIVE).count(),
                    "suspended": tenants.filter(status=Tenant.Status.SUSPENDED).count(),
                    "pending": tenants.filter(status=Tenant.Status.PENDING).count(),
                },
                "users": User.objects.filter(is_active=True).count(),
                "subscriptions": {
                    "trialing": Subscription.objects.filter(status=Subscription.Status.TRIALING).count(),
                    "active": Subscription.objects.filter(status=Subscription.Status.ACTIVE).count(),
                    "past_due": Subscription.objects.filter(status=Subscription.Status.PAST_DUE).count(),
                    "canceled": Subscription.objects.filter(status=Subscription.Status.CANCELED).count(),
                },
                "invoices": {
                    "issued": invoices.filter(status=Invoice.Status.ISSUED).count(),
                    "paid": invoices.filter(status=Invoice.Status.PAID).count(),
                    "overdue": invoices.filter(status=Invoice.Status.OVERDUE).count(),
                    "outstanding": str(
                        invoices.filter(status__in=[Invoice.Status.ISSUED, Invoice.Status.OVERDUE]).aggregate(total=Sum("total"))["total"]
                        or Decimal("0.00")
                    ),
                    "collected": str(invoices.filter(status=Invoice.Status.PAID).aggregate(total=Sum("total"))["total"] or Decimal("0.00")),
                },
                "packages": Plan.objects.filter(is_active=True).count(),
                "gateways": PaymentGateway.objects.filter(is_enabled=True).count(),
                "lead_sources": LeadSource.objects.filter(is_enabled=True).count(),
                "modules": ProductModule.objects.filter(is_active=True).count(),
                "ai": {
                    "requests": ai_completed.count(),
                    "tokens": int(ai_completed.aggregate(total=Sum(F("prompt_tokens") + F("completion_tokens"))).get("total") or 0),
                },
                "telemetry": {
                    "prompts": AIRequest.objects.count(),
                    "asks": AskQuery.objects.count(),
                    "page_views": PageView.objects.count(),
                },
                "recent_tenants": [
                    {"id": str(item.id), "name": item.name, "status": item.status, "created_at": item.created_at}
                    for item in tenants.order_by("-created_at")[:6]
                ],
                "activity": [serialize_activity(item) for item in platform_activity(limit=8)],
            }
        )


class PlatformTenantListView(generics.ListCreateAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PlatformTenantSerializer
    search_fields = ("name", "slug")
    filterset_fields = ("status",)
    ordering_fields = ("created_at", "name")

    def get_queryset(self):
        return Tenant.objects.annotate(member_count=Count("memberships", distinct=True)).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        payload = PlatformTenantCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        email = data["owner_email"].lower()
        user = User.objects.filter(email=email).first()
        if user is None:
            password = data.get("owner_password")
            if not password:
                raise APIError("A password is required when creating a new owner account.", code="VALIDATION_ERROR")
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=data.get("owner_first_name", ""),
                last_name=data.get("owner_last_name", ""),
            )
        tenant = create_tenant_for_owner(name=data["name"], owner=user)
        if data.get("plan_id"):
            plan = get_object_or_404(Plan, id=data["plan_id"])
            apply_plan_to_tenant(tenant, plan)
        write_audit(action="PLATFORM_TENANT_CREATED", request=request, tenant=tenant, resource_type="tenant", resource_id=tenant.id)
        tenant = Tenant.objects.annotate(member_count=Count("memberships", distinct=True)).get(id=tenant.id)
        return Response(PlatformTenantSerializer(tenant).data, status=status.HTTP_201_CREATED)


class PlatformTenantDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PlatformTenantSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Tenant.objects.annotate(member_count=Count("memberships", distinct=True))

    def perform_update(self, serializer):
        tenant = serializer.save()
        write_audit(action="PLATFORM_TENANT_UPDATED", request=self.request, tenant=tenant, resource_type="tenant", resource_id=tenant.id)

    def perform_destroy(self, instance):
        write_audit(action="PLATFORM_TENANT_DELETED", request=self.request, tenant=instance, resource_type="tenant", resource_id=instance.id)
        instance.delete()


class PlatformTenantModuleView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, id):
        tenant = get_object_or_404(Tenant, id=id)
        serializer = TenantModuleAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        module = get_object_or_404(ProductModule, code=serializer.validated_data["module_code"])
        assignment = set_tenant_module(tenant, module, enabled=serializer.validated_data["is_enabled"])
        write_audit(action="PLATFORM_MODULE_ASSIGNED", request=request, tenant=tenant, resource_type="tenant_module", resource_id=assignment.id)
        tenant = Tenant.objects.annotate(member_count=Count("memberships", distinct=True)).get(id=tenant.id)
        return Response(PlatformTenantSerializer(tenant).data)


class PlatformTenantPlanView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, id):
        tenant = get_object_or_404(Tenant, id=id)
        serializer = SubscriptionAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan_id = serializer.validated_data.get("plan_id")
        if not plan_id:
            raise APIError("plan_id is required.", code="VALIDATION_ERROR")
        plan = get_object_or_404(Plan, id=plan_id)
        subscription = apply_plan_to_tenant(tenant, plan, status=serializer.validated_data.get("status"))
        write_audit(action="PLATFORM_PLAN_ASSIGNED", request=request, tenant=tenant, resource_type="subscription", resource_id=subscription.id)
        return Response(SubscriptionSerializer(subscription).data)


class PlatformModuleListView(generics.ListCreateAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = ProductModuleSerializer
    queryset = ProductModule.objects.prefetch_related("features").all()

    def perform_create(self, serializer):
        module = serializer.save()
        write_audit(action="PLATFORM_MODULE_CREATED", request=self.request, resource_type="product_module", resource_id=module.id)


class PlatformModuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = ProductModuleSerializer
    queryset = ProductModule.objects.prefetch_related("features")
    lookup_field = "id"

    def perform_update(self, serializer):
        module = serializer.save()
        write_audit(action="PLATFORM_MODULE_UPDATED", request=self.request, resource_type="product_module", resource_id=module.id)

    def destroy(self, request, *args, **kwargs):
        module = self.get_object()
        if module.plan_modules.exists() or module.tenant_assignments.exists():
            return _conflict(request, "This module is assigned to a package or tenant. Deactivate it instead of deleting.")
        write_audit(action="PLATFORM_MODULE_DELETED", request=request, resource_type="product_module", resource_id=module.id)
        return super().destroy(request, *args, **kwargs)


class PlatformModuleFeatureListView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, id):
        module = get_object_or_404(ProductModule, id=id)
        serializer = ModuleFeatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(module=module)
        write_audit(action="PLATFORM_FEATURE_CREATED", request=request, resource_type="module_feature", resource_id=serializer.instance.id)
        return Response(ProductModuleSerializer(module).data, status=status.HTTP_201_CREATED)


class PlatformFeatureDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = ModuleFeatureSerializer
    queryset = ModuleFeature.objects.select_related("module")
    lookup_field = "id"

    def perform_update(self, serializer):
        feature = serializer.save()
        write_audit(action="PLATFORM_FEATURE_UPDATED", request=self.request, resource_type="module_feature", resource_id=feature.id)

    def perform_destroy(self, instance):
        write_audit(action="PLATFORM_FEATURE_DELETED", request=self.request, resource_type="module_feature", resource_id=instance.id)
        instance.delete()


class PlatformPackageListView(generics.ListCreateAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PlanSerializer
    queryset = Plan.objects.prefetch_related("plan_modules__module").all()

    def perform_create(self, serializer):
        plan = serializer.save()
        write_audit(action="PLATFORM_PACKAGE_CREATED", request=self.request, resource_type="plan", resource_id=plan.id)


class PlatformPackageDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PlanSerializer
    queryset = Plan.objects.prefetch_related("plan_modules__module")
    lookup_field = "id"

    def perform_update(self, serializer):
        plan = serializer.save()
        write_audit(action="PLATFORM_PACKAGE_UPDATED", request=self.request, resource_type="plan", resource_id=plan.id)

    def destroy(self, request, *args, **kwargs):
        plan = self.get_object()
        if plan.subscriptions.exists():
            return _conflict(request, "This package has tenant subscriptions. Deactivate it instead of deleting.")
        write_audit(action="PLATFORM_PACKAGE_DELETED", request=request, resource_type="plan", resource_id=plan.id)
        return super().destroy(request, *args, **kwargs)


class PlatformGatewayListView(generics.ListCreateAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PaymentGatewaySerializer
    queryset = PaymentGateway.objects.all()

    def perform_create(self, serializer):
        gateway = serializer.save()
        write_audit(action="PLATFORM_GATEWAY_CREATED", request=self.request, resource_type="payment_gateway", resource_id=gateway.id)


class PlatformGatewayDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PaymentGatewaySerializer
    queryset = PaymentGateway.objects.all()
    lookup_field = "id"

    def perform_update(self, serializer):
        gateway = serializer.save()
        write_audit(action="PLATFORM_GATEWAY_UPDATED", request=self.request, resource_type="payment_gateway", resource_id=gateway.id)

    def destroy(self, request, *args, **kwargs):
        gateway = self.get_object()
        if gateway.is_default:
            return _conflict(request, "Assign another default gateway before deleting this one.")
        write_audit(action="PLATFORM_GATEWAY_DELETED", request=request, resource_type="payment_gateway", resource_id=gateway.id)
        return super().destroy(request, *args, **kwargs)


class PlatformLeadSourceListView(generics.ListAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = LeadSourceSerializer
    pagination_class = None

    def get_queryset(self):
        ensure_lead_sources()
        return LeadSource.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data, "count": queryset.count()})


class PlatformLeadSourceDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = LeadSourceSerializer
    queryset = LeadSource.objects.all()
    lookup_field = "id"

    def perform_update(self, serializer):
        source = serializer.save()
        write_audit(action="PLATFORM_LEAD_SOURCE_UPDATED", request=self.request, resource_type="lead_source", resource_id=source.id)


class PlatformLeadSourceTestView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, id):
        source = get_object_or_404(LeadSource, id=id)
        from providers.ai.base import ProviderUnavailable

        try:
            result = test_lead_source(source)
        except ProviderUnavailable as exc:
            raise APIError(str(exc), code="INTEGRATION_ERROR") from exc
        write_audit(action="PLATFORM_LEAD_SOURCE_TESTED", request=request, resource_type="lead_source", resource_id=source.id)
        return Response(result)


class PlatformInvoiceListView(generics.ListCreateAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = InvoiceSerializer
    filterset_fields = ("status", "tenant")
    search_fields = ("number", "tenant__name")

    def get_queryset(self):
        return Invoice.objects.select_related("tenant", "gateway", "subscription").prefetch_related("lines")

    def create(self, request, *args, **kwargs):
        payload = InvoiceCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        tenant = get_object_or_404(Tenant, id=payload.validated_data["tenant_id"])
        subscription = Subscription.objects.filter(tenant=tenant).select_related("plan").first()
        invoice = create_invoice(
            tenant=tenant,
            description=payload.validated_data["description"],
            amount=payload.validated_data["amount"],
            notes=payload.validated_data.get("notes", ""),
            subscription=subscription,
        )
        write_audit(action="PLATFORM_INVOICE_CREATED", request=request, tenant=tenant, resource_type="invoice", resource_id=invoice.id)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class PlatformInvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.select_related("tenant", "gateway").prefetch_related("lines")
    lookup_field = "id"

    def update(self, request, *args, **kwargs):
        invoice = self.get_object()
        payload = InvoiceUpdateSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        try:
            invoice = update_draft_invoice(
                invoice,
                description=payload.validated_data.get("description"),
                amount=payload.validated_data.get("amount"),
                notes=payload.validated_data.get("notes"),
            )
        except ValueError as exc:
            return _conflict(request, str(exc))
        write_audit(action="PLATFORM_INVOICE_UPDATED", request=request, tenant=invoice.tenant, resource_type="invoice", resource_id=invoice.id)
        return Response(InvoiceSerializer(invoice).data)

    def destroy(self, request, *args, **kwargs):
        invoice = self.get_object()
        if invoice.status not in {Invoice.Status.DRAFT, Invoice.Status.VOID}:
            return _conflict(request, "Only draft or void invoices can be deleted.")
        write_audit(action="PLATFORM_INVOICE_DELETED", request=request, tenant=invoice.tenant, resource_type="invoice", resource_id=invoice.id)
        return super().destroy(request, *args, **kwargs)


class PlatformInvoiceIssueView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, id):
        invoice = get_object_or_404(Invoice, id=id)
        invoice = issue_invoice(invoice)
        write_audit(action="PLATFORM_INVOICE_ISSUED", request=request, tenant=invoice.tenant, resource_type="invoice", resource_id=invoice.id)
        return Response(InvoiceSerializer(invoice).data)


class PlatformInvoicePayView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, id):
        invoice = get_object_or_404(Invoice, id=id)
        try:
            invoice = mark_invoice_paid(invoice)
        except ValueError as exc:
            return _conflict(request, str(exc))
        write_audit(action="PLATFORM_INVOICE_PAID", request=request, tenant=invoice.tenant, resource_type="invoice", resource_id=invoice.id)
        return Response(InvoiceSerializer(invoice).data)


class PlatformInvoiceVoidView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, id):
        invoice = get_object_or_404(Invoice, id=id)
        try:
            invoice = void_invoice(invoice)
        except ValueError as exc:
            return _conflict(request, str(exc))
        write_audit(action="PLATFORM_INVOICE_VOIDED", request=request, tenant=invoice.tenant, resource_type="invoice", resource_id=invoice.id)
        return Response(InvoiceSerializer(invoice).data)


class PlatformSubscriptionListView(generics.ListCreateAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = SubscriptionSerializer
    filterset_fields = ("status",)
    queryset = Subscription.objects.select_related("plan", "tenant", "gateway").all()

    def create(self, request, *args, **kwargs):
        payload = SubscriptionCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        tenant = get_object_or_404(Tenant, id=payload.validated_data["tenant_id"])
        plan = get_object_or_404(Plan, id=payload.validated_data["plan_id"])
        subscription = apply_plan_to_tenant(tenant, plan, status=payload.validated_data.get("status"))
        if payload.validated_data.get("seats"):
            subscription.seats = payload.validated_data["seats"]
            subscription.save(update_fields=["seats", "updated_at"])
        write_audit(action="PLATFORM_SUBSCRIPTION_CREATED", request=request, tenant=tenant, resource_type="subscription", resource_id=subscription.id)
        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)


class PlatformSubscriptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = SubscriptionSerializer
    queryset = Subscription.objects.select_related("plan", "tenant", "gateway")
    lookup_field = "id"

    def update(self, request, *args, **kwargs):
        subscription = self.get_object()
        payload = SubscriptionAssignSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        if data.get("plan_id"):
            plan = get_object_or_404(Plan, id=data["plan_id"])
            subscription = apply_plan_to_tenant(subscription.tenant, plan, status=data.get("status") or subscription.status)
        elif data.get("status"):
            subscription.status = data["status"]
            subscription.save(update_fields=["status", "updated_at"])
        if data.get("seats"):
            subscription.seats = data["seats"]
            subscription.save(update_fields=["seats", "updated_at"])
        write_audit(
            action="PLATFORM_SUBSCRIPTION_UPDATED",
            request=request,
            tenant=subscription.tenant,
            resource_type="subscription",
            resource_id=subscription.id,
        )
        return Response(SubscriptionSerializer(subscription).data)

    def perform_destroy(self, instance):
        write_audit(
            action="PLATFORM_SUBSCRIPTION_CANCELED",
            request=self.request,
            tenant=instance.tenant,
            resource_type="subscription",
            resource_id=instance.id,
        )
        instance.status = Subscription.Status.CANCELED
        instance.save(update_fields=["status", "updated_at"])


class PlatformAppearanceView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        appearance = PlatformAppearance.get_solo()
        return Response(PlatformAppearanceSerializer(appearance, context={"request": request}).data)

    def patch(self, request):
        appearance = PlatformAppearance.get_solo()
        serializer = PlatformAppearanceSerializer(appearance, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        write_audit(action="PLATFORM_APPEARANCE_UPDATED", request=request, resource_type="platform_appearance", resource_id=appearance.id)
        return Response(serializer.data)


class PlatformLandingView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        landing = PlatformLanding.get_solo()
        return Response(PlatformLandingSerializer(landing).data)

    def patch(self, request):
        landing = PlatformLanding.get_solo()
        serializer = PlatformLandingSerializer(landing, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        write_audit(action="PLATFORM_LANDING_UPDATED", request=request, resource_type="platform_landing", resource_id=landing.id)
        return Response(serializer.data)


class PlatformAppearanceAssetView(APIView):
    permission_classes = [IsPlatformAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slot: str):
        if slot not in ASSET_SLOTS:
            raise APIError("Unknown branding asset.", code="VALIDATION_ERROR")
        upload = request.FILES.get("file")
        if not upload:
            raise APIError("Choose an image file.", code="VALIDATION_ERROR")
        try:
            validate_brand_asset(upload, slot=slot)
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise APIError(message, code="VALIDATION_ERROR") from exc
        appearance = PlatformAppearance.get_solo()
        replace_asset(appearance, slot, upload)
        write_audit(
            action="PLATFORM_APPEARANCE_ASSET_UPDATED",
            request=request,
            resource_type="platform_appearance",
            resource_id=appearance.id,
            metadata={"slot": slot},
        )
        return Response(PlatformAppearanceSerializer(appearance, context={"request": request}).data)

    def delete(self, request, slot: str):
        if slot not in ASSET_SLOTS:
            raise APIError("Unknown branding asset.", code="VALIDATION_ERROR")
        appearance = PlatformAppearance.get_solo()
        clear_asset(appearance, slot)
        write_audit(
            action="PLATFORM_APPEARANCE_ASSET_CLEARED",
            request=request,
            resource_type="platform_appearance",
            resource_id=appearance.id,
            metadata={"slot": slot},
        )
        return Response(PlatformAppearanceSerializer(appearance, context={"request": request}).data)
