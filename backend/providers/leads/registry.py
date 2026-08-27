from apps.platform.models import LeadSource
from providers.leads.adapters import (
    FoursquareAdapter,
    GeoapifyAdapter,
    HttpJsonLeadAdapter,
    LinkedInSalesAdapter,
    NpiRegistryAdapter,
    OpenCorporatesAdapter,
    OpenStreetMapAdapter,
    YelpAdapter,
)
from providers.leads.google_places import GooglePlacesAdapter


def build_adapter(source: LeadSource):
    provider = source.provider
    if provider == LeadSource.Provider.GOOGLE_PLACES:
        return GooglePlacesAdapter()
    if provider == LeadSource.Provider.YELP:
        return YelpAdapter()
    if provider == LeadSource.Provider.FOURSQUARE:
        return FoursquareAdapter()
    if provider == LeadSource.Provider.GEOAPIFY:
        return GeoapifyAdapter()
    if provider == LeadSource.Provider.OPENSTREETMAP:
        return OpenStreetMapAdapter()
    if provider == LeadSource.Provider.OPENCORPORATES:
        return OpenCorporatesAdapter()
    if provider == LeadSource.Provider.NPI_REGISTRY:
        return NpiRegistryAdapter()
    if provider == LeadSource.Provider.LINKEDIN_SALES_NAVIGATOR:
        return LinkedInSalesAdapter(search_url=str((source.public_config or {}).get("search_url") or ""))
    return HttpJsonLeadAdapter(source)
