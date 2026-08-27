from django.urls import path

from apps.markets.views import (
    GeoPlaceDetailView,
    GeoPlaceListView,
    MarketBriefView,
    MarketCollectView,
    MarketFocusListCreateView,
    MarketOverviewView,
    MarketSignalImportView,
    MarketSignalListCreateView,
    ScoringProfileView,
)

urlpatterns = [
    path("overview/", MarketOverviewView.as_view(), name="market-overview"),
    path("brief/", MarketBriefView.as_view(), name="market-brief"),
    path("import/", MarketSignalImportView.as_view(), name="market-import"),
    path("collect/", MarketCollectView.as_view(), name="market-collect"),
    path("places/", GeoPlaceListView.as_view(), name="market-places"),
    path("places/<uuid:id>/", GeoPlaceDetailView.as_view(), name="market-place-detail"),
    path("scoring/", ScoringProfileView.as_view(), name="market-scoring"),
    path("focus/", MarketFocusListCreateView.as_view(), name="market-focus"),
    path("signals/", MarketSignalListCreateView.as_view(), name="market-signals"),
]
