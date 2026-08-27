from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.auditlog.services import write_audit
from apps.billing.checkout import parse_stripe_invoice_id
from apps.billing.entitlements import (
    mark_invoice_paid,
    payment_method_payload,
    request_plan_subscription,
    start_invoice_payment,
    subscription_payload,
    tenant_module_codes,
)
from apps.billing.models import Invoice, Plan, Subscription
from apps.billing.serializers import InvoiceSerializer, PlanSerializer, SubscribeSerializer, SubscriptionSerializer
from apps.common.permissions import HasPermissionCode, HasTenant


class BillingView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "billing.view"
    subscription_exempt = True

    def get(self, request):
        subscription = Subscription.objects.for_tenant(request.tenant).select_related("plan", "gateway").first()
        invoices = Invoice.objects.for_tenant(request.tenant).select_related("gateway", "plan")[:50]
        plans = Plan.objects.filter(is_active=True, is_public=True)
        return Response(
            {
                "subscription": SubscriptionSerializer(subscription).data if subscription else None,
                "access": subscription_payload(request.tenant),
                "payment": payment_method_payload(),
                "plans": PlanSerializer(plans, many=True).data,
                "invoices": InvoiceSerializer(invoices, many=True).data,
                "modules": sorted(tenant_module_codes(request.tenant)),
            }
        )


class BillingSubscribeView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "billing.manage"
    subscription_exempt = True

    def post(self, request):
        payload = SubscribeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        plan = get_object_or_404(Plan, id=payload.validated_data["plan_id"])
        invoice = request_plan_subscription(request.tenant, plan)
        write_audit(
            action="BILLING_PLAN_REQUESTED",
            request=request,
            tenant=request.tenant,
            resource_type="invoice",
            resource_id=invoice.id,
        )
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class BillingInvoicePayView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "billing.manage"
    subscription_exempt = True

    def post(self, request, id):
        invoice = get_object_or_404(Invoice.objects.for_tenant(request.tenant), id=id)
        result = start_invoice_payment(invoice)
        write_audit(
            action="BILLING_PAYMENT_STARTED",
            request=request,
            tenant=request.tenant,
            resource_type="invoice",
            resource_id=invoice.id,
        )
        return Response({**result, "invoice": InvoiceSerializer(invoice).data})


class BillingGatewayWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    subscription_exempt = True

    def post(self, request):
        event = request.data if isinstance(request.data, dict) else {}
        kind = str(event.get("type") or "")
        invoice_id = parse_stripe_invoice_id(event)
        if kind not in {"checkout.session.completed", "payment_intent.succeeded"} or not invoice_id:
            return Response({"ok": True, "applied": False})
        invoice = Invoice.objects.filter(id=invoice_id).first()
        if invoice is None or invoice.status == Invoice.Status.PAID:
            return Response({"ok": True, "applied": False})
        mark_invoice_paid(invoice)
        write_audit(
            action="BILLING_INVOICE_PAID",
            request=request,
            tenant=invoice.tenant,
            resource_type="invoice",
            resource_id=invoice.id,
            metadata={"source": "gateway_webhook"},
        )
        return Response({"ok": True, "applied": True, "invoice_id": str(invoice.id)})
