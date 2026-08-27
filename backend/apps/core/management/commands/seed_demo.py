from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.auditlog.services import write_audit
from apps.billing.entitlements import apply_plan_to_tenant, create_invoice, ensure_billing_catalog, issue_invoice
from apps.billing.models import Plan
from apps.notifications.models import Notification
from apps.platform.content import apply_platform_content
from apps.rbac.services import assign_role, sync_system_roles
from apps.tenants.models import Membership
from apps.tenants.services import create_tenant_for_owner
from apps.users.models import User

DEMO_PASSWORD_OWNER = "owner@123"
DEMO_PASSWORD_DEMO = "demo@123"


class Command(BaseCommand):
    help = "Create development-only platform owner, demo tenant, packages, and invoices. Do not run in production."

    def handle(self, *args, **options):
        sync_system_roles()
        ensure_billing_catalog(refresh_copy=True)
        apply_platform_content()
        with transaction.atomic():
            platform, _ = User.objects.get_or_create(
                email="owner@sigbl.com",
                defaults={
                    "first_name": "SI",
                    "last_name": "Global",
                    "is_staff": True,
                    "is_superuser": True,
                    "is_active": True,
                },
            )
            platform.set_password(DEMO_PASSWORD_OWNER)
            platform.is_staff = True
            platform.is_superuser = True
            platform.is_active = True
            platform.save()

            owner, _created = User.objects.get_or_create(
                email="demo@sigbl.com",
                defaults={
                    "first_name": "Amina",
                    "last_name": "Rahman",
                    "is_active": True,
                },
            )
            owner.set_password(DEMO_PASSWORD_DEMO)
            owner.is_active = True
            owner.save()
            tenant = owner.memberships.select_related("tenant").first()
            if tenant is None:
                tenant_obj = create_tenant_for_owner(name="SIPulse Demo Workspace", owner=owner)
            else:
                tenant_obj = tenant.tenant
            apply_plan_to_tenant(tenant_obj, Plan.objects.get(code="growth"), status="active")
            from apps.billing.entitlements import set_tenant_module
            from apps.billing.models import ProductModule

            integrations = ProductModule.objects.filter(code="integrations").first()
            if integrations:
                set_tenant_module(tenant_obj, integrations, enabled=True)

            role_users = {
                "admin": ("admin@demo.sipulse.local", "Jordan", "Lee"),
                "manager": ("manager@demo.sipulse.local", "Priya", "Shah"),
                "analyst": ("analyst@demo.sipulse.local", "Noah", "Bennett"),
                "sales_manager": ("sales.manager@demo.sipulse.local", "Elena", "Costa"),
                "sales_representative": ("sales@demo.sipulse.local", "Omar", "Hassan"),
                "marketing_user": ("marketing@demo.sipulse.local", "Sofia", "Martinez"),
                "viewer": ("viewer@demo.sipulse.local", "Chris", "Ng"),
            }
            for role, (email, first, last) in role_users.items():
                user, _made = User.objects.get_or_create(
                    email=email,
                    defaults={"first_name": first, "last_name": last, "is_active": True},
                )
                user.set_password(DEMO_PASSWORD_DEMO)
                user.is_active = True
                user.save()
                membership, _ = Membership.objects.get_or_create(
                    tenant=tenant_obj,
                    user=user,
                    defaults={"status": Membership.Status.ACTIVE},
                )
                assign_role(membership, role)

            Notification.objects.get_or_create(
                tenant=tenant_obj,
                user=owner,
                title="Welcome to SIPulse",
                defaults={
                    "body": "Your Growth workspace is ready. Add a website to run a real audit, then confirm an ICP before discovery.",
                    "kind": "info",
                },
            )
            from apps.crm.services import ensure_default_pipeline
            from apps.platform.lead_sources import ensure_lead_sources

            ensure_lead_sources()
            ensure_default_pipeline(tenant_obj)
            if not tenant_obj.invoices.exists():
                invoice = create_invoice(
                    tenant=tenant_obj,
                    description="Growth plan — demo workspace",
                    amount=Decimal("149.00"),
                    notes="Seeded development invoice. Card capture is not enabled until a live gateway is configured.",
                    subscription=tenant_obj.subscriptions.first(),
                )
                issue_invoice(invoice)
            write_audit(action="SEED_DEMO", tenant=tenant_obj, user=owner, resource_type="tenant", resource_id=tenant_obj.id)

        self.stdout.write(self.style.SUCCESS("Demo data ready (development only)."))
        self.stdout.write(f"  Platform owner: owner@sigbl.com / {DEMO_PASSWORD_OWNER}")
        self.stdout.write(f"  Tenant owner:   demo@sigbl.com / {DEMO_PASSWORD_DEMO}")
