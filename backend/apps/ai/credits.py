from __future__ import annotations

from django.db.models import Count, F, Sum, Value
from django.db.models.functions import Greatest
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from apps.ai.models import AIRequest
from apps.billing.models import Plan, Subscription
from apps.common.exceptions import APIError


def billing_period_start(tenant):
    now = timezone.now()
    subscription = Subscription.objects.filter(tenant=tenant).select_related("plan").first()
    if subscription and subscription.current_period_end:
        delta = relativedelta(years=1) if subscription.plan.interval == Plan.Interval.YEAR else relativedelta(months=1)
        start = subscription.current_period_end - delta
        if start <= now:
            return start
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def plan_ai_credits(tenant) -> int:
    subscription = Subscription.objects.filter(tenant=tenant).select_related("plan").first()
    if subscription is None or subscription.plan_id is None:
        return 0
    return int(subscription.plan.ai_credits or 0)


def period_ai_queryset(tenant):
    return AIRequest.objects.for_tenant(tenant).filter(created_at__gte=billing_period_start(tenant))


def credits_used(tenant) -> int:
    total = (
        period_ai_queryset(tenant)
        .filter(status="completed")
        .annotate(credits=Greatest(F("prompt_tokens") + F("completion_tokens"), Value(1)))
        .aggregate(total=Sum("credits"))
        .get("total")
    )
    return int(total or 0)


def assert_ai_credits(tenant) -> None:
    limit = plan_ai_credits(tenant)
    used = credits_used(tenant)
    if used >= limit:
        raise APIError(
            "This workspace has used its package AI credits for the current billing period. Upgrade the package or wait until the period resets.",
            code="QUOTA_EXCEEDED",
            status_code=402,
            details={"credits_used": used, "credits_limit": limit},
        )


def usage_snapshot(tenant) -> dict:
    qs = period_ai_queryset(tenant)
    completed = qs.filter(status="completed")
    prompt = int(completed.aggregate(total=Sum("prompt_tokens")).get("total") or 0)
    completion = int(completed.aggregate(total=Sum("completion_tokens")).get("total") or 0)
    tokens = prompt + completion
    used = credits_used(tenant)
    limit = plan_ai_credits(tenant)
    return {
        "requests": qs.filter(status="completed").count(),
        "failed": qs.filter(status="failed").count(),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "tokens": tokens,
        "credits": used,
        "credits_used": used,
        "credits_limit": limit,
        "credits_remaining": max(limit - used, 0),
        "cost": str(completed.aggregate(total=Sum("cost")).get("total") or 0),
        "period_start": billing_period_start(tenant).isoformat(),
        "by_provider": list(
            completed.values("provider").annotate(
                tokens=Sum(F("prompt_tokens") + F("completion_tokens")),
                requests=Count("id"),
            ).order_by("-tokens")
        ),
    }
