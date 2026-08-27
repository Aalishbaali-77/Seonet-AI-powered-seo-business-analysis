from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("platform", "0007_pagespeed_source"),
    ]

    operations = [
        migrations.AlterField(
            model_name="leadsource",
            name="provider",
            field=models.CharField(
                choices=[
                    ("google_places", "Google Places"),
                    ("openai", "OpenAI"),
                    ("anthropic", "Claude"),
                    ("xai", "Grok"),
                    ("google_gemini", "Gemini"),
                    ("google_pagespeed", "PageSpeed Insights"),
                    ("yelp", "Yelp"),
                    ("foursquare", "Foursquare"),
                    ("geoapify", "Geoapify"),
                    ("openstreetmap", "OpenStreetMap"),
                    ("opencorporates", "OpenCorporates"),
                    ("npi_registry", "NPI Registry"),
                    ("linkedin_sales_navigator", "LinkedIn Sales Navigator"),
                    ("yellowpage_pk", "YellowPage.pk"),
                    ("bbb", "Better Business Bureau"),
                    ("manta", "Manta"),
                ],
                max_length=40,
            ),
        ),
    ]
