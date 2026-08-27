from __future__ import annotations

from copy import deepcopy

from apps.platform.landing import DEFAULT_LANDING
from apps.platform.models import PlatformAppearance, PlatformLanding

DEFAULT_APPEARANCE = {
    "product_name": "SIPulse",
    "legal_name": "SI Global Solutions",
    "tagline": "AI-Powered Business Growth Intelligence",
    "description": "Website intelligence, licensed keyword ranks, first-party commerce, cited markets, lead discovery, and native CRM in one tenant. Empty stays empty.",
    "support_email": "hello@siglobalsolutions.com",
    "support_url": "",
    "login_footer": "Need a workspace? Ask SI Global Solutions to provision your tenant.",
    "copyright_text": "© 2026 SI Global Solutions. All rights reserved.",
    "default_theme": PlatformAppearance.Theme.LIGHT,
    "primary_color": "#0B4F6C",
    "secondary_color": "#148A99",
}


def apply_platform_content() -> tuple[PlatformAppearance, PlatformLanding]:
    appearance = PlatformAppearance.get_solo()
    for key, value in DEFAULT_APPEARANCE.items():
        setattr(appearance, key, value)
    appearance.save()

    landing = PlatformLanding.get_solo()
    for key, value in DEFAULT_LANDING.items():
        setattr(landing, key, deepcopy(value) if isinstance(value, list) else value)
    landing.save()
    return appearance, landing
