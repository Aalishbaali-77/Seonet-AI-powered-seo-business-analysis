from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("websites", "0003_keywordrankrun"),
    ]

    operations = [
        migrations.AddField(
            model_name="keywordrankrun",
            name="ai",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
