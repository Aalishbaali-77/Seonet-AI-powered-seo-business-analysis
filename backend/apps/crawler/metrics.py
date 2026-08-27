from __future__ import annotations

from urllib.parse import urlparse

ALREADY_COMPRESSED = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/avif",
    "image/gif",
    "video/mp4",
    "video/webm",
    "application/zip",
    "application/pdf",
    "application/gzip",
    "font/woff",
    "font/woff2",
    "application/font-woff",
    "application/font-woff2",
}

CDN_HEADER_HINTS = (
    ("cf-ray", "cloudflare"),
    ("cf-cache-status", "cloudflare"),
    ("x-amz-cf-id", "cloudfront"),
    ("x-cache", "cdn"),
    ("x-served-by", "fastly"),
    ("x-fastly-request-id", "fastly"),
    ("x-akamai-request-id", "akamai"),
    ("x-azure-ref", "azure"),
    ("x-vercel-id", "vercel"),
    ("x-nf-request-id", "netlify"),
)


def detect_cdn(headers: dict[str, str]) -> str:
    lowered = {str(key).lower(): str(value) for key, value in (headers or {}).items()}
    for header, name in CDN_HEADER_HINTS:
        if header in lowered and lowered[header]:
            return name
    server = (lowered.get("server") or "").lower()
    for token, name in (("cloudflare", "cloudflare"), ("cloudfront", "cloudfront"), ("akamai", "akamai"), ("fastly", "fastly"), ("netlify", "netlify"), ("vercel", "vercel")):
        if token in server:
            return name
    via = (lowered.get("via") or "").lower()
    if "cloudfront" in via:
        return "cloudfront"
    return ""


def compression_kind(content_encoding: str) -> str:
    value = (content_encoding or "").lower()
    if "br" in value.split(",") or "br" in value.split():
        return "brotli"
    if "gzip" in value or "x-gzip" in value:
        return "gzip"
    if "deflate" in value:
        return "deflate"
    return "none"


def is_compressible(content_type: str) -> bool:
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype in ALREADY_COMPRESSED:
        return False
    return ctype.startswith("text/") or ctype in {
        "application/javascript",
        "application/json",
        "application/xml",
        "application/xhtml+xml",
        "image/svg+xml",
        "application/ld+json",
    }


def parse_hsts(header: str) -> dict:
    raw = (header or "").strip()
    if not raw:
        return {"present": False, "max_age": 0, "include_subdomains": False, "preload": False}
    parts = [item.strip().lower() for item in raw.split(";") if item.strip()]
    max_age = 0
    for part in parts:
        if part.startswith("max-age="):
            try:
                max_age = int(part.split("=", 1)[1].strip())
            except ValueError:
                max_age = 0
    return {
        "present": True,
        "max_age": max_age,
        "include_subdomains": any(item == "includesubdomains" for item in parts),
        "preload": any(item == "preload" for item in parts),
        "raw": raw[:240],
    }


def parse_cache_control(header: str) -> dict:
    raw = (header or "").strip()
    directives = {}
    for part in [item.strip() for item in raw.split(",") if item.strip()]:
        if "=" in part:
            key, value = part.split("=", 1)
            directives[key.strip().lower()] = value.strip().strip('"')
        else:
            directives[part.lower()] = True
    max_age = None
    if "max-age" in directives:
        try:
            max_age = int(directives["max-age"])
        except (TypeError, ValueError):
            max_age = None
    s_maxage = None
    if "s-maxage" in directives:
        try:
            s_maxage = int(directives["s-maxage"])
        except (TypeError, ValueError):
            s_maxage = None
    return {
        "raw": raw[:240],
        "max_age": max_age,
        "s_maxage": s_maxage,
        "public": bool(directives.get("public")),
        "private": bool(directives.get("private")),
        "no_cache": bool(directives.get("no-cache")),
        "no_store": bool(directives.get("no-store")),
        "must_revalidate": bool(directives.get("must-revalidate")),
        "immutable": bool(directives.get("immutable")),
    }


def http_protocol(version: str, alt_svc: str = "") -> str:
    value = (version or "").upper().replace("_", "/")
    if "HTTP/3" in value or value in {"H3", "HTTP/3.0"}:
        return "HTTP/3"
    if "HTTP/2" in value or value in {"H2", "HTTP/2.0"}:
        return "HTTP/2"
    if "h3" in (alt_svc or "").lower():
        return "HTTP/2"  # negotiated HTTP/2 now; HTTP/3 advertised
    if "HTTP/1.0" in value:
        return "HTTP/1.0"
    return "HTTP/1.1" if value else "HTTP/1.1"


def first_party(url: str, page_host: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    page = (page_host or "").lower().removeprefix("www.")
    host = host.removeprefix("www.")
    return bool(host) and (host == page or host.endswith("." + page))


def compression_ratio(uncompressed: int, compressed: int) -> float | None:
    if uncompressed <= 0 or compressed <= 0:
        return None
    return round(max(0.0, min(1.0, 1 - (compressed / uncompressed))), 4)
