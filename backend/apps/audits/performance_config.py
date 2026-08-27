from __future__ import annotations

from copy import deepcopy

from django.conf import settings

DEFAULT_PERFORMANCE_CONFIG: dict = {
    "weights": {
        "technical": 0.6,
        "ux": 0.4,
        "ttfb": 0.20,
        "response_time": 0.10,
        "html_size": 0.10,
        "compression": 0.10,
        "redirects": 0.10,
        "caching": 0.10,
        "resource_weight": 0.10,
        "protocol": 0.05,
        "errors": 0.10,
        "cdn": 0.05,
    },
    "bands": {
        "excellent": 90,
        "good": 75,
        "needs_improvement": 50,
    },
    "ttfb_ms": {"excellent": 200, "good": 500, "needs_improvement": 800, "poor": 1800},
    "html_bytes": {"excellent": 100_000, "good": 200_000, "needs_improvement": 500_000, "poor": 1_000_000},
    "response_ms": {"excellent": 400, "good": 800, "needs_improvement": 1500, "poor": 3000},
    "js_files": {"good": 8, "needs_improvement": 15, "poor": 25},
    "third_party": {"good": 6, "needs_improvement": 12, "poor": 20},
    "regression": {
        "ttfb_pct": 20,
        "html_pct": 25,
        "js_pct": 20,
        "score_points": 5,
        "cwv_points": 5,
    },
    "ux": {
        "lcp_ms": {"good": 2500, "poor": 4000},
        "inp_ms": {"good": 200, "poor": 500},
        "cls": {"good": 0.1, "poor": 0.25},
        "fcp_ms": {"good": 1800, "poor": 3000},
        "tbt_ms": {"good": 200, "poor": 600},
        "si_ms": {"good": 3400, "poor": 5800},
    },
}


def _merge(base: dict, override: dict | None) -> dict:
    merged = deepcopy(base)
    if not override:
        return merged
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def resolve_performance_config(website=None) -> dict:
    settings_override = getattr(settings, "PERFORMANCE_THRESHOLDS", None) or {}
    site_override = {}
    if website is not None:
        site_override = ((website.audit_config or {}).get("performance") or {})
    return _merge(_merge(DEFAULT_PERFORMANCE_CONFIG, settings_override), site_override)


def band_label(score: int | None, cfg: dict | None = None) -> str:
    if score is None:
        return "Unavailable"
    bands = (cfg or DEFAULT_PERFORMANCE_CONFIG)["bands"]
    if score >= int(bands["excellent"]):
        return "Excellent"
    if score >= int(bands["good"]):
        return "Good"
    if score >= int(bands["needs_improvement"]):
        return "Needs Improvement"
    return "Poor"


def threshold_score(value: float | int | None, steps: dict, *, higher_is_worse: bool = True) -> int:
    if value is None:
        return 70
    numeric = float(value)
    excellent = float(steps.get("excellent") or steps.get("good") or 0)
    good = float(steps.get("good") or excellent)
    needs = float(steps.get("needs_improvement") or good)
    poor = float(steps.get("poor") or needs * 2)
    if not higher_is_worse:
        if numeric >= excellent:
            return 100
        if numeric >= good:
            return 88
        if numeric >= needs:
            return 62
        if numeric >= poor:
            return 35
        return 12
    if numeric <= excellent:
        return 100
    if numeric <= good:
        return 85
    if numeric <= needs:
        return 62
    if numeric <= poor:
        return 35
    return 12
