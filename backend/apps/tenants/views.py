from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.auditlog.services import write_audit
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.tenants.members import add_tenant_member, remove_tenant_member, update_tenant_member
from apps.tenants.models import Membership, Tenant
from apps.tenants.serializers import MemberCreateSerializer, MembershipSerializer, MemberUpdateSerializer, TenantSerializer


class TenantQuerysetMixin:
    def get_memberships(self):
        return Membership.objects.filter(user=self.request.user, status=Membership.Status.ACTIVE)


class TenantListView(TenantQuerysetMixin, generics.ListAPIView):
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Tenant.objects.filter(id__in=self.get_memberships().values("tenant_id"))


class TenantDetailView(TenantQuerysetMixin, generics.RetrieveUpdateAPIView):
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "settings.manage"
    lookup_field = "id"
    subscription_exempt = True

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        return Tenant.objects.filter(id__in=self.get_memberships().values("tenant_id"))

    def perform_update(self, serializer):
        tenant = serializer.save()
        write_audit(
            action="SETTINGS_CHANGED",
            request=self.request,
            tenant=tenant,
            resource_type="tenant",
            resource_id=tenant.id,
        )


class TenantMemberListView(generics.ListCreateAPIView):
    serializer_class = MembershipSerializer
    pagination_class = None
    subscription_exempt = True

    def get_permissions(self):
        self.required_permission = "member.view" if self.request.method == "GET" else "member.manage"
        return [permissions.IsAuthenticated(), HasTenant(), HasPermissionCode()]

    def get_queryset(self):
        if str(self.request.tenant.id) != str(self.kwargs["id"]):
            return Membership.objects.none()
        return (
            Membership.objects.filter(tenant_id=self.kwargs["id"])
            .select_related("user")
            .prefetch_related("membership_roles__role")
            .order_by("user__email")
        )

    def create(self, request, *args, **kwargs):
        if str(request.tenant.id) != str(self.kwargs["id"]):
            raise NotFound()
        payload = MemberCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        membership = add_tenant_member(
            tenant=request.tenant,
            actor=request.user,
            email=data["email"],
            role_code=data.get("role_code") or "viewer",
            first_name=data.get("first_name") or "",
            last_name=data.get("last_name") or "",
            password=data.get("password") or "",
        )
        membership = (
            Membership.objects.select_related("user").prefetch_related("membership_roles__role").get(pk=membership.pk)
        )
        write_audit(action="MEMBER_ADDED", request=request, tenant=request.tenant, resource_type="membership", resource_id=membership.id)
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class TenantMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MembershipSerializer
    lookup_url_kwarg = "member_id"
    lookup_field = "id"
    subscription_exempt = True

    def get_permissions(self):
        self.required_permission = "member.view" if self.request.method == "GET" else "member.manage"
        return [permissions.IsAuthenticated(), HasTenant(), HasPermissionCode()]

    def get_queryset(self):
        if str(self.request.tenant.id) != str(self.kwargs["id"]):
            return Membership.objects.none()
        return Membership.objects.filter(tenant_id=self.kwargs["id"]).select_related("user").prefetch_related("membership_roles__role")

    def update(self, request, *args, **kwargs):
        membership = self.get_object()
        payload = MemberUpdateSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        membership = update_tenant_member(
            membership=membership,
            actor=request.user,
            role_code=payload.validated_data.get("role_code"),
            status=payload.validated_data.get("status"),
        )
        membership = (
            Membership.objects.select_related("user").prefetch_related("membership_roles__role").get(pk=membership.pk)
        )
        write_audit(action="MEMBER_UPDATED", request=request, tenant=request.tenant, resource_type="membership", resource_id=membership.id)
        return Response(MembershipSerializer(membership).data)

    def destroy(self, request, *args, **kwargs):
        membership = self.get_object()
        member_id = membership.id
        remove_tenant_member(membership=membership, actor=request.user)
        write_audit(action="MEMBER_REMOVED", request=request, tenant=request.tenant, resource_type="membership", resource_id=member_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
