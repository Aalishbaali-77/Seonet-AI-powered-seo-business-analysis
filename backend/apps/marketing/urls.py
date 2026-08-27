from django.urls import path

from apps.marketing.views import (
    CampaignAudienceExportView,
    CampaignDetailView,
    CampaignListCreateView,
    CampaignPreviewView,
    CampaignSendView,
)

urlpatterns = [
    path("campaigns/", CampaignListCreateView.as_view(), name="marketing-campaigns"),
    path("campaigns/<uuid:id>/", CampaignDetailView.as_view(), name="marketing-campaign-detail"),
    path("campaigns/<uuid:id>/send/", CampaignSendView.as_view(), name="marketing-campaign-send"),
    path("audiences/preview/", CampaignPreviewView.as_view(), name="marketing-audience-preview"),
    path("audiences/export/", CampaignAudienceExportView.as_view(), name="marketing-audience-export"),
]
