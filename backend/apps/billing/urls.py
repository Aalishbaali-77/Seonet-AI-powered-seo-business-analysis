from django.urls import path

from apps.billing.views import BillingGatewayWebhookView, BillingInvoicePayView, BillingSubscribeView, BillingView

urlpatterns = [
    path("", BillingView.as_view(), name="billing"),
    path("subscribe/", BillingSubscribeView.as_view(), name="billing-subscribe"),
    path("invoices/<uuid:id>/pay/", BillingInvoicePayView.as_view(), name="billing-invoice-pay"),
    path("webhooks/stripe/", BillingGatewayWebhookView.as_view(), name="billing-stripe-webhook"),
]
