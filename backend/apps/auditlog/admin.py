from django.contrib import admin

from apps.auditlog.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "tenant", "created_at")
    list_filter = ("action",)
    search_fields = ("action", "request_id")
    readonly_fields = [field.name for field in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
