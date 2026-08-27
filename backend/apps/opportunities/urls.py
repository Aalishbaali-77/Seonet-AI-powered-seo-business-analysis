from django.urls import path

from apps.opportunities.views import OpportunityDetailView, OpportunityGenerateView, OpportunityListCreateView

urlpatterns = [
    path("generate/", OpportunityGenerateView.as_view(), name="opportunity-generate"),
    path("", OpportunityListCreateView.as_view(), name="opportunity-list"),
    path("<uuid:id>/", OpportunityDetailView.as_view(), name="opportunity-detail"),
]
