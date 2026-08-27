import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="crmconnection",
            name="enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="crmconnection",
            name="encrypted_config",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="crmconnection",
            name="last_checked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="crmconnection",
            name="status",
            field=models.CharField(
                choices=[
                    ("disconnected", "Disconnected"),
                    ("configured", "Configured"),
                    ("connected", "Connected"),
                    ("error", "Error"),
                ],
                db_index=True,
                default="disconnected",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="crmconnection",
            name="provider",
            field=models.CharField(db_index=True, max_length=40),
        ),
        migrations.AlterUniqueTogether(
            name="crmconnection",
            unique_together={("tenant", "provider")},
        ),
        migrations.AddIndex(
            model_name="crmconnection",
            index=models.Index(fields=["tenant", "provider"], name="integration_tenant__prov_idx"),
        ),
        migrations.CreateModel(
            name="TenantApiToken",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("name", models.CharField(max_length=80)),
                ("prefix", models.CharField(db_index=True, max_length=24)),
                ("hashed_key", models.CharField(max_length=64)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tenant_api_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)ss",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="tenantapitoken",
            index=models.Index(fields=["tenant", "created_at"], name="integration_tenant__tok_idx"),
        ),
        migrations.AddIndex(
            model_name="tenantapitoken",
            index=models.Index(fields=["prefix"], name="integration_prefix_idx"),
        ),
    ]
