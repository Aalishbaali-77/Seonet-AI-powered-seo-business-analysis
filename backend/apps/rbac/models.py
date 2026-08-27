from __future__ import annotations

from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class Permission(UUIDPrimaryKeyModel, TimeStampedModel):
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    module = models.CharField(max_length=40, db_index=True)

    def __str__(self) -> str:
        return self.code


class Role(UUIDPrimaryKeyModel, TimeStampedModel):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="roles",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=120)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, through="RolePermission", related_name="roles")

    class Meta:
        indexes = [
            models.Index(fields=["code"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["code"],
                condition=Q(tenant__isnull=True),
                name="uniq_system_role_code",
            ),
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=Q(tenant__isnull=False),
                name="uniq_tenant_role_code",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class RolePermission(UUIDPrimaryKeyModel, TimeStampedModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")

    class Meta:
        unique_together = ("role", "permission")


class MembershipRole(UUIDPrimaryKeyModel, TimeStampedModel):
    membership = models.ForeignKey(
        "tenants.Membership",
        on_delete=models.CASCADE,
        related_name="membership_roles",
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="membership_roles")

    class Meta:
        unique_together = ("membership", "role")
