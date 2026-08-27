from django.urls import path

from apps.audits.views import (
    AuditDetailView,
    AuditIssueDetailView,
    AuditIssueListView,
    AuditListView,
    AuditPageDetailView,
    AuditPageExportView,
    AuditPageListView,
    AuditPerformanceCompareView,
    AuditPerformanceView,
    AuditRecommendationListView,
    AuditReportView,
)

urlpatterns = [
    path("", AuditListView.as_view(), name="audit-list"),
    path("<uuid:id>/", AuditDetailView.as_view(), name="audit-detail"),
    path("<uuid:id>/report/", AuditReportView.as_view(), name="audit-report"),
    path("<uuid:id>/issues/", AuditIssueListView.as_view(), name="audit-issues"),
    path("<uuid:id>/issues/<uuid:issue_id>/", AuditIssueDetailView.as_view(), name="audit-issue-detail"),
    path("<uuid:id>/recommendations/", AuditRecommendationListView.as_view(), name="audit-recommendations"),
    path("<uuid:id>/performance/", AuditPerformanceView.as_view(), name="audit-performance"),
    path("<uuid:id>/pages/", AuditPageListView.as_view(), name="audit-pages"),
    path("<uuid:id>/pages/export/", AuditPageExportView.as_view(), name="audit-pages-export"),
    path("<uuid:id>/pages/<uuid:page_id>/", AuditPageDetailView.as_view(), name="audit-page-detail"),
    path("<uuid:id>/compare/", AuditPerformanceCompareView.as_view(), name="audit-performance-compare"),
]
