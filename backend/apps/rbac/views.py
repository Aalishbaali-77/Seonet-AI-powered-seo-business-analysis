from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.auditlog.services import write_audit
from apps.common.exceptions import APIError
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.rbac.models import Permission, Role
from apps.rbac.serializers import PermissionSerializer, RoleSerializer


class RoleListView(generics.ListCreateAPIView):
    serializer_class = RoleSerializer
    pagination_class = None
    subscription_exempt = True

    def get_permissions(self):
        self.required_permission = "role.manage" if self.request.method != "GET" else None
        classes = [permissions.IsAuthenticated(), HasTenant()]
        if self.required_permission:
            classes.append(HasPermissionCode())
        return classes

    def get_queryset(self):
        return Role.objects.filter(tenant=self.request.tenant).prefetch_related("permissions").order_by("name")

    def perform_create(self, serializer):
        role = serializer.save()
        write_audit(action="ROLE_CREATED", request=self.request, tenant=self.request.tenant, resource_type="role", resource_id=role.id)


class RoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RoleSerializer
    lookup_field = "id"
    pagination_class = None
    subscription_exempt = True

    def get_permissions(self):
        self.required_permission = "role.manage" if self.request.method != "GET" else None
        classes = [permissions.IsAuthenticated(), HasTenant()]
        if self.required_permission:
            classes.append(HasPermissionCode())
        return classes

    def get_queryset(self):
        return Role.objects.filter(tenant=self.request.tenant).prefetch_related("permissions")

    def perform_update(self, serializer):
        role = serializer.save()
        write_audit(action="ROLE_UPDATED", request=self.request, tenant=self.request.tenant, resource_type="role", resource_id=role.id)

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.code == "owner" or role.is_system:
            raise APIError("System roles cannot be deleted. You can still change their permissions.", code="VALIDATION_ERROR")
        if role.membership_roles.exists():
            raise APIError("Reassign people on this role before deleting it.", code="CONFLICT", status_code=status.HTTP_409_CONFLICT)
        write_audit(action="ROLE_DELETED", request=request, tenant=request.tenant, resource_type="role", resource_id=role.id)
        role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PermissionListView(generics.ListAPIView):
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant]
    queryset = Permission.objects.all().order_by("module", "code")
    pagination_class = None
    subscription_exempt = True
