from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class UUIDPrimaryKeyModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        return self.update(deleted_at=timezone.now())


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"] if hasattr(self, "updated_at") else ["deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)


class TenantQuerySet(SoftDeleteQuerySet):
    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)


class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db).alive()

    def for_tenant(self, tenant):
        return self.get_queryset().for_tenant(tenant)


class TenantOwnedModel(UUIDPrimaryKeyModel, TimeStampedModel, SoftDeleteModel):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )

    objects = TenantManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
        ]
