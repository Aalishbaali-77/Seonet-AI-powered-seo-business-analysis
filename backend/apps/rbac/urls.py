from django.urls import path

from apps.rbac.views import PermissionListView, RoleDetailView, RoleListView

urlpatterns = [
    path("roles/", RoleListView.as_view(), name="role-list"),
    path("roles/<uuid:id>/", RoleDetailView.as_view(), name="role-detail"),
    path("permissions/", PermissionListView.as_view(), name="permission-list"),
]
