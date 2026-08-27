import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0001_initial"),
        ("tenants", "0002_initial"),
        ("websites", "0002_websiteaccess_auditfixrun"),
    ]

    operations = [
        migrations.CreateModel(
            name="KeywordRankRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], db_index=True, default="pending", max_length=20)),
                ("source", models.CharField(blank=True, max_length=40)),
                ("keywords", models.JSONField(blank=True, default=list)),
                ("results", models.JSONField(blank=True, default=list)),
                ("suggestions", models.JSONField(blank=True, default=list)),
                ("error", models.TextField(blank=True)),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="keyword_rank_runs", to="jobs.job")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)ss", to="tenants.tenant")),
                ("website", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="keyword_runs", to="websites.website")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="keywordrankrun",
            index=models.Index(fields=["tenant", "website", "created_at"], name="websites_ke_tenant__kw_idx"),
        ),
        migrations.AddIndex(
            model_name="keywordrankrun",
            index=models.Index(fields=["tenant", "created_at"], name="websites_ke_tenant__kw_cr_idx"),
        ),
    ]
