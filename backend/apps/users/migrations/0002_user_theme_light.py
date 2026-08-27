from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="theme_preference",
            field=models.CharField(
                choices=[("light", "Light"), ("dark", "Dark"), ("system", "System")],
                default="light",
                max_length=16,
            ),
        ),
    ]
