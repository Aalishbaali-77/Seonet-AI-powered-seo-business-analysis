from __future__ import annotations

from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel, UUIDPrimaryKeyModel


class Tenant(UUIDPrimaryKeyModel, TimeStampedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=80, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    settings = models.JSONField(default=dict, blank=True)
    feature_flags = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.name


class Membership(UUIDPrimaryKeyModel, TimeStampedModel):
    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="memberships")
    is_default = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        unique_together = ("tenant", "user")
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.tenant}"


class Team(UUIDPrimaryKeyModel, TimeStampedModel, SoftDeleteModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80)

    class Meta:
        unique_together = ("tenant", "slug")

    def __str__(self) -> str:
        return self.name


class TeamMembership(UUIDPrimaryKeyModel, TimeStampedModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="team_memberships")

    class Meta:
        unique_together = ("team", "user")
