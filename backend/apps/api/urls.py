from django.urls import include, path

from apps.core.dashboard import DashboardOverviewView, WorkspaceReportsExportView, WorkspaceReportsView

urlpatterns = [
    path("", include("apps.core.urls")),
    path("auth/", include("apps.users.urls")),
    path("tenants/", include("apps.tenants.urls")),
    path("", include("apps.rbac.urls")),
    path("jobs/", include("apps.jobs.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("dashboard/overview/", DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("reports/", WorkspaceReportsView.as_view(), name="workspace-reports"),
    path("reports/export/", WorkspaceReportsExportView.as_view(), name="workspace-reports-export"),
    path("websites/", include("apps.websites.urls")),
    path("audits/", include("apps.audits.urls")),
    path("leads/", include("apps.leads.urls")),
    path("business/", include("apps.business.urls")),
    path("markets/", include("apps.markets.urls")),
    path("opportunities/", include("apps.opportunities.urls")),
    path("marketing/", include("apps.marketing.urls")),
    path("crm/", include("apps.crm.urls")),
    path("integrations/", include("apps.integrations.urls")),
    path("usage/", include("apps.usage.urls")),
    path("billing/", include("apps.billing.urls")),
    path("ai/", include("apps.ai.urls")),
    path("telemetry/page/", include("apps.auditlog.urls")),
    path("platform/", include("apps.platform.urls")),
]
