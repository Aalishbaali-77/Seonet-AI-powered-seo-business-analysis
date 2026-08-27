from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.common.exceptions import APIError

User = get_user_model()

PLATFORM_ADMIN_FILTER = Q(is_staff=True) | Q(is_superuser=True)


def platform_admins() -> QuerySet:
    return User.objects.filter(PLATFORM_ADMIN_FILTER).order_by("-date_joined")


def _active_admin_count(*, exclude_id: str | None = None) -> int:
    qs = platform_admins().filter(is_active=True)
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    return qs.count()


def _reset_url(uid: str, token: str) -> str:
    origin = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else "http://localhost:3000"
    return f"{origin}/reset-password?uid={uid}&token={token}"


def send_platform_admin_invite_email(user) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    send_mail(
        subject="You've been added as a Seonet platform admin",
        message=f"You were added as a Seonet platform admin. Set your password: {_reset_url(uid, token)}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def send_platform_admin_reset_email(user) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    send_mail(
        subject="Reset your Seonet platform admin password",
        message=f"Reset your password: {_reset_url(uid, token)}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


@transaction.atomic
def invite_platform_admin(*, email: str, first_name: str = "", last_name: str = ""):
    email = email.lower().strip()
    if not email:
        raise APIError("An email address is required.", code="VALIDATION_ERROR")
    user = User.objects.filter(email=email).first()
    if user is not None:
        if user.is_staff or user.is_superuser:
            raise APIError("That person is already a platform admin.", code="CONFLICT", status_code=409)
        user.is_staff = True
        user.first_name = first_name or user.first_name
        user.last_name = last_name or user.last_name
        user.save(update_fields=["is_staff", "first_name", "last_name"])
        return user
    user = User(email=email, first_name=first_name, last_name=last_name, is_staff=True, is_superuser=False, is_active=True)
    user.set_unusable_password()
    user.save()
    send_platform_admin_invite_email(user)
    return user


@transaction.atomic
def set_platform_admin_active(*, admin, actor, is_active: bool):
    if not is_active:
        if admin.id == getattr(actor, "id", None):
            raise APIError("You cannot suspend your own access.", code="VALIDATION_ERROR")
        if _active_admin_count(exclude_id=admin.id) < 1:
            raise APIError("At least one active platform admin is required.", code="VALIDATION_ERROR")
    admin.is_active = is_active
    admin.save(update_fields=["is_active"])
    return admin


@transaction.atomic
def remove_platform_admin(*, admin, actor):
    if admin.id == getattr(actor, "id", None):
        raise APIError("You cannot remove your own access.", code="VALIDATION_ERROR")
    if _active_admin_count(exclude_id=admin.id) < 1:
        raise APIError("At least one active platform admin is required.", code="VALIDATION_ERROR")
    admin.is_active = False
    admin.is_staff = False
    admin.is_superuser = False
    admin.save(update_fields=["is_active", "is_staff", "is_superuser"])
    return admin


def force_platform_admin_password_reset(admin) -> None:
    send_platform_admin_reset_email(admin)
