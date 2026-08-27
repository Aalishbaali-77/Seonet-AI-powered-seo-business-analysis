from django.urls import path

from apps.integrations.views import TenantApiTokenDetailView, TenantApiTokenListView
from apps.tenants.views import TenantDetailView, TenantListView, TenantMemberDetailView, TenantMemberListView

urlpatterns = [
    path("", TenantListView.as_view(), name="tenant-list"),
    path("<uuid:id>/", TenantDetailView.as_view(), name="tenant-detail"),
    path("<uuid:id>/members/", TenantMemberListView.as_view(), name="tenant-members"),
    path("<uuid:id>/members/<uuid:member_id>/", TenantMemberDetailView.as_view(), name="tenant-member-detail"),
    path("<uuid:id>/api-tokens/", TenantApiTokenListView.as_view(), name="tenant-api-tokens"),
    path("<uuid:id>/api-tokens/<uuid:token_id>/", TenantApiTokenDetailView.as_view(), name="tenant-api-token-detail"),
]
