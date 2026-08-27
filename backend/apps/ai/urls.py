from django.urls import path

from apps.ai.views import AdvisorView, AIUsageView, QueryView

urlpatterns = [
    path("usage/", AIUsageView.as_view(), name="ai-usage"),
    path("advisor/", AdvisorView.as_view(), name="ai-advisor"),
    path("query/", QueryView.as_view(), name="ai-query"),
]
