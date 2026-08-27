from __future__ import annotations

import json
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        raise RuntimeError("FIELD_ENCRYPTION_KEY is not configured.")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_json(value) -> str:
    payload = json.dumps(value if value is not None else {}).encode("utf-8")
    return _fernet().encrypt(payload).decode("utf-8")


def decrypt_json(token: str | None) -> dict:
    if not token:
        return {}
    try:
        payload = _fernet().decrypt(token.encode("utf-8"))
    except (InvalidToken, ValueError):
        return {}
    try:
        return json.loads(payload.decode("utf-8"))
    except (TypeError, ValueError):
        return {}


class EncryptedJSONField(models.TextField):
    """A JSON dict, encrypted at rest with Fernet. Never stores plaintext secrets."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default", dict)
        kwargs.setdefault("blank", True)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        return decrypt_json(value)

    def to_python(self, value):
        if isinstance(value, dict):
            return value
        return decrypt_json(value)

    def get_prep_value(self, value):
        return encrypt_json(value)
