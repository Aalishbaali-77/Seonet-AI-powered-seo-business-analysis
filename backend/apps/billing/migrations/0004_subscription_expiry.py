import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0003_landing_cms"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscription",
            name="status",
            field=models.CharField(
                choices=[
                    ("trialing", "Trialing"),
                    ("active", "Active"),
                    ("past_due", "Past due"),
                    ("expired", "Expired"),
                    ("canceled", "Canceled"),
                ],
                db_index=True,
                default="trialing",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="plan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="invoices",
                to="billing.plan",
            ),
        ),
    ]
