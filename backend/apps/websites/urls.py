from django.urls import path

from apps.websites.views import (
    WebsiteAccessView,
    WebsiteApplyFixesView,
    WebsiteAuditStartView,
    WebsiteDetailView,
    WebsiteFixPlanView,
    WebsiteFixRunDetailView,
    WebsiteFixRunListView,
    WebsiteKeywordRankView,
    WebsiteListCreateView,
    WebsitePerformanceTrendsView,
)

urlpatterns = [
    path("", WebsiteListCreateView.as_view(), name="website-list"),
    path("<uuid:id>/", WebsiteDetailView.as_view(), name="website-detail"),
    path("<uuid:id>/audit/", WebsiteAuditStartView.as_view(), name="website-audit-start"),
    path("<uuid:id>/performance/trends/", WebsitePerformanceTrendsView.as_view(), name="website-performance-trends"),
    path("<uuid:id>/access/", WebsiteAccessView.as_view(), name="website-access"),
    path("<uuid:id>/fix-plan/", WebsiteFixPlanView.as_view(), name="website-fix-plan"),
    path("<uuid:id>/apply-fixes/", WebsiteApplyFixesView.as_view(), name="website-apply-fixes"),
    path("<uuid:id>/fix-runs/", WebsiteFixRunListView.as_view(), name="website-fix-runs"),
    path("<uuid:id>/fix-runs/<uuid:run_id>/", WebsiteFixRunDetailView.as_view(), name="website-fix-run-detail"),
    path("<uuid:id>/keywords/", WebsiteKeywordRankView.as_view(), name="website-keywords"),
]
