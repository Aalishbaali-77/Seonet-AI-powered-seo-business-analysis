from django.urls import path

from apps.integrations.views import (
    IntegrationDetailView,
    IntegrationListView,
    IntegrationSyncView,
    IntegrationTestView,
    WebhookRotateView,
)

urlpatterns = [
    path("", IntegrationListView.as_view(), name="integration-list"),
    path("webhook/rotate/", WebhookRotateView.as_view(), name="integration-webhook-rotate"),
    path("<slug:provider>/test/", IntegrationTestView.as_view(), name="integration-test"),
    path("<slug:provider>/sync/", IntegrationSyncView.as_view(), name="integration-sync"),
    path("<slug:provider>/", IntegrationDetailView.as_view(), name="integration-detail"),
]
