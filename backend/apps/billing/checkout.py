from __future__ import annotations

import os
from decimal import Decimal
import httpx

from apps.billing.models import PaymentGateway


def public_app_url() -> str:
    return (os.environ.get("PUBLIC_APP_URL") or os.environ.get("NEXT_PUBLIC_APP_URL") or "http://localhost:3000").rstrip("/")


def active_card_gateway() -> PaymentGateway | None:
    rows = PaymentGateway.objects.filter(
        is_enabled=True,
        provider__in=[PaymentGateway.Provider.STRIPE, PaymentGateway.Provider.PAYPAL],
    ).order_by("-is_default", "display_name")
    for gateway in rows:
        if (gateway.encrypted_config or {}).get("secret_key"):
            return gateway
    return None


def create_checkout_session(invoice, gateway: PaymentGateway) -> dict:
    if gateway.provider == PaymentGateway.Provider.STRIPE:
        return _stripe_checkout(invoice, gateway)
    if gateway.provider == PaymentGateway.Provider.PAYPAL:
        return _paypal_checkout(invoice, gateway)
    raise RuntimeError("This gateway does not start a card checkout.")


def _stripe_checkout(invoice, gateway: PaymentGateway) -> dict:
    secret = (gateway.encrypted_config or {}).get("secret_key")
    app = public_app_url()
    amount = int((invoice.total or Decimal("0")) * 100)
    with httpx.Client(timeout=20) as client:
        response = client.post(
            "https://api.stripe.com/v1/checkout/sessions",
            auth=(secret, ""),
            data={
                "mode": "payment",
                "success_url": f"{app}/app/billing?checkout=success",
                "cancel_url": f"{app}/app/billing?checkout=cancel",
                "client_reference_id": str(invoice.id),
                "line_items[0][quantity]": "1",
                "line_items[0][price_data][currency]": (invoice.currency or "USD").lower(),
                "line_items[0][price_data][unit_amount]": str(amount),
                "line_items[0][price_data][product_data][name]": invoice.number,
                "metadata[invoice_id]": str(invoice.id),
            },
        )
    if response.status_code >= 400:
        raise RuntimeError(response.json().get("error", {}).get("message") or "Stripe checkout failed.")
    payload = response.json()
    return {"checkout_url": payload.get("url") or "", "external_id": payload.get("id") or ""}


def _paypal_checkout(invoice, gateway: PaymentGateway) -> dict:
    secret = (gateway.encrypted_config or {}).get("secret_key")
    client_id = (gateway.public_config or {}).get("publishable_key") or (gateway.encrypted_config or {}).get("client_id") or ""
    host = "https://api-m.sandbox.paypal.com" if gateway.test_mode else "https://api-m.paypal.com"
    app = public_app_url()
    with httpx.Client(timeout=20) as client:
        token = client.post(
            f"{host}/v1/oauth2/token",
            auth=(client_id, secret),
            data={"grant_type": "client_credentials"},
        )
        if token.status_code >= 400:
            raise RuntimeError("PayPal could not authenticate the stored client credentials.")
        access = token.json().get("access_token")
        order = client.post(
            f"{host}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": str(invoice.id),
                        "amount": {"currency_code": invoice.currency or "USD", "value": f"{invoice.total:.2f}"},
                    }
                ],
                "application_context": {
                    "return_url": f"{app}/app/billing?checkout=success",
                    "cancel_url": f"{app}/app/billing?checkout=cancel",
                },
            },
        )
    if order.status_code >= 400:
        raise RuntimeError("PayPal checkout failed.")
    payload = order.json()
    links = {item.get("rel"): item.get("href") for item in payload.get("links") or [] if item.get("rel")}
    return {"checkout_url": links.get("approve") or "", "external_id": payload.get("id") or ""}


def parse_stripe_invoice_id(payload: dict) -> str:
    data = payload.get("data") or {}
    obj = data.get("object") or payload
    meta = obj.get("metadata") or {}
    return str(meta.get("invoice_id") or obj.get("client_reference_id") or "").strip()
