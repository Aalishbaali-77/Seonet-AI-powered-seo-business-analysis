from django.contrib import admin

from apps.tenants.models import Membership, Team, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "created_at")
    search_fields = ("name", "slug")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "tenant", "status", "is_default")
    list_filter = ("status",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "slug")
