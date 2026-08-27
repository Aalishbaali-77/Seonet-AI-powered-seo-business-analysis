from django.urls import path

from apps.crm.views import (
    ActivityDetailView,
    ActivityListCreateView,
    CompanyDetailView,
    CompanyListCreateView,
    ContactDetailView,
    ContactListCreateView,
    CrmAssigneeListView,
    CrmExportView,
    CrmFunnelView,
    DealDetailView,
    DealListCreateView,
    PipelineDetailView,
    PipelineListCreateView,
    StageDetailView,
    StageListCreateView,
)

urlpatterns = [
    path("pipelines/", PipelineListCreateView.as_view(), name="crm-pipelines"),
    path("pipelines/<uuid:id>/", PipelineDetailView.as_view(), name="crm-pipeline-detail"),
    path("pipelines/<uuid:pipeline_id>/stages/", StageListCreateView.as_view(), name="crm-stages"),
    path("pipelines/<uuid:pipeline_id>/stages/<uuid:id>/", StageDetailView.as_view(), name="crm-stage-detail"),
    path("export/", CrmExportView.as_view(), name="crm-export"),
    path("assignees/", CrmAssigneeListView.as_view(), name="crm-assignees"),
    path("funnel/", CrmFunnelView.as_view(), name="crm-funnel"),
    path("companies/", CompanyListCreateView.as_view(), name="crm-companies"),
    path("companies/<uuid:id>/", CompanyDetailView.as_view(), name="crm-company-detail"),
    path("contacts/", ContactListCreateView.as_view(), name="crm-contacts"),
    path("contacts/<uuid:id>/", ContactDetailView.as_view(), name="crm-contact-detail"),
    path("deals/", DealListCreateView.as_view(), name="crm-deals"),
    path("deals/<uuid:id>/", DealDetailView.as_view(), name="crm-deal-detail"),
    path("activities/", ActivityListCreateView.as_view(), name="crm-activities"),
    path("activities/<uuid:id>/", ActivityDetailView.as_view(), name="crm-activity-detail"),
]
