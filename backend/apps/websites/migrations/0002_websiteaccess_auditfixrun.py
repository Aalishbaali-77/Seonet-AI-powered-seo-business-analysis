import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("audits", "0001_initial"),
        ("jobs", "0001_initial"),
        ("tenants", "0002_initial"),
        ("websites", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebsiteAccess",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("kind", models.CharField(choices=[("wordpress", "WordPress"), ("ftp", "FTP"), ("sftp", "SFTP / VPS"), ("cpanel", "cPanel FTP")], max_length=20)),
                ("status", models.CharField(choices=[("disconnected", "Disconnected"), ("connected", "Connected"), ("error", "Error")], db_index=True, default="disconnected", max_length=20)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("secret_blob", models.TextField(blank=True)),
                ("last_tested_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)ss", to="tenants.tenant")),
                ("website", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="code_access", to="websites.website")),
            ],
        ),
        migrations.CreateModel(
            name="AuditFixRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("applying", "Applying"), ("reauditing", "Re-auditing"), ("completed", "Completed"), ("failed", "Failed")], db_index=True, default="pending", max_length=20)),
                ("plan", models.JSONField(blank=True, default=dict)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("comparison", models.JSONField(blank=True, default=dict)),
                ("error", models.TextField(blank=True)),
                ("access", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fix_runs", to="websites.websiteaccess")),
                ("baseline_audit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fix_runs_as_baseline", to="audits.audit")),
                ("followup_audit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fix_runs_as_followup", to="audits.audit")),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_fix_runs", to="jobs.job")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)ss", to="tenants.tenant")),
                ("website", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fix_runs", to="websites.website")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="websiteaccess",
            index=models.Index(fields=["tenant", "website"], name="websites_we_tenant__access_idx"),
        ),
        migrations.AddIndex(
            model_name="websiteaccess",
            index=models.Index(fields=["tenant", "created_at"], name="websites_we_tenant__acc_cr_idx"),
        ),
        migrations.AddIndex(
            model_name="auditfixrun",
            index=models.Index(fields=["tenant", "website", "created_at"], name="websites_au_tenant__fix_idx"),
        ),
        migrations.AddIndex(
            model_name="auditfixrun",
            index=models.Index(fields=["tenant", "created_at"], name="websites_au_tenant__fix_cr_idx"),
        ),
    ]
