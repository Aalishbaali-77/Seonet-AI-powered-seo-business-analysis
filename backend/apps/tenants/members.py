from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.text import slugify

from apps.billing.models import Subscription
from apps.common.exceptions import APIError
from apps.rbac.models import MembershipRole, Role
from apps.rbac.services import assign_role
from apps.tenants.models import Membership, Tenant

User = get_user_model()

PUBLIC_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "icloud.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
    "mail.com",
    "yandex.com",
}


def split_full_name(name: str) -> tuple[str, str]:
    parts = name.strip().split(None, 1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def infer_first_name(*, email: str, first_name: str = "", full_name: str = "") -> str:
    if first_name.strip():
        return first_name.strip()
    if full_name.strip():
        return split_full_name(full_name)[0]
    local = email.split("@")[0].replace(".", " ").replace("_", " ").replace("-", " ")
    token = local.split()[0] if local else "Workspace"
    return token.title()


def workspace_name_from_identity(*, company_name: str = "", email: str = "", first_name: str = "") -> str:
    if company_name.strip():
        return company_name.strip()[:255]
    domain = (email.split("@")[-1] if "@" in email else "").lower()
    if domain and domain not in PUBLIC_EMAIL_DOMAINS:
        label = domain.split(".")[0].replace("-", " ").replace("_", " ")
        return label.title()[:255]
    person = first_name.strip() or infer_first_name(email=email)
    return f"{person}'s workspace"[:255]


def tenant_seat_limit(tenant: Tenant) -> int:
    subscription = Subscription.objects.filter(tenant=tenant).select_related("plan").first()
    if subscription:
        return subscription.plan.max_users
    return 5


def occupied_seats(tenant: Tenant) -> int:
    return tenant.memberships.exclude(status=Membership.Status.DISABLED).count()


def _actor_is_owner(user, tenant: Tenant) -> bool:
    return "owner" in {
        code
        for code in Membership.objects.filter(user=user, tenant=tenant, status=Membership.Status.ACTIVE)
        .values_list("membership_roles__role__code", flat=True)
        if code
    } or bool(getattr(user, "is_superuser", False))


def _owner_count(tenant: Tenant) -> int:
    return (
        Membership.objects.filter(tenant=tenant, status=Membership.Status.ACTIVE, membership_roles__role__code="owner")
        .distinct()
        .count()
    )


def _member_is_owner(membership: Membership) -> bool:
    return membership.membership_roles.filter(role__code="owner").exists()


def set_membership_role(membership: Membership, role_code: str, *, actor) -> None:
    if role_code == "owner" and not _actor_is_owner(actor, membership.tenant):
        raise APIError("Only an owner can assign the owner role.", code="PERMISSION_DENIED", status_code=403)
    role = Role.objects.filter(tenant=membership.tenant, code=role_code).first()
    if role is None:
        raise APIError("That role does not exist in this workspace.", code="VALIDATION_ERROR")
    if _member_is_owner(membership) and role_code != "owner" and _owner_count(membership.tenant) <= 1:
        raise APIError("The workspace needs at least one owner.", code="VALIDATION_ERROR")
    MembershipRole.objects.filter(membership=membership).exclude(role=role).delete()
    assign_role(membership, role_code)


def send_password_setup_email(user) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    origin = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else "http://localhost:3000"
    reset_url = f"{origin}/reset-password?uid={uid}&token={token}"
    send_mail(
        subject="Set up your Seonet password",
        message=f"You were added to a Seonet workspace. Set your password: {reset_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


@transaction.atomic
def add_tenant_member(
    *,
    tenant: Tenant,
    actor,
    email: str,
    role_code: str,
    first_name: str = "",
    last_name: str = "",
    password: str = "",
) -> Membership:
    email = email.lower().strip()
    if occupied_seats(tenant) >= tenant_seat_limit(tenant):
        raise APIError("This workspace is at its seat limit. Upgrade the package or disable a member.", code="CONFLICT", status_code=409)

    user = User.objects.filter(email=email).first()
    created_user = False
    if user is None:
        user = User(email=email, first_name=first_name, last_name=last_name)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        created_user = True
    elif not user.is_active:
        raise APIError("That account is disabled.", code="VALIDATION_ERROR")
    else:
        if first_name and not user.first_name:
            user.first_name = first_name
        if last_name and not user.last_name:
            user.last_name = last_name
        user.save(update_fields=["first_name", "last_name"])

    membership = Membership.objects.filter(tenant=tenant, user=user).first()
    if membership and membership.status != Membership.Status.DISABLED:
        raise APIError("That person is already in this workspace.", code="CONFLICT", status_code=409)
    if membership is None:
        membership = Membership.objects.create(
            tenant=tenant,
            user=user,
            status=Membership.Status.ACTIVE if password or not created_user else Membership.Status.INVITED,
        )
    else:
        membership.status = Membership.Status.ACTIVE if password or not created_user else Membership.Status.INVITED
        membership.save(update_fields=["status", "updated_at"])

    set_membership_role(membership, role_code or "viewer", actor=actor)
    if created_user and not password:
        send_password_setup_email(user)
    return membership


@transaction.atomic
def update_tenant_member(*, membership: Membership, actor, role_code: str | None = None, status: str | None = None) -> Membership:
    if status and status not in Membership.Status.values:
        raise APIError("Invalid member status.", code="VALIDATION_ERROR")
    if status == Membership.Status.DISABLED and _member_is_owner(membership) and _owner_count(membership.tenant) <= 1:
        raise APIError("The workspace needs at least one owner.", code="VALIDATION_ERROR")
    if status == Membership.Status.DISABLED and membership.user_id == getattr(actor, "id", None):
        raise APIError("You cannot disable your own access.", code="VALIDATION_ERROR")
    if status:
        membership.status = status
        membership.save(update_fields=["status", "updated_at"])
    if role_code:
        set_membership_role(membership, role_code, actor=actor)
    return membership


@transaction.atomic
def remove_tenant_member(*, membership: Membership, actor) -> None:
    if membership.user_id == getattr(actor, "id", None):
        raise APIError("You cannot remove yourself.", code="VALIDATION_ERROR")
    if _member_is_owner(membership) and _owner_count(membership.tenant) <= 1:
        raise APIError("The workspace needs at least one owner.", code="VALIDATION_ERROR")
    membership.delete()


def role_code_from_name(name: str) -> str:
    code = slugify(name).replace("-", "_")[:64] or "custom_role"
    return code
