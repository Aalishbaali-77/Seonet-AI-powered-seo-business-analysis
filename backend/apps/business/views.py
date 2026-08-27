from django.http import HttpResponse
from rest_framework import generics, permissions
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditlog.services import write_audit
from apps.business.analysis import commerce_analysis
from apps.business.imports import csv_template, start_csv_import
from apps.business.kpis import commerce_kpis
from apps.business.models import BusinessProfile, CatalogProduct, CommerceCustomer, CommerceOrder, CommerceReview, ImportBatch
from apps.business.serializers import BusinessProfileSerializer, CatalogProductSerializer, CommerceCustomerSerializer, CommerceOrderSerializer, CommerceReviewSerializer, ImportBatchSerializer
from apps.common.exceptions import APIError
from apps.common.permissions import HasPermissionCode, HasTenant


class BusinessModule:
    required_module = "business"


def _profile(tenant) -> BusinessProfile:
    profile = BusinessProfile.objects.for_tenant(tenant).first()
    if profile is None:
        profile = BusinessProfile.objects.create(tenant=tenant)
    return profile


class BusinessOverviewView(BusinessModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "business.view"

    def get(self, request):
        profile = _profile(request.tenant)
        return Response(
            {
                "profile": BusinessProfileSerializer(profile).data,
                "kpis": commerce_kpis(request.tenant),
                "analysis": commerce_analysis(request.tenant),
                "expert": profile.last_expert or {},
            }
        )


class BusinessProfileView(BusinessModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]

    @property
    def required_permission(self):
        return "business.manage" if self.request.method in {"PUT", "PATCH"} else "business.view"

    def get(self, request):
        return Response(BusinessProfileSerializer(_profile(request.tenant)).data)

    def put(self, request):
        serializer = BusinessProfileSerializer(_profile(request.tenant), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        return self.put(request)


class ProductListCreateView(BusinessModule, generics.ListCreateAPIView):
    serializer_class = CatalogProductSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    search_fields = ("name", "sku", "category")

    @property
    def required_permission(self):
        return "business.manage" if self.request.method == "POST" else "business.view"

    def get_queryset(self):
        return CatalogProduct.objects.for_tenant(self.request.tenant).order_by("name")


class CustomerListView(BusinessModule, generics.ListAPIView):
    serializer_class = CommerceCustomerSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "business.view"
    search_fields = ("name", "city", "email")

    def get_queryset(self):
        return CommerceCustomer.objects.for_tenant(self.request.tenant).order_by("name")


class OrderListView(BusinessModule, generics.ListAPIView):
    serializer_class = CommerceOrderSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "business.view"

    def get_queryset(self):
        return CommerceOrder.objects.for_tenant(self.request.tenant).select_related("customer").prefetch_related("items").order_by("-ordered_at", "-created_at")


class OrderDetailView(BusinessModule, generics.RetrieveUpdateAPIView):
    serializer_class = CommerceOrderSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    lookup_field = "id"

    @property
    def required_permission(self):
        return "business.manage" if self.request.method in {"PUT", "PATCH"} else "business.view"

    def get_queryset(self):
        return CommerceOrder.objects.for_tenant(self.request.tenant).select_related("customer").prefetch_related("items")

    def perform_update(self, serializer):
        order = serializer.save()
        write_audit(
            action="BUSINESS_ORDER_UPDATED",
            request=self.request,
            resource_type="order",
            resource_id=order.id,
            metadata={"status": order.status, "city": order.city, "channel": order.channel},
        )


class BusinessImportView(BusinessModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @property
    def required_permission(self):
        return "business.manage" if self.request.method == "POST" else "business.view"

    def get(self, request):
        kind = (request.query_params.get("kind") or "products").strip()
        try:
            filename, content = csv_template(kind)
        except ValueError:
            raise APIError("Download the products or orders template.", code="VALIDATION_ERROR")
        response = HttpResponse(content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def post(self, request):
        from apps.jobs.serializers import JobSerializer

        kind = (request.data.get("kind") or "products").strip()
        upload = request.FILES.get("file")
        if upload is None:
            raise APIError("Upload a CSV file.", code="VALIDATION_ERROR")
        job = start_csv_import(tenant=request.tenant, user=request.user, kind=kind, raw=upload.read(), file_name=upload.name or "")
        return Response(JobSerializer(job).data, status=202)


class ImportBatchListView(BusinessModule, generics.ListAPIView):
    serializer_class = ImportBatchSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "business.view"

    def get_queryset(self):
        return ImportBatch.objects.for_tenant(self.request.tenant).order_by("-created_at")


class ImportBatchDetailView(BusinessModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "business.manage"

    def delete(self, request, id):
        batch = ImportBatch.objects.for_tenant(request.tenant).filter(id=id).first()
        if batch is None:
            raise APIError("Import not found.", code="NOT_FOUND", status_code=404)
        mode = (request.query_params.get("mode") or "").strip()
        if mode not in {"log_only", "log_and_rows"}:
            raise APIError(
                "Choose how to remove this import: log_only (keep imported rows) or log_and_rows (remove rows too).",
                code="VALIDATION_ERROR",
            )
        rows_removed = 0
        if mode == "log_and_rows":
            rows_removed = CommerceOrder.objects.for_tenant(request.tenant).filter(import_batch=batch).delete()
        write_audit(
            action="BUSINESS_IMPORT_DELETED",
            request=request,
            resource_type="import_batch",
            resource_id=batch.id,
            metadata={"mode": mode, "file_name": batch.file_name, "rows_removed": rows_removed},
        )
        batch.delete()
        return Response({"deleted": True, "mode": mode, "rows_removed": rows_removed})


class ReviewListView(BusinessModule, generics.ListAPIView):
    serializer_class = CommerceReviewSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "business.view"

    def get_queryset(self):
        return CommerceReview.objects.for_tenant(self.request.tenant).select_related("product").order_by("-created_at")


class StoreListView(BusinessModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "business.view"

    def get(self, request):
        from apps.integrations.services import list_commerce_stores

        return Response({"items": list_commerce_stores(request.tenant)})


class StoreDetailView(BusinessModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "business.manage"

    def put(self, request, provider: str):
        from apps.billing.entitlements import tenant_module_codes
        from apps.business.stores import COMMERCE_PROVIDERS
        from apps.integrations.catalog import PROVIDER_BY_CODE
        from apps.integrations.services import save_integration, serialize_connection

        if provider not in COMMERCE_PROVIDERS:
            raise APIError("Unknown store.", code="NOT_FOUND", status_code=404)
        connection, revealed = save_integration(request.tenant, provider, request.data if isinstance(request.data, dict) else {})
        payload = serialize_connection(PROVIDER_BY_CODE[provider], connection, modules=tenant_module_codes(request.tenant))
        if revealed:
            payload["revealed"] = revealed
        return Response(payload)

    def delete(self, request, provider: str):
        from apps.billing.entitlements import tenant_module_codes
        from apps.business.stores import COMMERCE_PROVIDERS
        from apps.integrations.catalog import PROVIDER_BY_CODE
        from apps.integrations.services import disconnect_integration, serialize_connection

        if provider not in COMMERCE_PROVIDERS:
            raise APIError("Unknown store.", code="NOT_FOUND", status_code=404)
        connection = disconnect_integration(request.tenant, provider)
        return Response(serialize_connection(PROVIDER_BY_CODE[provider], connection, modules=tenant_module_codes(request.tenant)))


class StoreTestView(BusinessModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "business.manage"

    def post(self, request, provider: str):
        from apps.billing.entitlements import tenant_module_codes
        from apps.business.stores import COMMERCE_PROVIDERS
        from apps.integrations.catalog import PROVIDER_BY_CODE
        from apps.integrations.services import serialize_connection, test_integration

        if provider not in COMMERCE_PROVIDERS:
            raise APIError("Unknown store.", code="NOT_FOUND", status_code=404)
        connection = test_integration(request.tenant, provider)
        return Response(serialize_connection(PROVIDER_BY_CODE[provider], connection, modules=tenant_module_codes(request.tenant)))


class StoreSyncView(BusinessModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "business.manage"

    def post(self, request, provider: str):
        from apps.business.sync import start_store_sync
        from apps.jobs.serializers import JobSerializer

        job = start_store_sync(tenant=request.tenant, user=request.user, provider=provider)
        return Response(JobSerializer(job).data, status=202)


class PromoteCustomersView(BusinessModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "business.manage"

    def post(self, request):
        from apps.business.sync import promote_customers_to_leads

        return Response(promote_customers_to_leads(request.tenant))


class BusinessAnalyzeView(BusinessModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]

    @property
    def required_permission(self):
        return "business.manage" if self.request.method == "POST" else "business.view"

    def get(self, request):
        profile = _profile(request.tenant)
        return Response(
            {
                "analysis": commerce_analysis(request.tenant),
                "expert": profile.last_expert or {},
            }
        )

    def post(self, request):
        from apps.business.analysis import start_business_analysis
        from apps.jobs.serializers import JobSerializer

        job = start_business_analysis(tenant=request.tenant, user=request.user)
        return Response(JobSerializer(job).data, status=202)
