from copy import deepcopy

from django.db import migrations


def refresh_landing(apps, schema_editor):
    from apps.billing.catalog import PRODUCT_MODULES
    from apps.platform.content import DEFAULT_APPEARANCE
    from apps.platform.landing import DEFAULT_LANDING

    PlatformLanding = apps.get_model("platform", "PlatformLanding")
    landing = PlatformLanding.objects.filter(singleton_key=1).first()
    if landing is not None:
        for key, value in DEFAULT_LANDING.items():
            setattr(landing, key, deepcopy(value) if isinstance(value, list) else value)
        landing.save()

    PlatformAppearance = apps.get_model("platform", "PlatformAppearance")
    appearance = PlatformAppearance.objects.filter(singleton_key=1).first()
    if appearance is not None:
        appearance.description = DEFAULT_APPEARANCE["description"]
        appearance.save()

    ProductModule = apps.get_model("billing", "ProductModule")
    for item in PRODUCT_MODULES:
        ProductModule.objects.filter(code=item["code"]).update(description=item["description"], name=item["name"])


def noop(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0004_subscription_expiry"),
        ("platform", "0009_serp_sources"),
    ]

    operations = [
        migrations.RunPython(refresh_landing, noop),
    ]
