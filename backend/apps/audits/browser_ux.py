from __future__ import annotations

import logging
import os

import httpx

from apps.audits.performance_config import threshold_score
from apps.crawler.ssrf import SSRFBlocked, validate_public_http_url

logger = logging.getLogger("seonet.performance")

PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PROBE_URL = "https://www.google.com/"


def _pagespeed_key() -> str:
    key = (os.getenv("PAGESPEED_API_KEY") or os.getenv("GOOGLE_PAGESPEED_API_KEY") or "").strip()
    if key:
        return key
    try:
        from apps.platform.lead_sources import resolve_source_credentials

        _source, stored = resolve_source_credentials("google_pagespeed")
        return stored
    except Exception:  # noqa: BLE001
        return ""


def probe_pagespeed(api_key: str) -> dict:
    from apps.common.exceptions import APIError

    if not str(api_key or "").strip():
        raise APIError("Store an API key before testing this source.", code="VALIDATION_ERROR")
    try:
        with httpx.Client(timeout=25, follow_redirects=False) as client:
            response = client.get(
                PSI_URL,
                params={"url": PROBE_URL, "key": api_key, "category": "PERFORMANCE", "strategy": "mobile"},
            )
    except Exception as exc:  # noqa: BLE001
        raise APIError("PageSpeed Insights could not be reached.", code="PROVIDER_UNAVAILABLE") from exc
    if response.status_code >= 400:
        raise APIError("PageSpeed Insights rejected this API key.", code="VALIDATION_ERROR")
    payload = response.json() if response.content else {}
    lighthouse = payload.get("lighthouseResult") or {}
    if not lighthouse and not payload.get("loadingExperience"):
        raise APIError("PageSpeed Insights did not return a usable result for this key.", code="VALIDATION_ERROR")
    return {
        "ok": True,
        "sample_count": 1,
        "provider": "google_pagespeed",
        "message": "PageSpeed Insights accepted the key. Lab overlay is available for homepage audits.",
    }


def fetch_lab_metrics(url: str) -> dict | None:
    key = _pagespeed_key()
    if not key:
        return None
    try:
        target = validate_public_http_url(url)
    except SSRFBlocked:
        return None
    try:
        with httpx.Client(timeout=25, follow_redirects=False) as client:
            response = client.get(
                PSI_URL,
                params={"url": target, "key": key, "category": "PERFORMANCE", "strategy": "mobile"},
            )
        if response.status_code >= 400:
            logger.info("pagespeed_unavailable status=%s", response.status_code)
            return None
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.info("pagespeed_failed error=%s", type(exc).__name__)
        return None
    vitals = ((payload.get("loadingExperience") or {}).get("metrics")) or {}
    lighthouse = ((payload.get("lighthouseResult") or {}).get("audits")) or {}
    field = bool(vitals)
    source = "field" if field else "lab"

    def lab_ms(audit_id: str) -> int | None:
        raw = (lighthouse.get(audit_id) or {}).get("numericValue")
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    lcp = lab_ms("largest-contentful-paint")
    inp = lab_ms("interaction-to-next-paint")
    fcp = lab_ms("first-contentful-paint")
    tbt = lab_ms("total-blocking-time")
    si = lab_ms("speed-index")
    cls_raw = (lighthouse.get("cumulative-layout-shift") or {}).get("numericValue")
    try:
        cls = float(cls_raw) if cls_raw is not None else None
    except (TypeError, ValueError):
        cls = None
    from apps.audits.performance_config import DEFAULT_PERFORMANCE_CONFIG

    ux_cfg = DEFAULT_PERFORMANCE_CONFIG["ux"]
    parts = []
    if lcp is not None:
        parts.append(threshold_score(lcp, ux_cfg["lcp_ms"]))
    if inp is not None:
        parts.append(threshold_score(inp, ux_cfg["inp_ms"]))
    if cls is not None:
        parts.append(threshold_score(cls, ux_cfg["cls"]))
    if fcp is not None:
        parts.append(threshold_score(fcp, ux_cfg["fcp_ms"]))
    if tbt is not None:
        parts.append(threshold_score(tbt, ux_cfg["tbt_ms"]))
    if si is not None:
        parts.append(threshold_score(si, ux_cfg["si_ms"]))
    if not parts:
        return None
    return {
        "available": True,
        "source": source,
        "label": "Field Data" if source == "field" else "Browser Lab",
        "score": int(sum(parts) / len(parts)),
        "lcp_ms": lcp,
        "inp_ms": inp,
        "cls": cls,
        "fcp_ms": fcp,
        "tbt_ms": tbt,
        "si_ms": si,
        "note": "Optional PageSpeed Insights overlay. It does not replace Seonet crawl TTFB or the technical score.",
    }


def attach_browser_ux(crawl) -> None:
    homepage = crawl.pages.order_by("created_at").first()
    if homepage is None:
        return
    metrics = fetch_lab_metrics(homepage.url)
    if not metrics:
        return
    extracted = dict(homepage.extracted or {})
    extracted["browser_ux"] = metrics
    homepage.extracted = extracted
    homepage.save(update_fields=["extracted", "updated_at"])
    signals = dict(crawl.signals or {})
    signals["browser_ux"] = {"available": True, "source": metrics["source"], "score": metrics["score"]}
    crawl.signals = signals
    crawl.save(update_fields=["signals", "updated_at"])
