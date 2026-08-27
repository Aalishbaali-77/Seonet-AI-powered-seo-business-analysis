from apps.usage.models import UsageRecord


def record_usage(*, tenant, user=None, event_type: str, quantity: int = 1, metadata: dict | None = None) -> UsageRecord:
    return UsageRecord.objects.create(
        tenant=tenant,
        user=user if getattr(user, "is_authenticated", False) else None,
        event_type=event_type,
        quantity=max(quantity, 0),
        metadata=metadata or {},
    )
