from django.contrib import admin

from apps.rbac.models import Permission, Role


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "module")
    search_fields = ("code", "name")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "is_system")
    list_filter = ("is_system",)
