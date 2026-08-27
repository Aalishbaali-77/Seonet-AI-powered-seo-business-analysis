from __future__ import annotations

from apps.notifications.models import Notification


def notify(*, tenant, user, title: str, body: str = "", kind: str = "info", link: str = "") -> Notification | None:
    if user is None or not getattr(user, "is_authenticated", True):
        return None
    return Notification.objects.create(tenant=tenant, user=user, title=title[:200], body=body, kind=kind, link=link)
