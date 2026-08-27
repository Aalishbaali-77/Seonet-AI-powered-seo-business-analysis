from __future__ import annotations

import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(str(settings.SECRET_KEY).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_json(payload: dict | None) -> str:
    if not payload:
        return ""
    return _fernet().encrypt(json.dumps(payload).encode("utf-8")).decode("ascii")


def decrypt_json(blob: str) -> dict:
    if not blob:
        return {}
    try:
        raw = _fernet().decrypt(blob.encode("ascii"))
    except InvalidToken:
        return {}
    data = json.loads(raw.decode("utf-8"))
    return data if isinstance(data, dict) else {}
