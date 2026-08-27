from django.contrib import admin

from apps.jobs.models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("job_type", "status", "tenant", "progress", "created_at")
    list_filter = ("status", "job_type")
