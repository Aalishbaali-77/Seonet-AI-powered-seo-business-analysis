from django.urls import path

from apps.auditlog.views import PageViewCreateView

urlpatterns = [
    path("", PageViewCreateView.as_view(), name="telemetry-page"),
]
