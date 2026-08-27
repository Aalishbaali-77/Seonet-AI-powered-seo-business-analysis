from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx

from apps.crawler.metrics import compression_kind, detect_cdn, http_protocol, parse_cache_control, parse_hsts
from apps.crawler.ssrf import SSRFBlocked, resolve_pinned_target, validate_public_http_url

logger = logging.getLogger("seonet.crawler")

ALLOWED_HTML_TYPES = {"text/html", "application/xhtml+xml"}
ALLOWED_TEXT_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "text/xml",
    "application/xml",
    "application/rss+xml",
    "application/atom+xml",
    "text/sitemap",
}
MAX_REDIRECTS = 5
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class UnsafeRedirect(SSRFBlocked):
    default_detail = "Redirect target is not allowed."


@dataclass
class FetchResult:
    url: str
    status_code: int
    content_type: str
    body: str
    elapsed_ms: int = 0
    ttfb_ms: int = 0
    download_ms: int = 0
    size_bytes: int = 0
    transfer_bytes: int = 0
    headers: dict[str, str] = field(default_factory=dict)
    redirect_count: int = 0
    hops: list[str] = field(default_factory=list)
    redirect_hops: list[dict] = field(default_factory=list)
    http_version: str = ""
    http_protocol: str = "HTTP/1.1"
    timing: dict = field(default_factory=dict)


def _lower_headers(response) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in response.headers.items()}


def _hop(url: str, status: int, headers: dict[str, str] | None = None) -> dict:
    return {
        "url": url,
        "status": status,
        "type": str(status),
        "https": url.startswith("https://"),
        "host": urlparse(url).netloc,
        "cache_control": (headers or {}).get("cache-control") or "",
    }


def fetch_document(
    url: str,
    *,
    timeout: int = 10,
    max_bytes: int = 2_000_000,
    allowed_types: set[str] | None = None,
    require_type: bool = False,
) -> FetchResult:
    allowed = allowed_types or ALLOWED_HTML_TYPES
    current = validate_public_http_url(url)
    last_error = "Unable to fetch URL."
    hops = [current]
    redirect_hops: list[dict] = []
    started = time.perf_counter()
    with httpx.Client(follow_redirects=False, timeout=timeout, headers={"User-Agent": "SeonetBot/1.0"}) as client:
        for _ in range(MAX_REDIRECTS + 1):
            hop_started = time.perf_counter()
            try:
                pinned_url, host_header, sni_hostname = resolve_pinned_target(current)
                request_headers = {"Host": host_header}
                extensions = {"sni_hostname": sni_hostname} if pinned_url.startswith("https://") else {}
                response = client.get(pinned_url, headers=request_headers, extensions=extensions)
            except httpx.HTTPError as exc:
                last_error = str(exc)
                logger.info("crawl_url_failure url=%s error=%s", current, type(exc).__name__)
                break
            headers = _lower_headers(response)
            if response.status_code in REDIRECT_STATUSES:
                location = response.headers.get("Location")
                if not location:
                    raise SSRFBlocked("Redirect is missing a Location header.")
                nxt = urljoin(current, location)
                try:
                    nxt = validate_public_http_url(nxt)
                except SSRFBlocked:
                    logger.info("crawl_redirect_blocked from=%s", current)
                    raise
                redirect_hops.append(_hop(current, response.status_code, headers))
                if nxt in hops:
                    redirect_hops.append({**_hop(nxt, 0, {}), "loop": True})
                    raise SSRFBlocked("Redirect loop detected.")
                hops.append(nxt)
                current = nxt
                continue
            content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
            if content_type and content_type not in allowed:
                if require_type or allowed == ALLOWED_HTML_TYPES:
                    raise SSRFBlocked("Only HTML responses can be audited.")
            raw = response.content
            transfer = int(getattr(response, "num_bytes_downloaded", 0) or 0)
            if not transfer:
                try:
                    transfer = int(headers.get("content-length") or 0)
                except ValueError:
                    transfer = len(raw)
            body_bytes = raw[:max_bytes]
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            hop_ms = int((time.perf_counter() - hop_started) * 1000)
            ttfb_ms = int(response.elapsed.total_seconds() * 1000) if response.elapsed else hop_ms
            download_ms = max(hop_ms - ttfb_ms, 0)
            # current is the logical (hostname-based) URL; the actual request went
            # to a pinned IP (see resolve_pinned_target), so response.url isn't
            # useful for reporting here.
            final_url = current
            version = str(getattr(response, "http_version", "") or "")
            protocol = http_protocol(version, headers.get("alt-svc") or "")
            encoding = headers.get("content-encoding") or ""
            uncompressed = len(raw)
            transfer_bytes = transfer or uncompressed
            logger.info(
                "crawl_url_ok url=%s status=%s ttfb_ms=%s protocol=%s encoding=%s",
                final_url,
                response.status_code,
                ttfb_ms,
                protocol,
                encoding or "none",
            )
            return FetchResult(
                url=final_url,
                status_code=response.status_code,
                content_type=content_type,
                body=body_bytes.decode(response.encoding or "utf-8", errors="replace"),
                elapsed_ms=elapsed_ms,
                ttfb_ms=ttfb_ms,
                download_ms=download_ms,
                size_bytes=uncompressed,
                transfer_bytes=transfer_bytes,
                headers=headers,
                redirect_count=max(len(hops) - 1, 0),
                hops=hops,
                redirect_hops=redirect_hops,
                http_version=version,
                http_protocol=protocol,
                timing={
                    "ttfb_ms": ttfb_ms,
                    "download_ms": download_ms,
                    "total_ms": elapsed_ms,
                    "redirect_ms": max(elapsed_ms - hop_ms, 0),
                    "source": "crawl",
                },
            )
    logger.info("crawl_url_failed url=%s error=%s", url, last_error)
    raise SSRFBlocked(last_error)


def fetch_url(url: str, *, timeout: int = 10, max_bytes: int = 2_000_000) -> FetchResult:
    return fetch_document(url, timeout=timeout, max_bytes=max_bytes, allowed_types=ALLOWED_HTML_TYPES, require_type=True)


def fetch_optional(url: str, *, timeout: int = 10, max_bytes: int = 500_000) -> FetchResult | None:
    try:
        return fetch_document(
            url,
            timeout=timeout,
            max_bytes=max_bytes,
            allowed_types=ALLOWED_TEXT_TYPES,
            require_type=False,
        )
    except SSRFBlocked:
        return None


def network_snapshot(result: FetchResult) -> dict:
    headers = result.headers or {}
    encoding = headers.get("content-encoding") or ""
    kind = compression_kind(encoding)
    uncompressed = result.size_bytes or len(result.body.encode("utf-8", errors="replace"))
    compressed = result.transfer_bytes or uncompressed
    if kind == "none":
        compressed = uncompressed
    ratio = None
    if uncompressed > 0 and compressed > 0 and kind != "none":
        ratio = round(max(0.0, min(1.0, 1 - (compressed / uncompressed))), 4)
    hsts = parse_hsts(headers.get("strict-transport-security") or "")
    cache = parse_cache_control(headers.get("cache-control") or "")
    return {
        "elapsed_ms": result.elapsed_ms,
        "ttfb_ms": result.ttfb_ms or result.elapsed_ms,
        "download_ms": result.download_ms,
        "size_bytes": uncompressed,
        "transfer_bytes": compressed,
        "html_size_bytes": uncompressed,
        "compressed_size_bytes": compressed if kind != "none" else uncompressed,
        "compression": kind,
        "compression_ratio": ratio,
        "content_encoding": encoding,
        "redirect_count": result.redirect_count,
        "redirect_hops": result.redirect_hops,
        "hops": result.hops,
        "https": result.url.startswith("https://"),
        "hsts": hsts["present"],
        "hsts_detail": hsts,
        "http_version": result.http_version,
        "http_protocol": result.http_protocol,
        "cache_control": headers.get("cache-control") or "",
        "cache": cache,
        "etag": headers.get("etag") or "",
        "last_modified": headers.get("last-modified") or "",
        "age": headers.get("age") or "",
        "vary": headers.get("vary") or "",
        "server": headers.get("server") or "",
        "cdn": detect_cdn(headers),
        "x_robots_tag": headers.get("x-robots-tag") or "",
        "timing": result.timing or {"ttfb_ms": result.ttfb_ms, "download_ms": result.download_ms, "total_ms": result.elapsed_ms, "source": "crawl"},
        "final_url": result.url,
        "status_code": result.status_code,
        "content_type": result.content_type,
        "alt_svc": headers.get("alt-svc") or "",
        "timing_source": "crawl",
    }
