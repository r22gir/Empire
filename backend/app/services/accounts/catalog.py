"""Every online account SocialForge owns, per business.

OAuth providers stay at ``needs_keys`` until their env client id and
secret are set. Other platforms are tracked here and stay
``not_connected`` until a real credential exists.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


OWNER = "socialforge"

BUSINESSES: tuple[tuple[str, str], ...] = (
    ("workroom", "Empire Workroom"),
    ("woodcraft", "Empire WoodCraft"),
)


@dataclass(frozen=True)
class PlatformSpec:
    key: str
    label: str
    kind: str  # social, marketplace, email, directory, canva, domain_email
    oauth: str | None = None
    env_keys: tuple[str, ...] = ()


PLATFORMS: tuple[PlatformSpec, ...] = (
    PlatformSpec("facebook", "Facebook", "social", "meta", ("META_APP_ID", "META_APP_SECRET")),
    PlatformSpec("instagram", "Instagram", "social", "meta", ("META_APP_ID", "META_APP_SECRET")),
    PlatformSpec("pinterest", "Pinterest", "social", "pinterest", ("PINTEREST_APP_ID", "PINTEREST_APP_SECRET")),
    PlatformSpec("linkedin", "LinkedIn", "social", "linkedin", ("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET")),
    PlatformSpec("tiktok", "TikTok", "social"),
    PlatformSpec("x", "X", "social"),
    PlatformSpec("etsy", "Etsy", "marketplace", "etsy", ("ETSY_CLIENT_ID",)),
    PlatformSpec("ebay", "eBay", "marketplace"),
    PlatformSpec("amazon", "Amazon", "marketplace"),
    PlatformSpec("facebook_marketplace", "Facebook Marketplace", "marketplace"),
    PlatformSpec("craigslist", "Craigslist", "marketplace"),
    PlatformSpec("business_email", "Business email", "email"),
    PlatformSpec("support_email", "Support email", "email"),
    PlatformSpec("google_business", "Google Business Profile", "directory"),
    PlatformSpec("houzz", "Houzz", "directory"),
    PlatformSpec("thumbtack", "Thumbtack", "directory"),
    PlatformSpec("yelp", "Yelp", "directory"),
    PlatformSpec("nextdoor", "Nextdoor", "directory"),
    PlatformSpec("canva", "Canva", "canva"),
    PlatformSpec("domain_email", "Domain email", "domain_email"),
)

_BY_KEY = {spec.key: spec for spec in PLATFORMS}


def platform_spec(key: str) -> PlatformSpec | None:
    return _BY_KEY.get(key)


def provider_keys_ready(spec: PlatformSpec) -> bool | None:
    """True/False when the platform is an OAuth provider. None otherwise."""
    if not spec.oauth:
        return None
    return all(bool(os.getenv(name, "").strip()) for name in spec.env_keys)


def public_base_url() -> str:
    return os.getenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store").rstrip("/")
