from django.urls import path

from apps.core.views import HealthView, LiveView, PublicConfigView, ReadyView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("health/live/", LiveView.as_view(), name="health-live"),
    path("health/ready/", ReadyView.as_view(), name="health-ready"),
    path("config/", PublicConfigView.as_view(), name="public-config"),
]
