from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))
