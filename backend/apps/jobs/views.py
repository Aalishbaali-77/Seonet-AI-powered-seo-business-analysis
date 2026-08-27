from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import APIError
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.jobs.models import Job
from apps.jobs.serializers import JobSerializer
from apps.jobs.services import cancel_job


class JobListView(generics.ListAPIView):
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "job.view"
    filterset_fields = ("status", "job_type")
    search_fields = ("job_type", "error")

    def get_queryset(self):
        return Job.objects.for_tenant(self.request.tenant)


class JobDetailView(generics.RetrieveAPIView):
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "job.view"
    lookup_field = "id"

    def get_queryset(self):
        return Job.objects.for_tenant(self.request.tenant)

    def get_object(self):
        try:
            return super().get_object()
        except Job.DoesNotExist as exc:
            raise NotFound() from exc


class JobCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "job.view"

    def post(self, request, id):
        job = Job.objects.for_tenant(request.tenant).filter(id=id).first()
        if job is None:
            raise APIError("Resource not found.", code="NOT_FOUND", status_code=404)
        if job.status in {Job.Status.COMPLETED, Job.Status.FAILED}:
            raise APIError("Finished jobs cannot be cancelled.", code="VALIDATION_ERROR")
        return Response(JobSerializer(cancel_job(job)).data)
