from django.urls import path

from apps.jobs.views import JobCancelView, JobDetailView, JobListView

urlpatterns = [
    path("", JobListView.as_view(), name="job-list"),
    path("<uuid:id>/", JobDetailView.as_view(), name="job-detail"),
    path("<uuid:id>/cancel/", JobCancelView.as_view(), name="job-cancel"),
]
