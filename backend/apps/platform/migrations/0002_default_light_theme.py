import django.core.validators
from django.db import migrations, models


def set_light_theme(apps, schema_editor):
    Appearance = apps.get_model("platform", "PlatformAppearance")
    Appearance.objects.filter(singleton_key=1).update(default_theme="light", secondary_color="#148A99")


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="platformappearance",
            name="default_theme",
            field=models.CharField(
                choices=[("light", "Light"), ("dark", "Dark"), ("system", "System")],
                default="light",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="platformappearance",
            name="secondary_color",
            field=models.CharField(
                default="#148A99",
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        r"^#[0-9A-Fa-f]{6}$",
                        "Use a 6-digit hex color such as #0B4F6C.",
                    )
                ],
            ),
        ),
        migrations.RunPython(set_light_theme, migrations.RunPython.noop),
    ]
