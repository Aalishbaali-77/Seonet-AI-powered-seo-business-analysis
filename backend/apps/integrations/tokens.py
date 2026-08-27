from __future__ import annotations

import hashlib
import hmac
import secrets

from django.utils import timezone

from apps.integrations.models import TenantApiToken

TOKEN_PREFIX = "sip_live_"


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_api_token(*, tenant, user, name: str) -> tuple[TenantApiToken, str]:
    label = (name or "").strip() or "Workspace API token"
    if len(label) > 80:
        raise ValueError("Token name is too long.")
    raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    token = TenantApiToken.objects.create(
        tenant=tenant,
        name=label,
        prefix=raw[:16],
        hashed_key=_hash_token(raw),
        created_by=user,
    )
    return token, raw


def revoke_api_token(token: TenantApiToken) -> None:
    if token.revoked_at:
        return
    token.revoked_at = timezone.now()
    token.save(update_fields=["revoked_at", "updated_at"])


def authenticate_api_token(raw: str) -> TenantApiToken | None:
    if not raw or not raw.startswith(TOKEN_PREFIX) or len(raw) < 20:
        return None
    prefix = raw[:16]
    digest = _hash_token(raw)
    for token in TenantApiToken.objects.filter(prefix=prefix, revoked_at__isnull=True).select_related("tenant", "created_by"):
        if hmac.compare_digest(token.hashed_key, digest):
            if token.created_by_id is None or not token.created_by.is_active:
                return None
            token.last_used_at = timezone.now()
            token.save(update_fields=["last_used_at", "updated_at"])
            return token
    return None
