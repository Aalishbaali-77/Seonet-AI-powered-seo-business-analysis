from django.urls import path

from apps.business.views import (
    BusinessAnalyzeView,
    BusinessImportView,
    BusinessOverviewView,
    BusinessProfileView,
    CustomerListView,
    ImportBatchDetailView,
    ImportBatchListView,
    OrderDetailView,
    OrderListView,
    ProductListCreateView,
    PromoteCustomersView,
    ReviewListView,
    StoreDetailView,
    StoreListView,
    StoreSyncView,
    StoreTestView,
)

urlpatterns = [
    path("overview/", BusinessOverviewView.as_view(), name="business-overview"),
    path("profile/", BusinessProfileView.as_view(), name="business-profile"),
    path("products/", ProductListCreateView.as_view(), name="business-products"),
    path("customers/promote/", PromoteCustomersView.as_view(), name="business-customers-promote"),
    path("customers/", CustomerListView.as_view(), name="business-customers"),
    path("orders/", OrderListView.as_view(), name="business-orders"),
    path("orders/<uuid:id>/", OrderDetailView.as_view(), name="business-order-detail"),
    path("reviews/", ReviewListView.as_view(), name="business-reviews"),
    path("analyze/", BusinessAnalyzeView.as_view(), name="business-analyze"),
    path("import/", BusinessImportView.as_view(), name="business-import"),
    path("imports/", ImportBatchListView.as_view(), name="business-imports"),
    path("imports/<uuid:id>/", ImportBatchDetailView.as_view(), name="business-import-detail"),
    path("stores/", StoreListView.as_view(), name="business-stores"),
    path("stores/<slug:provider>/test/", StoreTestView.as_view(), name="business-store-test"),
    path("stores/<slug:provider>/sync/", StoreSyncView.as_view(), name="business-store-sync"),
    path("stores/<slug:provider>/", StoreDetailView.as_view(), name="business-store-detail"),
]
