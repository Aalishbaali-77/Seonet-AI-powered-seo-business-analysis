from __future__ import annotations

from apps.leads.models import ICP, Lead


def _contains(haystack: str, needles: list[str]) -> bool | None:
    text = (haystack or "").strip().lower()
    items = [item.strip().lower() for item in needles if item and str(item).strip()]
    if not text or not items:
        return None
    return any(item in text or text in item for item in items)


def score_lead(lead: Lead, icp: ICP | None = None) -> dict:
    present = {
        "website": bool(lead.website),
        "email": bool(lead.email),
        "phone": bool(lead.phone),
        "location": bool(lead.location),
        "industry": bool(lead.industry),
    }
    quality = int(round(100 * sum(1 for ok in present.values() if ok) / len(present)))
    missing = [key for key, ok in present.items() if not ok]
    industry_fit = None
    location_fit = None
    if icp is not None:
        matched_industry = _contains(lead.industry, [icp.industry, *(icp.keywords or [])])
        if matched_industry is not None:
            industry_fit = 100 if matched_industry else 0
        matched_location = _contains(lead.location, list(icp.locations or []))
        if matched_location is not None:
            location_fit = 100 if matched_location else 0
    fits = [value for value in (industry_fit, location_fit) if value is not None]
    icp_fit = int(round(sum(fits) / len(fits))) if fits else None
    parts = [quality]
    if icp_fit is not None:
        parts.append(icp_fit)
    lead_score = int(round(sum(parts) / len(parts)))
    return {
        "quality_score": quality,
        "industry_fit": industry_fit,
        "location_fit": location_fit,
        "icp_fit": icp_fit,
        "lead_score": lead_score,
        "opportunity_score": lead.opportunity_score,
        "missing_fields": missing,
        "origin": "fact",
        "why": "Quality is field completeness. Fit scores compare this lead to a confirmed ICP. Missing contact values are not invented.",
    }


def apply_lead_score(lead: Lead, icp: ICP | None = None) -> Lead:
    payload = score_lead(lead, icp)
    lead.quality_score = payload["quality_score"]
    lead.industry_fit = payload["industry_fit"]
    lead.location_fit = payload["location_fit"]
    lead.icp_fit = payload["icp_fit"]
    lead.lead_score = payload["lead_score"]
    lead.save(
        update_fields=["quality_score", "industry_fit", "location_fit", "icp_fit", "lead_score", "updated_at"]
    )
    return lead
