from django.urls import path

from apps.usage.views import UsageListView, UsageSummaryView

urlpatterns = [
    path("", UsageListView.as_view(), name="usage-list"),
    path("summary/", UsageSummaryView.as_view(), name="usage-summary"),
]
