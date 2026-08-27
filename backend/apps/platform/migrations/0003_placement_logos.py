import apps.platform.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0002_default_light_theme"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformappearance",
            name="logo_mark",
            field=models.FileField(blank=True, upload_to=apps.platform.models.branding_upload_to),
        ),
        migrations.AddField(
            model_name="platformappearance",
            name="logo_mark_dark",
            field=models.FileField(blank=True, upload_to=apps.platform.models.branding_upload_to),
        ),
        migrations.AddField(
            model_name="platformappearance",
            name="logo_nav",
            field=models.FileField(blank=True, upload_to=apps.platform.models.branding_upload_to),
        ),
        migrations.AddField(
            model_name="platformappearance",
            name="logo_nav_dark",
            field=models.FileField(blank=True, upload_to=apps.platform.models.branding_upload_to),
        ),
        migrations.AddField(
            model_name="platformappearance",
            name="logo_sidebar",
            field=models.FileField(blank=True, upload_to=apps.platform.models.branding_upload_to),
        ),
        migrations.AddField(
            model_name="platformappearance",
            name="logo_sidebar_dark",
            field=models.FileField(blank=True, upload_to=apps.platform.models.branding_upload_to),
        ),
        migrations.AddField(
            model_name="platformappearance",
            name="logo_footer",
            field=models.FileField(blank=True, upload_to=apps.platform.models.branding_upload_to),
        ),
        migrations.AddField(
            model_name="platformappearance",
            name="logo_footer_dark",
            field=models.FileField(blank=True, upload_to=apps.platform.models.branding_upload_to),
        ),
    ]
