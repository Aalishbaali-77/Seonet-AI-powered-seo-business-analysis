from __future__ import annotations

DEFAULT_WEIGHTS: dict[str, int] = {
    "demand": 25,
    "target_category": 20,
    "purchasing_power": 15,
    "population": 10,
    "competition_gap": 10,
    "business_density": 10,
    "growth_signals": 5,
    "search_interest": 5,
}


def tenant_weights(tenant) -> dict[str, int]:
    from apps.markets.models import ScoringProfile

    profile = ScoringProfile.objects.for_tenant(tenant).first()
    return normalize_weights(profile.weights if profile else DEFAULT_WEIGHTS)


def normalize_weights(raw: dict | None) -> dict[str, int]:
    cleaned: dict[str, int] = {}
    for key, default in DEFAULT_WEIGHTS.items():
        try:
            value = int(raw.get(key) if isinstance(raw, dict) else default)
        except (TypeError, ValueError):
            value = default
        cleaned[key] = max(0, min(100, value))
    total = sum(cleaned.values())
    if total == 0:
        return dict(DEFAULT_WEIGHTS)
    if total == 100:
        return cleaned
    scaled = {key: round(value * 100 / total) for key, value in cleaned.items()}
    drift = 100 - sum(scaled.values())
    first = next(iter(scaled))
    scaled[first] = max(0, scaled[first] + drift)
    return scaled


def score_from_signals(signals, weights: dict[str, int] | None = None) -> dict:
    weights = normalize_weights(weights)
    by_kind: dict[str, list[int]] = {}
    for item in signals:
        if getattr(item, "verification_status", "") == "stale":
            continue
        kind = getattr(item, "kind", None)
        value = getattr(item, "value", None)
        if kind not in weights or value is None:
            continue
        by_kind.setdefault(kind, []).append(int(value))
    parts: dict[str, int | None] = {}
    missing: list[str] = []
    for key in weights:
        values = by_kind.get(key) or []
        if not values:
            parts[key] = None
            missing.append(key)
        else:
            parts[key] = int(round(sum(values) / len(values)))
    available = sum(weights[key] for key in weights if parts[key] is not None)
    if available == 0:
        return {
            "score": None,
            "parts": parts,
            "coverage": 0,
            "missing": missing,
            "origin": "none",
            "why": "No market signals ingested for this place. Scores are not invented.",
        }
    weighted = sum((parts[key] or 0) * weights[key] for key in weights if parts[key] is not None)
    score = int(round(weighted / available))
    origin = "data" if not missing else "estimated"
    why = (
        f"Opportunity score {score}/100 from ingested signals covering {available}% of configured weights."
        if not missing
        else f"Partial score {score}/100. Missing signals: {', '.join(missing)}. Not a full market grade."
    )
    return {"score": score, "parts": parts, "coverage": available, "missing": missing, "origin": origin, "why": why}
