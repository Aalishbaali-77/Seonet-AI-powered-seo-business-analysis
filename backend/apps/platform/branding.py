from __future__ import annotations

from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ASSET_SLOTS = (
    "logo",
    "logo_dark",
    "logo_mark",
    "logo_mark_dark",
    "logo_nav",
    "logo_nav_dark",
    "logo_sidebar",
    "logo_sidebar_dark",
    "logo_footer",
    "logo_footer_dark",
    "favicon",
    "app_icon",
)
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".ico", ".gif"}
ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "image/x-icon",
    "image/vnd.microsoft.icon",
    "image/ico",
}
LOGO_MAX_BYTES = 2 * 1024 * 1024
FAVICON_MAX_BYTES = 512 * 1024


def validate_brand_asset(upload, *, slot: str) -> None:
    name = (getattr(upload, "name", "") or "").lower()
    ext = Path(name).suffix
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("Use PNG, JPEG, WEBP, GIF, or ICO.")
    max_bytes = FAVICON_MAX_BYTES if slot == "favicon" else LOGO_MAX_BYTES
    size = getattr(upload, "size", 0) or 0
    if size > max_bytes:
        raise ValidationError(f"File must be under {max_bytes // 1024} KB.")
    content_type = (getattr(upload, "content_type", "") or "").lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES and not content_type.startswith("image/"):
        raise ValidationError("Unsupported image type.")
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("File is not a valid image.") from exc
    finally:
        upload.seek(0)


def replace_asset(appearance, slot: str, upload) -> None:
    field = getattr(appearance, slot)
    if field:
        field.delete(save=False)
    setattr(appearance, slot, upload)
    appearance.save(update_fields=[slot, "updated_at"])


def clear_asset(appearance, slot: str) -> None:
    field = getattr(appearance, slot)
    if field:
        field.delete(save=False)
        setattr(appearance, slot, "")
        appearance.save(update_fields=[slot, "updated_at"])
