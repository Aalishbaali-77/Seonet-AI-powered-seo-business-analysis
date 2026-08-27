import csv

from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditlog.services import write_audit
from apps.common.exceptions import APIError
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.crm.models import Activity, Company, Contact, Deal, Pipeline, Stage
from apps.crm.serializers import (
    ActivitySerializer,
    CompanySerializer,
    ContactSerializer,
    DealSerializer,
    PipelineSerializer,
    StageSerializer,
)
from apps.tenants.models import Membership


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _falsy(value) -> bool:
    return str(value or "").strip().lower() in {"0", "false", "no"}


def _audit_delete(request, instance):
    write_audit(
        action=f"CRM_{instance.__class__.__name__.upper()}_DELETED",
        request=request,
        tenant=request.tenant,
        resource_type=instance.__class__.__name__.lower(),
        resource_id=instance.id,
    )


class TenantCrmMixin:
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_module = "crm"

    def get_queryset(self):
        return self.queryset_model.objects.for_tenant(self.request.tenant)

    def perform_destroy(self, instance):
        _audit_delete(self.request, instance)
        instance.delete()


class PipelineListCreateView(TenantCrmMixin, generics.ListCreateAPIView):
    serializer_class = PipelineSerializer
    queryset_model = Pipeline
    pagination_class = None

    @property
    def required_permission(self):
        return "crm.create" if self.request.method == "POST" else "crm.view"

    def get_queryset(self):
        return Pipeline.objects.for_tenant(self.request.tenant).prefetch_related("stages")


class PipelineDetailView(TenantCrmMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PipelineSerializer
    queryset_model = Pipeline
    lookup_field = "id"

    @property
    def required_permission(self):
        if self.request.method == "DELETE":
            return "crm.delete"
        if self.request.method in {"PUT", "PATCH"}:
            return "crm.update"
        return "crm.view"

    def get_queryset(self):
        return Pipeline.objects.for_tenant(self.request.tenant).prefetch_related("stages")

    def perform_destroy(self, instance):
        if instance.is_default:
            raise APIError("Set another default pipeline before deleting this one.", code="VALIDATION_ERROR")
        if instance.deals.exists():
            raise APIError("Move or delete deals on this pipeline before deleting it.", code="VALIDATION_ERROR")
        _audit_delete(self.request, instance)
        instance.delete()


class StageListCreateView(TenantCrmMixin, generics.ListCreateAPIView):
    serializer_class = StageSerializer
    queryset_model = Stage
    pagination_class = None

    @property
    def required_permission(self):
        return "crm.create" if self.request.method == "POST" else "crm.view"

    def get_queryset(self):
        return Stage.objects.for_tenant(self.request.tenant).filter(pipeline_id=self.kwargs["pipeline_id"])

    def perform_create(self, serializer):
        pipeline = Pipeline.objects.for_tenant(self.request.tenant).filter(id=self.kwargs["pipeline_id"]).first()
        if pipeline is None:
            raise APIError("Resource not found.", code="NOT_FOUND", status_code=404)
        serializer.save(pipeline=pipeline, tenant=self.request.tenant)


class StageDetailView(TenantCrmMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StageSerializer
    queryset_model = Stage
    lookup_field = "id"

    @property
    def required_permission(self):
        if self.request.method == "DELETE":
            return "crm.delete"
        if self.request.method in {"PUT", "PATCH"}:
            return "crm.update"
        return "crm.view"

    def get_queryset(self):
        return Stage.objects.for_tenant(self.request.tenant).filter(pipeline_id=self.kwargs["pipeline_id"])

    def perform_destroy(self, instance):
        if instance.deals.exists():
            raise APIError("Move deals off this stage before deleting it.", code="VALIDATION_ERROR")
        if instance.pipeline.stages.count() <= 1:
            raise APIError("A pipeline needs at least one stage.", code="VALIDATION_ERROR")
        _audit_delete(self.request, instance)
        instance.delete()


class CrmExportView(TenantCrmMixin, APIView):
    required_permission = "crm.view"

    def get(self, request):
        kind = (request.query_params.get("kind") or "deals").strip().lower()
        writers = {
            "companies": (
                "sipulse-crm-companies.csv",
                ["name", "domain", "industry", "location", "phone", "email", "owner"],
                Company.objects.for_tenant(request.tenant).select_related("owner"),
                lambda row: [row.name, row.domain, row.industry, row.location, row.phone, row.email, _owner_csv(row.owner)],
            ),
            "contacts": (
                "sipulse-crm-contacts.csv",
                ["first_name", "last_name", "title", "email", "phone", "company", "owner"],
                Contact.objects.for_tenant(request.tenant).select_related("company", "owner"),
                lambda row: [row.first_name, row.last_name, row.title, row.email, row.phone, row.company.name if row.company else "", _owner_csv(row.owner)],
            ),
            "deals": (
                "sipulse-crm-deals.csv",
                ["name", "amount", "currency", "stage", "company", "priority", "expected_close_at", "owner"],
                Deal.objects.for_tenant(request.tenant).select_related("stage", "company", "owner"),
                lambda row: [
                    row.name,
                    str(row.amount),
                    row.currency,
                    row.stage.name if row.stage else "",
                    row.company.name if row.company else "",
                    row.priority,
                    row.expected_close_at or "",
                    _owner_csv(row.owner),
                ],
            ),
            "activities": (
                "sipulse-crm-activities.csv",
                ["title", "kind", "company", "deal", "due_at", "completed_at"],
                Activity.objects.for_tenant(request.tenant).select_related("company", "deal"),
                lambda row: [
                    row.title,
                    row.kind,
                    row.company.name if row.company else "",
                    row.deal.name if row.deal else "",
                    row.due_at or "",
                    row.completed_at or "",
                ],
            ),
        }
        spec = writers.get(kind)
        if spec is None:
            raise APIError("Export kind must be companies, contacts, deals, or activities.", code="VALIDATION_ERROR")
        filename, headers, queryset, row_fn = spec
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(headers)
        count = 0
        for item in queryset.iterator():
            writer.writerow(row_fn(item))
            count += 1
        write_audit(
            action="CRM_EXPORTED",
            request=request,
            tenant=request.tenant,
            resource_type=kind,
            metadata={"count": count},
        )
        return response


def _owner_csv(user) -> str:
    if user is None:
        return ""
    return ((user.first_name or "") + " " + (user.last_name or "")).strip() or user.email


class CrmAssigneeListView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "crm.view"
    required_module = "crm"

    def get(self, request):
        members = (
            Membership.objects.filter(tenant=request.tenant, status=Membership.Status.ACTIVE)
            .select_related("user")
            .order_by("user__email")
        )
        rows = []
        for membership in members:
            person = membership.user
            name = ((person.first_name or "") + " " + (person.last_name or "")).strip() or person.email
            rows.append(
                {
                    "id": str(person.id),
                    "email": person.email,
                    "first_name": person.first_name,
                    "last_name": person.last_name,
                    "name": name,
                }
            )
        return Response(rows)


class CompanyListCreateView(TenantCrmMixin, generics.ListCreateAPIView):
    serializer_class = CompanySerializer
    queryset_model = Company
    search_fields = ("name", "domain", "industry", "location", "phone", "email")
    filterset_fields = ("industry", "owner")

    @property
    def required_permission(self):
        return "crm.create" if self.request.method == "POST" else "crm.view"

    def get_queryset(self):
        return Company.objects.for_tenant(self.request.tenant).select_related("owner")


class CompanyDetailView(TenantCrmMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CompanySerializer
    queryset_model = Company
    lookup_field = "id"

    @property
    def required_permission(self):
        if self.request.method == "DELETE":
            return "crm.delete"
        if self.request.method in {"PUT", "PATCH"}:
            return "crm.update"
        return "crm.view"

    def get_queryset(self):
        return Company.objects.for_tenant(self.request.tenant).select_related("owner")


class ContactListCreateView(TenantCrmMixin, generics.ListCreateAPIView):
    serializer_class = ContactSerializer
    queryset_model = Contact
    search_fields = ("first_name", "last_name", "email", "phone", "title")
    filterset_fields = ("company", "owner")

    @property
    def required_permission(self):
        return "crm.create" if self.request.method == "POST" else "crm.view"

    def get_queryset(self):
        return Contact.objects.for_tenant(self.request.tenant).select_related("company", "owner")


class ContactDetailView(TenantCrmMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContactSerializer
    queryset_model = Contact
    lookup_field = "id"

    @property
    def required_permission(self):
        if self.request.method == "DELETE":
            return "crm.delete"
        if self.request.method in {"PUT", "PATCH"}:
            return "crm.update"
        return "crm.view"

    def get_queryset(self):
        return Contact.objects.for_tenant(self.request.tenant).select_related("company", "owner")


class DealListCreateView(TenantCrmMixin, generics.ListCreateAPIView):
    serializer_class = DealSerializer
    queryset_model = Deal
    filterset_fields = ("stage", "pipeline", "company", "owner", "contact", "priority")
    search_fields = ("name",)

    @property
    def required_permission(self):
        return "crm.create" if self.request.method == "POST" else "crm.view"

    def get_queryset(self):
        qs = Deal.objects.for_tenant(self.request.tenant).select_related(
            "company", "contact", "stage", "pipeline", "owner"
        )
        after = (self.request.query_params.get("expected_close_after") or "").strip()
        before = (self.request.query_params.get("expected_close_before") or "").strip()
        has_lead = self.request.query_params.get("has_lead")
        if after:
            qs = qs.filter(expected_close_at__gte=after)
        if before:
            qs = qs.filter(expected_close_at__lte=before)
        if _truthy(has_lead):
            qs = qs.filter(lead__isnull=False)
        elif _falsy(has_lead):
            qs = qs.filter(lead__isnull=True)
        return qs


class DealDetailView(TenantCrmMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DealSerializer
    queryset_model = Deal
    lookup_field = "id"

    @property
    def required_permission(self):
        if self.request.method == "DELETE":
            return "crm.delete"
        if self.request.method in {"PUT", "PATCH"}:
            return "crm.update"
        return "crm.view"

    def get_queryset(self):
        return Deal.objects.for_tenant(self.request.tenant).select_related(
            "company", "contact", "stage", "pipeline", "owner"
        )


class ActivityListCreateView(TenantCrmMixin, generics.ListCreateAPIView):
    serializer_class = ActivitySerializer
    queryset_model = Activity
    filterset_fields = ("company", "deal", "contact", "kind", "owner")
    search_fields = ("title", "body")

    @property
    def required_permission(self):
        return "crm.create" if self.request.method == "POST" else "crm.view"

    def get_queryset(self):
        qs = Activity.objects.for_tenant(self.request.tenant).select_related("company", "deal", "contact", "owner")
        overdue = self.request.query_params.get("overdue")
        if _truthy(overdue):
            qs = qs.filter(due_at__lt=timezone.now(), completed_at__isnull=True)
        completed = self.request.query_params.get("completed")
        if _truthy(completed):
            qs = qs.filter(completed_at__isnull=False)
        elif _falsy(completed):
            qs = qs.filter(completed_at__isnull=True)
        return qs


class ActivityDetailView(TenantCrmMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ActivitySerializer
    queryset_model = Activity
    lookup_field = "id"

    @property
    def required_permission(self):
        if self.request.method == "DELETE":
            return "crm.delete"
        if self.request.method in {"PUT", "PATCH"}:
            return "crm.update"
        return "crm.view"

    def get_queryset(self):
        return Activity.objects.for_tenant(self.request.tenant).select_related("company", "deal", "contact", "owner")


class CrmFunnelView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "crm.view"
    required_module = "crm"

    def get(self, request):
        pipelines = Pipeline.objects.for_tenant(request.tenant).prefetch_related("stages")
        pipeline_id = request.query_params.get("pipeline")
        pipeline = pipelines.filter(id=pipeline_id).first() if pipeline_id else None
        if pipeline is None:
            pipeline = pipelines.filter(is_default=True).first() or pipelines.first()
        if pipeline is None:
            return Response({"pipeline": "", "pipeline_id": "", "origin": "none", "why": "No CRM pipeline exists yet.", "stages": []})
        deals = Deal.objects.for_tenant(request.tenant).filter(pipeline=pipeline)
        stages = []
        for stage in pipeline.stages.all():
            qs = deals.filter(stage=stage)
            stages.append(
                {
                    "id": str(stage.id),
                    "name": stage.name,
                    "code": stage.code,
                    "is_won": stage.is_won,
                    "is_lost": stage.is_lost,
                    "deals": qs.count(),
                    "amount": str(qs.aggregate(total=Sum("amount"))["total"] or 0),
                }
            )
        return Response(
            {
                "pipeline": pipeline.name,
                "pipeline_id": str(pipeline.id),
                "origin": "fact",
                "why": "Stage counts and amounts are stored CRM deals. No win-rate forecast is computed.",
                "stages": stages,
            }
        )
