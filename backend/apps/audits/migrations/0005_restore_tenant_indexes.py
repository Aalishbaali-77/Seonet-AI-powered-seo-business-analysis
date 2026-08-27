from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("audits", "0004_performance_intelligence"),
        ("tenants", "0002_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="crawlpage",
            index=models.Index(fields=["tenant", "created_at"], name="audits_craw_tenant__d22fc3_idx"),
        ),
        migrations.AddIndex(
            model_name="auditissue",
            index=models.Index(fields=["tenant", "created_at"], name="audits_issue_tenant_created"),
        ),
    ]
