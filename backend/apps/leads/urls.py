from django.urls import path

from apps.leads.views import (
    ICPConfirmView,
    ICPListCreateView,
    LeadDetailView,
    LeadBulkEnrichView,
    LeadEnrichView,
    LeadExportView,
    LeadListCollectionView,
    LeadListCreateView,
    LeadListDetailView,
    LeadListMembersView,
    LeadScoreView,
    LeadSearchListView,
    LeadSearchStartView,
)

urlpatterns = [
    path("icps/", ICPListCreateView.as_view(), name="icp-list"),
    path("icps/<uuid:id>/confirm/", ICPConfirmView.as_view(), name="icp-confirm"),
    path("searches/", LeadSearchListView.as_view(), name="lead-search-list"),
    path("searches/start/", LeadSearchStartView.as_view(), name="lead-search-start"),
    path("lists/", LeadListCollectionView.as_view(), name="lead-list-collection"),
    path("lists/<uuid:id>/", LeadListDetailView.as_view(), name="lead-list-detail"),
    path("lists/<uuid:id>/members/", LeadListMembersView.as_view(), name="lead-list-members"),
    path("score/", LeadScoreView.as_view(), name="lead-score"),
    path("export/", LeadExportView.as_view(), name="lead-export"),
    path("enrich/", LeadBulkEnrichView.as_view(), name="lead-enrich-bulk"),
    path("", LeadListCreateView.as_view(), name="lead-list"),
    path("<uuid:id>/enrich/", LeadEnrichView.as_view(), name="lead-enrich"),
    path("<uuid:id>/", LeadDetailView.as_view(), name="lead-detail"),
]
