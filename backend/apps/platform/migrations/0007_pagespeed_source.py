from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("platform", "0006_api_sources"),
    ]

    operations = [
        migrations.AlterField(
            model_name="leadsource",
            name="category",
            field=models.CharField(
                choices=[
                    ("discovery", "Lead discovery"),
                    ("ai", "AI models"),
                    ("diagnostics", "Diagnostics"),
                ],
                db_index=True,
                default="discovery",
                max_length=20,
            ),
        ),
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
                ],
                max_length=40,
            ),
        ),
    ]
