from __future__ import annotations

import uuid
from pathlib import Path

from django.core.validators import RegexValidator
from django.db import models

from apps.common.encryption import EncryptedJSONField
from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel
from apps.platform.landing import (
    DEFAULT_LANDING,
    default_faqs,
    default_nav,
    default_pains,
    default_security,
    default_stats,
    default_steps,
)

HEX_COLOR = RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Use a 6-digit hex color such as #0B4F6C.")


def branding_upload_to(_instance, filename: str) -> str:
    ext = Path(filename).suffix.lower()[:8]
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".ico", ".gif"}:
        ext = ".png"
    return f"branding/{uuid.uuid4().hex}{ext}"


class PlatformAppearance(UUIDPrimaryKeyModel, TimeStampedModel):
    class Theme(models.TextChoices):
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"
        SYSTEM = "system", "System"

    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    product_name = models.CharField(max_length=80, default="Seonet")
    legal_name = models.CharField(max_length=160, default="Seonet")
    tagline = models.CharField(max_length=180, default="AI-Powered Business Growth Intelligence")
    description = models.TextField(
        blank=True,
        default="Website intelligence, licensed keyword ranks, first-party commerce, cited markets, lead discovery, and native CRM in one tenant. Empty stays empty.",
    )
    support_email = models.EmailField(blank=True, default="hello@siglobalsolutions.com")
    support_url = models.URLField(blank=True, default="")
    login_footer = models.CharField(
        max_length=240,
        blank=True,
        default="Need a workspace? Ask Seonet to provision your tenant.",
    )
    copyright_text = models.CharField(
        max_length=240,
        blank=True,
        default="© 2026 Seonet. All rights reserved.",
    )
    default_theme = models.CharField(max_length=16, choices=Theme.choices, default=Theme.LIGHT)
    primary_color = models.CharField(max_length=7, default="#0B4F6C", validators=[HEX_COLOR])
    secondary_color = models.CharField(max_length=7, default="#148A99", validators=[HEX_COLOR])
    logo = models.FileField(upload_to=branding_upload_to, blank=True)
    logo_dark = models.FileField(upload_to=branding_upload_to, blank=True)
    logo_mark = models.FileField(upload_to=branding_upload_to, blank=True)
    logo_mark_dark = models.FileField(upload_to=branding_upload_to, blank=True)
    logo_nav = models.FileField(upload_to=branding_upload_to, blank=True)
    logo_nav_dark = models.FileField(upload_to=branding_upload_to, blank=True)
    logo_sidebar = models.FileField(upload_to=branding_upload_to, blank=True)
    logo_sidebar_dark = models.FileField(upload_to=branding_upload_to, blank=True)
    logo_footer = models.FileField(upload_to=branding_upload_to, blank=True)
    logo_footer_dark = models.FileField(upload_to=branding_upload_to, blank=True)
    favicon = models.FileField(upload_to=branding_upload_to, blank=True)
    app_icon = models.FileField(upload_to=branding_upload_to, blank=True)

    class Meta:
        verbose_name = "Platform appearance"

    def __str__(self) -> str:
        return self.product_name

    def save(self, *args, **kwargs):
        self.singleton_key = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> PlatformAppearance:
        obj, _created = cls.objects.get_or_create(singleton_key=1)
        return obj


class PlatformLanding(UUIDPrimaryKeyModel, TimeStampedModel):
    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    nav = models.JSONField(default=default_nav, blank=True)
    hero_eyebrow = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["hero_eyebrow"])
    hero_title = models.CharField(max_length=240, blank=True, default=DEFAULT_LANDING["hero_title"])
    hero_body = models.TextField(blank=True, default=DEFAULT_LANDING["hero_body"])
    hero_primary_cta = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["hero_primary_cta"])
    hero_secondary_cta = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["hero_secondary_cta"])
    hero_secondary_href = models.CharField(max_length=240, blank=True, default=DEFAULT_LANDING["hero_secondary_href"])
    stats = models.JSONField(default=default_stats, blank=True)
    pains_eyebrow = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["pains_eyebrow"])
    pains_title = models.CharField(max_length=240, blank=True, default=DEFAULT_LANDING["pains_title"])
    pains_body = models.TextField(blank=True, default=DEFAULT_LANDING["pains_body"])
    pains = models.JSONField(default=default_pains, blank=True)
    product_eyebrow = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["product_eyebrow"])
    product_title = models.CharField(max_length=240, blank=True, default=DEFAULT_LANDING["product_title"])
    product_body = models.TextField(blank=True, default=DEFAULT_LANDING["product_body"])
    steps_eyebrow = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["steps_eyebrow"])
    steps_title = models.CharField(max_length=240, blank=True, default=DEFAULT_LANDING["steps_title"])
    steps_body = models.TextField(blank=True, default=DEFAULT_LANDING["steps_body"])
    steps = models.JSONField(default=default_steps, blank=True)
    workspace_eyebrow = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["workspace_eyebrow"])
    workspace_title = models.CharField(max_length=240, blank=True, default=DEFAULT_LANDING["workspace_title"])
    workspace_body = models.TextField(blank=True, default=DEFAULT_LANDING["workspace_body"])
    control_plane_eyebrow = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["control_plane_eyebrow"])
    control_plane_title = models.CharField(max_length=240, blank=True, default=DEFAULT_LANDING["control_plane_title"])
    control_plane_body = models.TextField(blank=True, default=DEFAULT_LANDING["control_plane_body"])
    pricing_eyebrow = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["pricing_eyebrow"])
    pricing_title = models.CharField(max_length=240, blank=True, default=DEFAULT_LANDING["pricing_title"])
    pricing_body = models.TextField(blank=True, default=DEFAULT_LANDING["pricing_body"])
    security_eyebrow = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["security_eyebrow"])
    security_title = models.CharField(max_length=240, blank=True, default=DEFAULT_LANDING["security_title"])
    security_body = models.TextField(blank=True, default=DEFAULT_LANDING["security_body"])
    security = models.JSONField(default=default_security, blank=True)
    faq_eyebrow = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["faq_eyebrow"])
    faq_title = models.CharField(max_length=240, blank=True, default=DEFAULT_LANDING["faq_title"])
    faqs = models.JSONField(default=default_faqs, blank=True)
    cta_title = models.CharField(max_length=240, blank=True, default=DEFAULT_LANDING["cta_title"])
    cta_body = models.TextField(blank=True, default=DEFAULT_LANDING["cta_body"])
    cta_primary = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["cta_primary"])
    cta_secondary = models.CharField(max_length=80, blank=True, default=DEFAULT_LANDING["cta_secondary"])

    class Meta:
        verbose_name = "Platform landing page"

    def __str__(self) -> str:
        return "Landing page"

    def save(self, *args, **kwargs):
        self.singleton_key = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> PlatformLanding:
        obj, _created = cls.objects.get_or_create(singleton_key=1)
        return obj


class LeadSource(UUIDPrimaryKeyModel, TimeStampedModel):
    class Provider(models.TextChoices):
        GOOGLE_PLACES = "google_places", "Google Places"
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Claude"
        XAI = "xai", "Grok"
        GOOGLE_GEMINI = "google_gemini", "Gemini"
        GOOGLE_PAGESPEED = "google_pagespeed", "PageSpeed Insights"
        GOOGLE_CUSTOM_SEARCH = "google_custom_search", "Google Custom Search"
        SERPAPI = "serpapi", "SerpAPI"
        YELP = "yelp", "Yelp"
        FOURSQUARE = "foursquare", "Foursquare"
        GEOAPIFY = "geoapify", "Geoapify"
        OPENSTREETMAP = "openstreetmap", "OpenStreetMap"
        OPENCORPORATES = "opencorporates", "OpenCorporates"
        NPI_REGISTRY = "npi_registry", "NPI Registry"
        LINKEDIN_SALES_NAVIGATOR = "linkedin_sales_navigator", "LinkedIn Sales Navigator"
        YELLOWPAGE_PK = "yellowpage_pk", "YellowPage.pk"
        BBB = "bbb", "Better Business Bureau"
        MANTA = "manta", "Manta"
        HUNTER = "hunter", "Hunter"
        CLEARBIT = "clearbit", "Clearbit"
        APOLLO = "apollo", "Apollo"
        WIKIDATA = "wikidata", "Wikidata"

    class Category(models.TextChoices):
        DISCOVERY = "discovery", "Lead discovery"
        ENRICHMENT = "enrichment", "Lead enrichment"
        AI = "ai", "AI models"
        DIAGNOSTICS = "diagnostics", "Diagnostics"

    code = models.CharField(max_length=40, unique=True)
    provider = models.CharField(max_length=40, choices=Provider.choices)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.DISCOVERY, db_index=True)
    display_name = models.CharField(max_length=80)
    purpose = models.CharField(max_length=240, blank=True)
    is_enabled = models.BooleanField(default=False)
    setup_hint = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    public_config = models.JSONField(default=dict, blank=True)
    encrypted_config = EncryptedJSONField(default=dict, blank=True)

    class Meta:
        ordering = ["sort_order", "display_name"]

    @property
    def requires_key(self) -> bool:
        return bool((self.public_config or {}).get("requires_key", True))

    @property
    def credentials_configured(self) -> bool:
        if not self.requires_key:
            return True
        encrypted = self.encrypted_config or {}
        return bool(str(encrypted.get("api_key") or encrypted.get("access_token") or "").strip())

    @property
    def model(self) -> str:
        return str((self.public_config or {}).get("model") or "")

    @property
    def homepage_url(self) -> str:
        public = self.public_config or {}
        return str(public.get("homepage_url") or public.get("docs_url") or "")

    @property
    def search_url(self) -> str:
        return str((self.public_config or {}).get("search_url") or "")

    def __str__(self) -> str:
        return self.display_name
