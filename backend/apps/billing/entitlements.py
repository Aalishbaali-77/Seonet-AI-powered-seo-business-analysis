from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from apps.billing.catalog import DEFAULT_GATEWAYS, DEFAULT_PACKAGES, MODULE_FEATURES, PRODUCT_MODULES
from apps.billing.models import (
    Invoice,
    InvoiceLine,
    ModuleFeature,
    PaymentGateway,
    Plan,
    PlanFeature,
    PlanModule,
    ProductModule,
    Subscription,
    TenantModule,
)
from apps.tenants.models import Tenant


def _plan_defaults(package: dict) -> dict:
    return {
        "name": package["name"],
        "description": package["description"],
        "price_amount": Decimal(str(package["price_amount"])),
        "interval": package["interval"],
        "trial_days": package["trial_days"],
        "max_pages": package["max_pages"],
        "max_audits_per_month": package["max_audits_per_month"],
        "ai_credits": package["ai_credits"],
        "max_users": package["max_users"],
        "is_public": package.get("is_public", True),
        "is_featured": package.get("is_featured", False),
        "cta_label": package.get("cta_label", ""),
        "cta_href": package.get("cta_href", ""),
        "sort_order": package["sort_order"],
        "is_active": True,
    }


def ensure_billing_catalog(*, refresh_copy: bool = False) -> None:
    modules: dict[str, ProductModule] = {}
    for item in PRODUCT_MODULES:
        defaults = {
            "name": item["name"],
            "description": item["description"],
            "category": item["category"],
            "sort_order": item["sort_order"],
            "is_active": True,
        }
        module, created = ProductModule.objects.get_or_create(code=item["code"], defaults=defaults)
        if refresh_copy and not created:
            for key, value in defaults.items():
                setattr(module, key, value)
            module.save()
        modules[module.code] = module

    for module_code, feature_code, name, description in MODULE_FEATURES:
        module = modules[module_code]
        feature, created = ModuleFeature.objects.get_or_create(
            module=module,
            code=feature_code,
            defaults={"name": name, "description": description, "is_active": True},
        )
        if refresh_copy and not created:
            feature.name = name
            feature.description = description
            feature.is_active = True
            feature.save(update_fields=["name", "description", "is_active", "updated_at"])

    for package in DEFAULT_PACKAGES:
        defaults = _plan_defaults(package)
        plan, created = Plan.objects.get_or_create(code=package["code"], defaults=defaults)
        if refresh_copy and not created:
            for key, value in defaults.items():
                setattr(plan, key, value)
            plan.save()
        if created or refresh_copy or not plan.plan_modules.exists():
            set_plan_modules(plan, list(package["modules"]))

    for gateway in DEFAULT_GATEWAYS:
        defaults = {
            "provider": gateway["provider"],
            "display_name": gateway["display_name"],
            "is_enabled": gateway["is_enabled"],
            "is_default": gateway["is_default"],
            "test_mode": gateway["test_mode"],
            "public_config": gateway["public_config"],
        }
        obj, created = PaymentGateway.objects.get_or_create(code=gateway["code"], defaults=defaults)
        if refresh_copy and not created:
            obj.display_name = gateway["display_name"]
            obj.public_config = gateway["public_config"]
            obj.save(update_fields=["display_name", "public_config", "updated_at"])

    from apps.platform.lead_sources import ensure_lead_sources

    ensure_lead_sources()
    from apps.markets.catalog import ensure_geo_catalog

    ensure_geo_catalog()
    _ensure_catalog_modules_on_plans()


def _ensure_catalog_modules_on_plans() -> None:
    for package in DEFAULT_PACKAGES:
        plan = Plan.objects.filter(code=package["code"]).first()
        if plan is None:
            continue
        for code in package["modules"]:
            module = ProductModule.objects.filter(code=code).first()
            if module is None:
                continue
            PlanModule.objects.get_or_create(plan=plan, module=module, defaults={"is_included": True})
            for feature in ModuleFeature.objects.filter(module=module, is_active=True):
                PlanFeature.objects.get_or_create(plan=plan, feature=feature, defaults={"is_enabled": True})
        for subscription in Subscription.objects.filter(plan=plan).select_related("tenant"):
            sync_tenant_modules_from_plan(subscription.tenant, plan)


def set_plan_modules(plan: Plan, module_codes: list[str]) -> None:
    modules = list(ProductModule.objects.filter(code__in=module_codes))
    PlanModule.objects.filter(plan=plan).exclude(module__in=modules).delete()
    for module in modules:
        PlanModule.objects.get_or_create(plan=plan, module=module, defaults={"is_included": True})
    features = ModuleFeature.objects.filter(module__in=modules, is_active=True)
    PlanFeature.objects.filter(plan=plan).exclude(feature__in=features).delete()
    for feature in features:
        PlanFeature.objects.get_or_create(plan=plan, feature=feature, defaults={"is_enabled": True})


def plan_period_end(plan: Plan, *, status: str, now=None):
    now = now or timezone.now()
    if status == Subscription.Status.TRIALING:
        return now + timedelta(days=plan.trial_days or 14)
    if plan.interval == Plan.Interval.YEAR:
        return now + relativedelta(years=1)
    return now + relativedelta(months=1)


def apply_plan_to_tenant(tenant: Tenant, plan: Plan, *, status: str | None = None) -> Subscription:
    ensure_billing_catalog()
    gateway = PaymentGateway.objects.filter(is_default=True).first() or PaymentGateway.objects.filter(is_enabled=True).first()
    subscription = Subscription.objects.filter(tenant=tenant).first()
    desired_status = status or (subscription.status if subscription else Subscription.Status.TRIALING)
    period_end = plan_period_end(plan, status=desired_status)
    if subscription is None:
        subscription = Subscription.objects.create(
            tenant=tenant,
            plan=plan,
            status=desired_status,
            gateway=gateway,
            current_period_end=period_end,
        )
    else:
        subscription.plan = plan
        subscription.status = desired_status
        subscription.current_period_end = period_end
        if gateway and subscription.gateway_id is None:
            subscription.gateway = gateway
        subscription.save()
    sync_tenant_modules_from_plan(tenant, plan)
    return subscription


def sync_tenant_modules_from_plan(tenant: Tenant, plan: Plan) -> None:
    included = {
        pm.module_id: pm
        for pm in plan.plan_modules.filter(is_included=True).select_related("module")
    }
    TenantModule.objects.filter(tenant=tenant, source=TenantModule.Source.PLAN).exclude(module_id__in=included).delete()
    for module_id, plan_module in included.items():
        assignment, created = TenantModule.objects.get_or_create(
            tenant=tenant,
            module_id=module_id,
            defaults={
                "is_enabled": True,
                "source": TenantModule.Source.PLAN,
                "limits": plan_module.limits,
            },
        )
        if not created and assignment.source == TenantModule.Source.PLAN:
            assignment.is_enabled = True
            assignment.limits = plan_module.limits
            assignment.save(update_fields=["is_enabled", "limits", "updated_at"])


def tenant_module_codes(tenant: Tenant | None) -> set[str]:
    if tenant is None:
        return set()
    subscription = refresh_subscription_state(tenant)
    if not subscription_allows_access(subscription):
        return set()
    return set(
        TenantModule.objects.filter(tenant=tenant, is_enabled=True, module__is_active=True).values_list(
            "module__code",
            flat=True,
        )
    )


ACCESS_STATUSES = {Subscription.Status.TRIALING, Subscription.Status.ACTIVE}


def subscription_allows_access(subscription: Subscription | None) -> bool:
    if subscription is None:
        return False
    if subscription.status not in ACCESS_STATUSES:
        return False
    if subscription.current_period_end and subscription.current_period_end < timezone.now():
        return False
    return True


def refresh_subscription_state(tenant: Tenant | None) -> Subscription | None:
    if tenant is None:
        return None
    subscription = Subscription.objects.filter(tenant=tenant).select_related("plan", "gateway").first()
    if subscription is None:
        return None
    now = timezone.now()
    for invoice in Invoice.objects.filter(tenant=tenant, status=Invoice.Status.ISSUED):
        previous = invoice.status
        invoice.recast_status()
        if invoice.status != previous:
            invoice.save(update_fields=["status", "updated_at"])
    changed_fields: list[str] = []
    if subscription.current_period_end is None and subscription.status in ACCESS_STATUSES:
        subscription.current_period_end = plan_period_end(subscription.plan, status=subscription.status)
        changed_fields.append("current_period_end")
    if (
        subscription.status in ACCESS_STATUSES | {Subscription.Status.PAST_DUE}
        and subscription.current_period_end
        and subscription.current_period_end < now
    ):
        subscription.status = Subscription.Status.EXPIRED
        changed_fields.append("status")
    if changed_fields:
        changed_fields.append("updated_at")
        subscription.save(update_fields=changed_fields)
    return subscription


def assert_subscription_access(tenant: Tenant) -> None:
    from apps.common.exceptions import APIError

    subscription = refresh_subscription_state(tenant)
    if subscription_allows_access(subscription):
        return
    raise APIError(
        "Your subscription is inactive. Choose a package and complete payment to restore workspace access.",
        code="SUBSCRIPTION_INACTIVE",
        status_code=402,
        details={"redirect": "/app/billing"},
    )


def subscription_payload(tenant: Tenant | None) -> dict:
    from apps.tenants.members import occupied_seats

    subscription = refresh_subscription_state(tenant)
    if tenant is None or subscription is None:
        return {
            "status": "none",
            "access": False,
            "current_period_end": None,
            "plan_id": None,
            "plan_code": None,
            "plan_name": None,
            "max_users": 0,
            "seats_used": 0,
        }
    return {
        "status": subscription.status,
        "access": subscription_allows_access(subscription),
        "current_period_end": subscription.current_period_end,
        "plan_id": str(subscription.plan_id),
        "plan_code": subscription.plan.code,
        "plan_name": subscription.plan.name,
        "max_users": subscription.plan.max_users,
        "seats_used": occupied_seats(tenant),
    }


def payment_method_payload() -> dict:
    from apps.billing.checkout import active_card_gateway

    card = active_card_gateway()
    if card is not None:
        return {
            "method": card.provider,
            "gateway_name": card.display_name,
            "card_available": True,
            "instructions": f"Pay this invoice with {card.display_name}. Seonet opens the gateway checkout and marks the invoice paid when that gateway confirms collection.",
        }
    gateway = PaymentGateway.objects.filter(is_default=True).first() or PaymentGateway.objects.filter(is_enabled=True).first()
    if gateway is None:
        return {
            "method": "invoice",
            "gateway_name": "Manual invoice",
            "card_available": False,
            "instructions": "Pay issued invoices. Access restores after SI Global confirms payment.",
        }
    instructions = (gateway.public_config or {}).get("instructions") or (
        "Pay issued invoices. Access restores after SI Global confirms payment."
    )
    return {
        "method": "invoice",
        "gateway_name": gateway.display_name,
        "card_available": False,
        "instructions": instructions,
    }


@transaction.atomic
def request_plan_subscription(tenant: Tenant, plan: Plan) -> Invoice:
    from apps.common.exceptions import APIError

    if not plan.is_active or not plan.is_public:
        raise APIError("That package is not available for self-serve checkout.", code="VALIDATION_ERROR")
    if plan.price_amount <= 0:
        raise APIError("Custom packages are billed by SI Global. Contact sales to continue.", code="VALIDATION_ERROR")
    ensure_billing_catalog()
    subscription = refresh_subscription_state(tenant)
    if (
        subscription
        and subscription.plan_id == plan.id
        and subscription_allows_access(subscription)
        and subscription.status == Subscription.Status.ACTIVE
    ):
        raise APIError("This workspace is already on that package.", code="CONFLICT", status_code=409)
    open_invoice = (
        Invoice.objects.filter(tenant=tenant, plan=plan, status__in=[Invoice.Status.DRAFT, Invoice.Status.ISSUED, Invoice.Status.OVERDUE])
        .order_by("-created_at")
        .first()
    )
    if open_invoice:
        if open_invoice.status == Invoice.Status.DRAFT:
            return issue_invoice(open_invoice)
        return open_invoice
    if subscription is None:
        subscription = apply_plan_to_tenant(tenant, plan, status=Subscription.Status.TRIALING)
        subscription.status = Subscription.Status.EXPIRED
        subscription.current_period_end = timezone.now()
        subscription.save(update_fields=["status", "current_period_end", "updated_at"])
    invoice = create_invoice(
        tenant=tenant,
        description=f"{plan.name} · {plan.interval}",
        amount=plan.price_amount,
        notes=f"Self-serve package request for {plan.name}.",
        subscription=subscription,
        plan=plan,
    )
    return issue_invoice(invoice)


def start_invoice_payment(invoice: Invoice) -> dict:
    from apps.billing.checkout import active_card_gateway, create_checkout_session
    from apps.common.exceptions import APIError

    invoice.recast_status()
    if invoice.status not in {Invoice.Status.ISSUED, Invoice.Status.OVERDUE}:
        raise APIError("This invoice cannot be paid.", code="VALIDATION_ERROR")
    payment = payment_method_payload()
    gateway = active_card_gateway()
    checkout_url = ""
    if gateway is not None:
        try:
            session = create_checkout_session(invoice, gateway)
        except Exception as exc:  # noqa: BLE001
            raise APIError(str(exc) or "Card checkout is not available.", code="VALIDATION_ERROR") from exc
        checkout_url = session.get("checkout_url") or ""
        invoice.gateway = gateway
        invoice.external_id = session.get("external_id") or invoice.external_id
        invoice.save(update_fields=["gateway", "external_id", "updated_at"])
    return {
        "method": payment["method"],
        "paid": False,
        "invoice_id": str(invoice.id),
        "status": invoice.status,
        "instructions": payment["instructions"],
        "gateway_name": payment["gateway_name"],
        "card_available": payment["card_available"],
        "checkout_url": checkout_url,
    }


def set_tenant_module(tenant: Tenant, module: ProductModule, *, enabled: bool) -> TenantModule:
    assignment, _ = TenantModule.objects.update_or_create(
        tenant=tenant,
        module=module,
        defaults={"is_enabled": enabled, "source": TenantModule.Source.OVERRIDE},
    )
    return assignment


def next_invoice_number() -> str:
    year = timezone.now().year
    prefix = f"INV-{year}-"
    latest = Invoice.all_objects.filter(number__startswith=prefix).order_by("-number").values_list("number", flat=True).first()
    sequence = 1
    if latest:
        try:
            sequence = int(latest.split("-")[-1]) + 1
        except ValueError:
            sequence = Invoice.all_objects.filter(number__startswith=prefix).count() + 1
    return f"{prefix}{sequence:04d}"


@transaction.atomic
def create_invoice(
    *,
    tenant: Tenant,
    description: str,
    amount: Decimal,
    notes: str = "",
    subscription: Subscription | None = None,
    gateway: PaymentGateway | None = None,
    plan: Plan | None = None,
) -> Invoice:
    gateway = gateway or PaymentGateway.objects.filter(is_default=True).first()
    billing_plan = plan or (subscription.plan if subscription else None)
    invoice = Invoice.objects.create(
        tenant=tenant,
        subscription=subscription,
        plan=billing_plan,
        gateway=gateway,
        number=next_invoice_number(),
        currency=billing_plan.currency if billing_plan else "USD",
        subtotal=amount,
        tax=Decimal("0.00"),
        total=amount,
        notes=notes,
        due_at=timezone.now() + timedelta(days=14),
    )
    InvoiceLine.objects.create(
        invoice=invoice,
        description=description,
        quantity=1,
        unit_amount=amount,
        amount=amount,
    )
    return invoice


def issue_invoice(invoice: Invoice) -> Invoice:
    if invoice.status != Invoice.Status.DRAFT:
        return invoice
    invoice.status = Invoice.Status.ISSUED
    invoice.issued_at = timezone.now()
    invoice.save(update_fields=["status", "issued_at", "updated_at"])
    return invoice


def mark_invoice_paid(invoice: Invoice) -> Invoice:
    if invoice.status == Invoice.Status.VOID:
        raise ValueError("Void invoices cannot be marked paid.")
    invoice.status = Invoice.Status.PAID
    invoice.paid_at = timezone.now()
    invoice.save(update_fields=["status", "paid_at", "updated_at"])
    plan = invoice.plan or (invoice.subscription.plan if invoice.subscription else None)
    if plan and invoice.subscription and invoice.subscription.status != Subscription.Status.CANCELED:
        apply_plan_to_tenant(invoice.tenant, plan, status=Subscription.Status.ACTIVE)
    elif invoice.subscription and invoice.subscription.status != Subscription.Status.CANCELED:
        invoice.subscription.status = Subscription.Status.ACTIVE
        invoice.subscription.current_period_end = plan_period_end(invoice.subscription.plan, status=Subscription.Status.ACTIVE)
        invoice.subscription.save(update_fields=["status", "current_period_end", "updated_at"])
    return invoice


def update_draft_invoice(invoice: Invoice, *, description: str | None = None, amount: Decimal | None = None, notes: str | None = None) -> Invoice:
    if invoice.status != Invoice.Status.DRAFT:
        raise ValueError("Only draft invoices can be edited.")
    if notes is not None:
        invoice.notes = notes
    if amount is not None:
        invoice.subtotal = amount
        invoice.total = amount + invoice.tax
    invoice.save()
    line = invoice.lines.first()
    if line:
        if description is not None:
            line.description = description
        if amount is not None:
            line.unit_amount = amount
            line.amount = amount
        line.save()
    elif description and amount is not None:
        InvoiceLine.objects.create(invoice=invoice, description=description, quantity=1, unit_amount=amount, amount=amount)
    return invoice


def void_invoice(invoice: Invoice) -> Invoice:
    if invoice.status == Invoice.Status.PAID:
        raise ValueError("Paid invoices cannot be voided.")
    invoice.status = Invoice.Status.VOID
    invoice.save(update_fields=["status", "updated_at"])
    return invoice
