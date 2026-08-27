from __future__ import annotations

from apps.business.models import CommerceCustomer
from apps.leads.models import Lead, LeadList
from apps.opportunities.models import Opportunity


def audience_rows(tenant, *, audience_type: str, lead_list_id=None, city: str = "", opportunity_id=None) -> list[dict]:
    if audience_type == "lead_list":
        item = LeadList.objects.for_tenant(tenant).filter(id=lead_list_id).first() if lead_list_id else None
        if item is None:
            return []
        return [
            {
                "name": lead.company_name,
                "email": lead.email,
                "phone": lead.phone,
                "location": lead.location,
                "source": "lead_list",
            }
            for lead in Lead.objects.for_tenant(tenant).filter(lists=item)
        ]
    if audience_type == "commerce_city":
        place = (city or "").strip()
        if not place:
            return []
        return [
            {
                "name": row.name,
                "email": row.email,
                "phone": "",
                "location": row.city,
                "source": "commerce_city",
            }
            for row in CommerceCustomer.objects.for_tenant(tenant).filter(city__iexact=place)
        ]
    if audience_type == "opportunity":
        item = Opportunity.objects.for_tenant(tenant).filter(id=opportunity_id).first() if opportunity_id else None
        if item is None:
            return []
        return [
            {
                "name": lead.company_name,
                "email": lead.email,
                "phone": lead.phone,
                "location": lead.location,
                "source": "opportunity",
            }
            for lead in Lead.objects.for_tenant(tenant).filter(growth_opportunities=item)
        ]
    return []


def audience_count(tenant, *, audience_type: str, lead_list_id=None, city: str = "", opportunity_id=None) -> dict:
    if audience_type == "lead_list":
        item = LeadList.objects.for_tenant(tenant).filter(id=lead_list_id).first() if lead_list_id else None
        count = Lead.objects.for_tenant(tenant).filter(lists=item).count() if item else 0
        return {
            "count": count,
            "label": item.name if item else "No lead list selected",
            "origin": "fact",
            "why": "Count is members of an existing Seonet lead list. No contacts are invented.",
        }
    if audience_type == "commerce_city":
        place = (city or "").strip()
        count = CommerceCustomer.objects.for_tenant(tenant).filter(city__iexact=place).count() if place else 0
        return {
            "count": count,
            "label": place or "No city selected",
            "origin": "fact",
            "why": "Count is imported first-party customers with that city. Open rates are not estimated.",
        }
    if audience_type == "opportunity":
        item = Opportunity.objects.for_tenant(tenant).filter(id=opportunity_id).first() if opportunity_id else None
        count = Lead.objects.for_tenant(tenant).filter(growth_opportunities=item).count() if item else 0
        return {
            "count": count,
            "label": item.title if item else "No opportunity selected",
            "origin": "fact",
            "why": "Count is leads already linked to that opportunity. Discovery stays in the Leads module.",
        }
    return {"count": 0, "label": "", "origin": "none", "why": "Unknown audience type."}
