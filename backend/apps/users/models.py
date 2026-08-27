from __future__ import annotations

import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email).lower()
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified_at", extra_fields.get("email_verified_at"))
        return self._create_user(email, password, **extra_fields)


class User(UUIDPrimaryKeyModel, TimeStampedModel, AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    mfa_enabled = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    avatar_url = models.URLField(blank=True)
    theme_preference = models.CharField(
        max_length=16,
        default="light",
        choices=[("light", "Light"), ("dark", "Dark"), ("system", "System")],
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email
