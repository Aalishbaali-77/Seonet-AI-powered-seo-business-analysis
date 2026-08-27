from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from apps.billing.entitlements import ensure_billing_catalog, mark_invoice_paid
from apps.billing.models import Invoice, Plan, Subscription
from apps.tenants.models import Membership
from apps.users.models import User


@pytest.mark.django_db
def test_register_starts_starter_trial(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        {"email": "founder@northwind.example", "password": "SecurePass!123", "name": "Amina Rahman"},
        format="json",
    )
    assert response.status_code == 201
    user = User.objects.get(email="founder@northwind.example")
    tenant = user.memberships.get().tenant
    subscription = Subscription.objects.get(tenant=tenant)
    assert subscription.plan.code == "starter"
    assert subscription.status == Subscription.Status.TRIALING
    assert subscription.current_period_end is not None
    assert response.data["subscription"]["access"] is True


@pytest.mark.django_db
def test_expired_subscription_blocks_dashboard_and_allows_billing(api_client, user, tenant):
    subscription = Subscription.objects.get(tenant=tenant)
    subscription.status = Subscription.Status.EXPIRED
    subscription.current_period_end = timezone.now() - timedelta(days=1)
    subscription.save()
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}

    blocked = api_client.get("/api/v1/dashboard/overview/", **headers)
    assert blocked.status_code == 402
    assert blocked.data["error"]["code"] == "SUBSCRIPTION_INACTIVE"

    billing = api_client.get("/api/v1/billing/", **headers)
    assert billing.status_code == 200
    assert billing.data["access"]["access"] is False

    me = api_client.get("/api/v1/auth/me/", **headers)
    assert me.status_code == 200
    assert me.data["subscription"]["access"] is False
    assert me.data["modules"] == []


@pytest.mark.django_db
def test_period_end_expires_trial_on_refresh(api_client, user, tenant):
    subscription = Subscription.objects.get(tenant=tenant)
    subscription.status = Subscription.Status.TRIALING
    subscription.current_period_end = timezone.now() - timedelta(minutes=1)
    subscription.save()
    api_client.force_authenticate(user=user)
    blocked = api_client.get("/api/v1/dashboard/overview/", HTTP_X_TENANT_ID=str(tenant.id))
    assert blocked.status_code == 402
    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.EXPIRED


@pytest.mark.django_db
def test_tenant_can_request_plan_and_pay_invoice(api_client, user, tenant):
    ensure_billing_catalog()
    growth = Plan.objects.get(code="growth")
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}

    created = api_client.post("/api/v1/billing/subscribe/", {"plan_id": str(growth.id)}, format="json", **headers)
    assert created.status_code == 201
    assert created.data["status"] == Invoice.Status.ISSUED
    invoice_id = created.data["id"]

    pay = api_client.post(f"/api/v1/billing/invoices/{invoice_id}/pay/", **headers)
    assert pay.status_code == 200
    assert pay.data["method"] == "invoice"
    assert pay.data["paid"] is False

    invoice = Invoice.objects.get(id=invoice_id)
    mark_invoice_paid(invoice)
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID
    subscription = Subscription.objects.get(tenant=tenant)
    assert subscription.status == Subscription.Status.ACTIVE
    assert subscription.plan.code == "growth"

    restored = api_client.get("/api/v1/dashboard/overview/", **headers)
    assert restored.status_code == 200


@pytest.mark.django_db
def test_expired_tenant_can_still_manage_team(api_client, user, tenant):
    Subscription.objects.filter(tenant=tenant).update(status=Subscription.Status.EXPIRED, current_period_end=timezone.now())
    api_client.force_authenticate(user=user)
    invited = api_client.post(
        f"/api/v1/tenants/{tenant.id}/members/",
        {"email": "ops@acme.test", "first_name": "Ops", "role_code": "viewer", "password": "SecurePass!123"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert invited.status_code == 201
    assert Membership.objects.filter(tenant=tenant, user__email="ops@acme.test").exists()


@pytest.mark.django_db
def test_card_checkout_uses_enabled_stripe_gateway(api_client, user, tenant, monkeypatch):
    from apps.billing.models import PaymentGateway

    ensure_billing_catalog()
    PaymentGateway.objects.create(
        code="stripe-live",
        provider=PaymentGateway.Provider.STRIPE,
        display_name="Stripe",
        is_enabled=True,
        is_default=True,
        encrypted_config={"secret_key": "sk_test_x"},
    )
    growth = Plan.objects.get(code="growth")
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    created = api_client.post("/api/v1/billing/subscribe/", {"plan_id": str(growth.id)}, format="json", **headers)
    monkeypatch.setattr(
        "apps.billing.checkout.create_checkout_session",
        lambda invoice, gateway: {"checkout_url": "https://checkout.stripe.test/session", "external_id": "cs_test"},
    )
    pay = api_client.post(f"/api/v1/billing/invoices/{created.data['id']}/pay/", **headers)
    assert pay.status_code == 200
    assert pay.data["card_available"] is True
    assert pay.data["checkout_url"] == "https://checkout.stripe.test/session"
    hook = api_client.post(
        "/api/v1/billing/webhooks/stripe/",
        {"type": "checkout.session.completed", "data": {"object": {"metadata": {"invoice_id": created.data["id"]}}}},
        format="json",
    )
    assert hook.status_code == 200
    assert hook.data["applied"] is True
    assert Invoice.objects.get(id=created.data["id"]).status == Invoice.Status.PAID
