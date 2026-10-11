"""
SocialForge — Social media management for Empire.
Content calendar, post composer, AI content generation, analytics.
JSON file storage (same pattern as quotes/craftforge).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import json
import uuid
import os
import logging

from app.services.social_service import (
    post_to_instagram,
    post_to_facebook,
    get_social_accounts,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["socialforge"])

from app.routers.account_hub import router as account_hub_router  # noqa: E402

router.include_router(account_hub_router)


def _storage_root() -> str:
    from app.edition import socialforge_storage_dir
    return str(socialforge_storage_dir())


def _posts_dir() -> str:
    path = os.path.join(_storage_root(), "posts")
    os.makedirs(path, exist_ok=True)
    return path


def _campaigns_dir() -> str:
    path = os.path.join(_storage_root(), "campaigns")
    os.makedirs(path, exist_ok=True)
    return path


def _accounts_file() -> str:
    return os.path.join(_storage_root(), "accounts.json")


def _profile_file() -> str:
    return os.path.join(_storage_root(), "business_profile.json")


# Never mkdir ~/empire-repo at import. Family editions resolve under
# EMPIRE_DATA_DIR via socialforge_storage_dir(); Workroom mkdirs on first write.


# ── Helpers ───────────────────────────────────────────────────────────────

def _load_all(directory: str) -> list[dict]:
    items = []
    if not os.path.isdir(directory):
        return items
    for f in sorted(os.listdir(directory), reverse=True):
        if f.endswith(".json"):
            with open(os.path.join(directory, f)) as fh:
                items.append(json.load(fh))
    return items


def _load_one(directory: str, item_id: str) -> dict | None:
    path = os.path.join(directory, f"{item_id}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _save(directory: str, item_id: str, data: dict):
    with open(os.path.join(directory, f"{item_id}.json"), "w") as f:
        json.dump(data, f, indent=2)


def _delete(directory: str, item_id: str) -> bool:
    path = os.path.join(directory, f"{item_id}.json")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def _next_code(directory: str, prefix: str) -> str:
    year = datetime.now().strftime("%Y")
    existing = _load_all(directory)
    codes = [p.get("code", "") for p in existing if p.get("code", "").startswith(f"{prefix}-{year}-")]
    if codes:
        nums = [int(c.split("-")[-1]) for c in codes if c.split("-")[-1].isdigit()]
        next_num = max(nums) + 1 if nums else 1
    else:
        next_num = 1
    return f"{prefix}-{year}-{next_num:03d}"


# ── Models ────────────────────────────────────────────────────────────────

class PostCreate(BaseModel):
    platform: str = "instagram"  # instagram, facebook, pinterest, linkedin, tiktok
    content: str = ""
    hashtags: str = ""
    media_url: Optional[str] = None
    scheduled_for: Optional[str] = None  # ISO datetime
    campaign_id: Optional[str] = None
    status: str = "draft"  # draft, scheduled, posted, failed

class PostUpdate(BaseModel):
    content: Optional[str] = None
    hashtags: Optional[str] = None
    platform: Optional[str] = None
    media_url: Optional[str] = None
    scheduled_for: Optional[str] = None
    campaign_id: Optional[str] = None
    status: Optional[str] = None

class CampaignCreate(BaseModel):
    name: str
    description: str = ""
    platforms: list[str] = ["instagram"]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str = "planning"  # planning, active, completed, paused

class AIContentRequest(BaseModel):
    platform: str = "instagram"
    topic: str
    style: str = "professional"  # professional, casual, luxury, educational
    include_hashtags: bool = True


# ── Posts CRUD ────────────────────────────────────────────────────────────

@router.get("/posts")
async def list_posts(status: Optional[str] = None, platform: Optional[str] = None):
    posts = _load_all(_posts_dir())
    if status:
        posts = [p for p in posts if p.get("status") == status]
    if platform:
        posts = [p for p in posts if p.get("platform") == platform]
    return posts


@router.post("/posts")
async def create_post(data: PostCreate):
    post_id = uuid.uuid4().hex[:12]
    code = _next_code(_posts_dir(), "POST")
    from app.edition import coerce_social_status
    post = {
        "id": post_id,
        "code": code,
        "platform": data.platform,
        "content": data.content,
        "hashtags": data.hashtags,
        "media_url": data.media_url,
        "scheduled_for": data.scheduled_for,
        "campaign_id": data.campaign_id,
        "status": coerce_social_status(data.status),
        "engagement": {"likes": 0, "comments": 0, "shares": 0, "reach": 0},
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "posted_at": None,
    }
    _save(_posts_dir(), post_id, post)
    return post


@router.get("/posts/{post_id}")
async def get_post(post_id: str):
    post = _load_one(_posts_dir(), post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    return post


@router.put("/posts/{post_id}")
async def update_post(post_id: str, data: PostUpdate):
    post = _load_one(_posts_dir(), post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    from app.edition import coerce_social_status, is_family_edition
    for field, val in data.model_dump(exclude_none=True).items():
        post[field] = val
    if is_family_edition() and data.status:
        post["status"] = coerce_social_status(data.status)
    if data.status == "posted" and not is_family_edition() and not post.get("posted_at"):
        post["posted_at"] = datetime.utcnow().isoformat()
    post["updated_at"] = datetime.utcnow().isoformat()
    _save(_posts_dir(), post_id, post)
    return post


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str):
    if not _delete(_posts_dir(), post_id):
        raise HTTPException(404, "Post not found")
    return {"deleted": True}


# ── Campaigns CRUD ────────────────────────────────────────────────────────

@router.get("/campaigns")
async def list_campaigns():
    return _load_all(_campaigns_dir())


@router.post("/campaigns")
async def create_campaign(data: CampaignCreate):
    camp_id = uuid.uuid4().hex[:12]
    code = _next_code(_campaigns_dir(), "CAMP")
    campaign = {
        "id": camp_id,
        "code": code,
        "name": data.name,
        "description": data.description,
        "platforms": data.platforms,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "status": data.status,
        "post_count": 0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    _save(_campaigns_dir(), camp_id, campaign)
    return campaign


@router.delete("/campaigns/{camp_id}")
async def delete_campaign(camp_id: str):
    if not _delete(_campaigns_dir(), camp_id):
        raise HTTPException(404, "Campaign not found")
    return {"deleted": True}


# ── AI Content Generation ─────────────────────────────────────────────────

@router.post("/generate")
async def generate_content(data: AIContentRequest):
    """Use AI to generate a social media post."""
    from app.services.max.ai_router import ai_router, AIMessage

    platform_tips = {
        "instagram": "Use emojis, line breaks for readability, 20-25 hashtags, include a CTA",
        "facebook": "More conversational, shorter hashtag list (5-8), include a link or question",
        "pinterest": "Descriptive, keyword-rich, 5-10 hashtags, focus on visual appeal",
        "linkedin": "Professional tone, industry insights, 3-5 hashtags, thought leadership",
        "tiktok": "Casual, trendy, trending hashtags, hook in first line",
    }

    style_guide = {
        "professional": "Polished, trustworthy, expert tone",
        "casual": "Friendly, approachable, conversational",
        "luxury": "Elegant, aspirational, premium feel",
        "educational": "Informative, helpful tips, value-driven",
    }

    from app.edition import assistant_name, is_family_edition
    from app.services.edition_facts import guard_public_text, public_facts_block
    if is_family_edition():
        who = assistant_name()
        prompt = (
            f"Escribe un post de {data.platform} en español para {who}. "
            "Usa solo los hechos públicos. No incluyas datos confidenciales, "
            "precios que no estén en esos hechos, ni datos legales que no estén escritos.\n\n"
            f"{public_facts_block()}\n\n"
            f"Tema: {data.topic}\n"
        )
    else:
        prompt = (
        f"Write a {data.platform} post for Empire Workroom, a premium custom window treatment "
        f"business in Washington DC. We specialize in drapery, shades, blinds, upholstery, and bedding.\n\n"
        f"Topic: {data.topic}\n"
        f"Style: {style_guide.get(data.style, data.style)}\n"
        f"Platform tips: {platform_tips.get(data.platform, '')}\n\n"
        f"Provide:\n"
        f"1. The full post caption (ready to copy-paste)\n"
    )
    if data.include_hashtags:
        prompt += f"2. A list of 20-25 relevant hashtags for {data.platform}\n"
    prompt += "3. Best day/time to post\n4. Suggested image/visual description\n"

    try:
        system = (
            f"You are {assistant_name() if is_family_edition() else 'Nova'}. "
            "Public content may use only public facts. Never repeat a confidential value."
            if is_family_edition()
            else (
                "You are Nova, the AI social media manager for Empire Workroom. "
                "Create engaging, platform-optimized content that drives engagement. "
                "Target audience: homeowners, interior designers, real estate stagers."
            )
        )
        response = await ai_router.chat(
            messages=[AIMessage(role="user", content=prompt)],
            desk="marketing",
            source="generate",
            system_prompt=system,
        )
        content = guard_public_text(response.content) if is_family_edition() else response.content
        return {
            "platform": data.platform,
            "topic": data.topic,
            "style": data.style,
            "generated_content": content,
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, f"AI generation failed: {e}")


# ── Live Social Posting ───────────────────────────────────────────────────

class InstagramPostRequest(BaseModel):
    caption: str
    image_url: Optional[str] = None


class FacebookPostRequest(BaseModel):
    message: str
    link: Optional[str] = None


@router.post("/posts/{post_id}/approve")
async def approve_post(post_id: str):
    """AMP: Juan (or an allowlisted operator) approves before anything posts."""
    post = _load_one(_posts_dir(), post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    post["status"] = "approved"
    post["approved_at"] = datetime.utcnow().isoformat()
    post["updated_at"] = datetime.utcnow().isoformat()
    _save(_posts_dir(), post_id, post)
    return post


@router.post("/post/instagram")
async def api_post_to_instagram(data: InstagramPostRequest):
    """Publish a post to Instagram via Graph API."""
    from app.edition import is_family_edition
    from app.services.edition_facts import contains_confidential
    if is_family_edition():
        raise HTTPException(
            403,
            "Sin aprobación. Nada se publica hasta que se apruebe el contenido.",
        )
    if contains_confidential(data.caption):
        raise HTTPException(403, "Ese texto incluye datos confidenciales. No se publica.")
    result = await post_to_instagram(caption=data.caption, image_url=data.image_url)
    if not result["posted"]:
        raise HTTPException(400, result.get("error", "Instagram post failed"))
    return result


@router.post("/post/facebook")
async def api_post_to_facebook(data: FacebookPostRequest):
    """Publish a post to Facebook Page via Graph API."""
    from app.edition import is_family_edition
    from app.services.edition_facts import contains_confidential
    if is_family_edition():
        raise HTTPException(
            403,
            "Sin aprobación. Nada se publica hasta que se apruebe el contenido.",
        )
    if contains_confidential(data.message):
        raise HTTPException(403, "Ese texto incluye datos confidenciales. No se publica.")
    result = await post_to_facebook(message=data.message, link=data.link)
    if not result["posted"]:
        raise HTTPException(400, result.get("error", "Facebook post failed"))
    return result


@router.get("/connected-accounts")
async def api_get_social_accounts():
    """Check which social platforms have valid tokens configured."""
    return await get_social_accounts()


# ── Dashboard KPIs ────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard():
    posts = _load_all(_posts_dir())
    campaigns = _load_all(_campaigns_dir())

    drafts = [p for p in posts if p.get("status") == "draft"]
    scheduled = [p for p in posts if p.get("status") == "scheduled"]
    posted = [p for p in posts if p.get("status") == "posted"]

    total_engagement = sum(
        p.get("engagement", {}).get("likes", 0) +
        p.get("engagement", {}).get("comments", 0) +
        p.get("engagement", {}).get("shares", 0)
        for p in posted
    )

    # Posts by platform
    by_platform = {}
    for p in posts:
        plat = p.get("platform", "unknown")
        by_platform[plat] = by_platform.get(plat, 0) + 1

    return {
        "total_posts": len(posts),
        "drafts": len(drafts),
        "scheduled": len(scheduled),
        "posted": len(posted),
        "total_engagement": total_engagement,
        "active_campaigns": len([c for c in campaigns if c.get("status") == "active"]),
        "by_platform": by_platform,
        "recent_posts": posts[:5],
        "campaigns": campaigns[:5],
    }


# ── Content Calendar ──────────────────────────────────────────────────────

@router.get("/calendar")
async def content_calendar(month: Optional[str] = None):
    """Get posts organized by date for calendar view."""
    posts = _load_all(_posts_dir())
    calendar = {}

    for p in posts:
        date_str = p.get("scheduled_for") or p.get("posted_at") or p.get("created_at", "")
        if date_str:
            day = date_str[:10]
            if month and not day.startswith(month):
                continue
            if day not in calendar:
                calendar[day] = []
            calendar[day].append({
                "id": p["id"],
                "platform": p.get("platform"),
                "content": (p.get("content") or "")[:100],
                "status": p.get("status"),
            })

    return {"month": month or "all", "days": calendar}


# ── Accounts / Setup ──────────────────────────────────────────────────────

# ── Business Profile ──────────────────────────────────────────────────────

DEFAULT_PROFILE = {
    "business_name": "Empire Workroom",
    "tagline": "",
    "phone": "",
    "email": "",
    "website": "https://empirebox.store",
    "address": "",
    "city": "Washington",
    "state": "DC",
    "zip": "",
    "bio_short": "",
    "bio_long": "",
    "services": "Custom Drapery, Shades, Blinds, Upholstery, Bedding, Cornices, Valances",
    "target_audience": "Homeowners, Interior Designers, Real Estate Stagers, Commercial Property Managers",
    "style_keywords": "Premium, Custom, Luxury, Handcrafted, Bespoke",
    "brand_colors": "#c9a84c, #1a1a1a, #faf9f7",
    "logo_url": "",
    "owner_name": "",
    "founded_year": "",
    "service_area": "Washington DC Metro Area",
}


class ProfileUpdate(BaseModel):
    business_name: Optional[str] = None
    tagline: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    bio_short: Optional[str] = None
    bio_long: Optional[str] = None
    services: Optional[str] = None
    target_audience: Optional[str] = None
    style_keywords: Optional[str] = None
    brand_colors: Optional[str] = None
    logo_url: Optional[str] = None
    owner_name: Optional[str] = None
    founded_year: Optional[str] = None
    service_area: Optional[str] = None


def _family_default_profile() -> Optional[dict]:
    """Maxine / Max-e start from their own trade, never the Workroom profile."""
    from app.edition import active_business_slug, is_family_edition

    if not is_family_edition():
        return None
    from app.services.leadforge.trade_profile import social_default_profile

    trade = social_default_profile(active_business_slug())
    if trade is None:
        return None
    blank = {k: "" for k in DEFAULT_PROFILE}
    blank.update(trade)
    return blank


def _is_workroom_seed_profile(profile: dict) -> bool:
    return (
        (profile.get("business_name") or "") == DEFAULT_PROFILE["business_name"]
        and (profile.get("services") or "") == DEFAULT_PROFILE["services"]
    )


def _load_profile() -> dict:
    family_default = _family_default_profile()
    if os.path.exists(_profile_file()):
        with open(_profile_file()) as f:
            stored = json.load(f)
        if family_default is None or not _is_workroom_seed_profile(stored):
            return stored
        # A family profile still holding the untouched Workroom seed: replace it.
    default = family_default if family_default is not None else DEFAULT_PROFILE
    with open(_profile_file(), "w") as f:
        json.dump(default, f, indent=2)
    return dict(default)


def _save_profile(profile: dict):
    with open(_profile_file(), "w") as f:
        json.dump(profile, f, indent=2)


@router.get("/profile")
async def get_profile():
    return _load_profile()


@router.put("/profile")
async def update_profile(data: ProfileUpdate):
    profile = _load_profile()
    for field, val in data.model_dump(exclude_none=True).items():
        profile[field] = val
    profile["updated_at"] = datetime.utcnow().isoformat()
    _save_profile(profile)
    return profile

# Default account checklist — every channel Empire needs
DEFAULT_ACCOUNTS = [
    {"id": "email_business", "category": "email", "name": "Business Email", "platform": "Google Workspace / Gmail",
     "description": "Primary business email (e.g. hello@empirebox.store)", "setup_url": "https://workspace.google.com/",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "email_support", "category": "email", "name": "Support Email", "platform": "Google Workspace / Gmail",
     "description": "Customer support email (e.g. support@empirebox.store)", "setup_url": "https://workspace.google.com/",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "instagram", "category": "social", "name": "Instagram Business", "platform": "Instagram",
     "description": "Business profile with portfolio, reels, stories", "setup_url": "https://www.instagram.com/accounts/emailsignup/",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "facebook_page", "category": "social", "name": "Facebook Business Page", "platform": "Facebook",
     "description": "Business page with reviews, services, portfolio", "setup_url": "https://www.facebook.com/pages/create",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "pinterest", "category": "social", "name": "Pinterest Business", "platform": "Pinterest",
     "description": "Boards for room inspiration, before/after, fabric collections", "setup_url": "https://www.pinterest.com/business/create/",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "linkedin", "category": "social", "name": "LinkedIn Company Page", "platform": "LinkedIn",
     "description": "Professional presence for B2B design clients", "setup_url": "https://www.linkedin.com/company/setup/new/",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "tiktok", "category": "social", "name": "TikTok Business", "platform": "TikTok",
     "description": "Short-form video: process shots, reveals, tips", "setup_url": "https://www.tiktok.com/signup",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "google_business", "category": "local", "name": "Google Business Profile", "platform": "Google",
     "description": "Show up in local search, Google Maps, collect reviews", "setup_url": "https://business.google.com/create",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "yelp", "category": "local", "name": "Yelp Business", "platform": "Yelp",
     "description": "Local reviews and discovery", "setup_url": "https://biz.yelp.com/signup_business/new",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "nextdoor", "category": "local", "name": "Nextdoor Business", "platform": "Nextdoor",
     "description": "Neighborhood recommendations and local ads", "setup_url": "https://business.nextdoor.com/",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "houzz", "category": "directory", "name": "Houzz Pro", "platform": "Houzz",
     "description": "Interior design portfolio and lead generation", "setup_url": "https://www.houzz.com/professionals/sign-up",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "thumbtack", "category": "directory", "name": "Thumbtack", "platform": "Thumbtack",
     "description": "Local service marketplace for drapery/upholstery leads", "setup_url": "https://www.thumbtack.com/pro/signup",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "mailchimp", "category": "email_marketing", "name": "Email Marketing", "platform": "Mailchimp / Brevo",
     "description": "Newsletter, drip campaigns, quote follow-ups", "setup_url": "https://login.mailchimp.com/signup/",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "canva", "category": "tools", "name": "Canva Pro", "platform": "Canva",
     "description": "Social media graphics, quote templates, brand kit", "setup_url": "https://www.canva.com/signup",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "later", "category": "tools", "name": "Social Scheduler", "platform": "Later / Buffer",
     "description": "Auto-post to all platforms on schedule", "setup_url": "https://later.com/",
     "status": "not_started", "handle": "", "notes": ""},
    {"id": "domain_email", "category": "email", "name": "Domain Email Setup", "platform": "Cloudflare / Namecheap",
     "description": "Route @empirebox.store emails to Gmail", "setup_url": "https://dash.cloudflare.com/",
     "status": "not_started", "handle": "", "notes": ""},
]


# Workroom-only directory listings (drapery / interior design leads).
_FAMILY_HIDDEN_ACCOUNTS = {"houzz", "thumbtack"}
_FAMILY_ACCOUNT_DESCRIPTIONS = {
    "email_business": "Correo principal del negocio",
    "email_support": "Correo para atención a clientes",
    "pinterest": "Tableros con fotos del proyecto e inspiración",
    "linkedin": "Presencia profesional para aliados y empresas",
    "tiktok": "Videos cortos: recorridos, avances y consejos",
    "mailchimp": "Boletín y seguimiento a interesados",
    "canva": "Piezas gráficas para redes y presentaciones",
    "domain_email": "Correo con dominio propio",
}


def _family_accounts(accounts: list[dict]) -> list[dict]:
    from app.edition import is_family_edition

    if not is_family_edition():
        return accounts
    out = []
    for acc in accounts:
        if acc.get("id") in _FAMILY_HIDDEN_ACCOUNTS:
            continue
        acc = dict(acc)
        if acc.get("id") in _FAMILY_ACCOUNT_DESCRIPTIONS:
            acc["description"] = _FAMILY_ACCOUNT_DESCRIPTIONS[acc["id"]]
        out.append(acc)
    return out


def _load_accounts() -> list[dict]:
    if os.path.exists(_accounts_file()):
        with open(_accounts_file()) as f:
            return _family_accounts(json.load(f))
    # Initialize with defaults
    defaults = _family_accounts(DEFAULT_ACCOUNTS)
    _save_accounts(defaults)
    return defaults


def _save_accounts(accounts: list[dict]):
    with open(_accounts_file(), "w") as f:
        json.dump(accounts, f, indent=2)


class AccountUpdate(BaseModel):
    status: Optional[str] = None  # not_started, in_progress, done, skipped
    handle: Optional[str] = None
    notes: Optional[str] = None


@router.get("/accounts")
async def list_accounts():
    """Get all account setup items with status."""
    accounts = _load_accounts()
    categories = {}
    for a in accounts:
        cat = a.get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(a)

    done = len([a for a in accounts if a.get("status") == "done"])
    total = len(accounts)

    return {
        "accounts": accounts,
        "categories": categories,
        "progress": {"done": done, "total": total, "pct": round(done / total * 100) if total else 0},
    }


@router.put("/accounts/{account_id}")
async def update_account(account_id: str, data: AccountUpdate):
    """Update an account's setup status, handle, or notes."""
    accounts = _load_accounts()
    found = False
    for a in accounts:
        if a["id"] == account_id:
            if data.status is not None:
                a["status"] = data.status
            if data.handle is not None:
                a["handle"] = data.handle
            if data.notes is not None:
                a["notes"] = data.notes
            a["updated_at"] = datetime.utcnow().isoformat()
            found = True
            break
    if not found:
        raise HTTPException(404, "Account not found")
    _save_accounts(accounts)
    return {"updated": True, "account_id": account_id}


@router.post("/accounts/sync")
async def sync_accounts():
    """Check configured social tokens and auto-update accounts.json with connection status."""
    from app.services.social_service import get_social_accounts

    live = await get_social_accounts()
    accounts = _load_accounts()
    synced = []

    # Map live check results to accounts.json entries
    mapping = {
        "instagram": {"category": "social", "platform_match": "instagram"},
        "facebook":  {"category": "social", "platform_match": "facebook"},
    }

    for platform, info in live.items():
        if not info.get("connected"):
            continue
        m = mapping.get(platform)
        if not m:
            continue
        for a in accounts:
            if a.get("category") == m["category"] and m["platform_match"] in a.get("id", "").lower():
                a["status"] = "done"
                handle = info.get("handle") or info.get("page") or ""
                if handle:
                    a["handle"] = handle
                a["notes"] = f"Auto-synced {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} — token verified via Graph API"
                a["updated_at"] = datetime.utcnow().isoformat()
                synced.append({"id": a["id"], "platform": platform, "handle": handle})
                break

    if synced:
        _save_accounts(accounts)

    return {"synced": synced, "live_status": live}


@router.post("/accounts/ai-guide")
async def ai_setup_guide(data: AIContentRequest):
    """Get AI guidance for setting up a specific platform account, using business profile."""
    from app.services.max.ai_router import ai_router, AIMessage

    profile = _load_profile()
    biz = profile.get("business_name", "Empire Workroom")
    city = f"{profile.get('city', 'Washington')}, {profile.get('state', 'DC')}"
    phone = profile.get("phone", "")
    email = profile.get("email", "")
    website = profile.get("website", "")
    address = profile.get("address", "")
    services = profile.get("services", "Custom Drapery, Shades, Blinds, Upholstery, Bedding")
    bio_short = profile.get("bio_short", "")
    bio_long = profile.get("bio_long", "")
    tagline = profile.get("tagline", "")
    owner = profile.get("owner_name", "")
    area = profile.get("service_area", city)
    keywords = profile.get("style_keywords", "Premium, Custom, Luxury")
    audience = profile.get("target_audience", "Homeowners, Interior Designers")

    prompt = (
        f"I'm setting up a {data.platform} account for my business. Here's my info:\n\n"
        f"Business: {biz}\n"
        f"Tagline: {tagline}\n"
        f"Owner: {owner}\n"
        f"Location: {address}, {city}\n"
        f"Service Area: {area}\n"
        f"Phone: {phone}\n"
        f"Email: {email}\n"
        f"Website: {website}\n"
        f"Services: {services}\n"
        f"Target Audience: {audience}\n"
        f"Style: {keywords}\n"
        f"Short Bio: {bio_short}\n"
        f"Long Bio: {bio_long}\n\n"
        f"Give me a COMPLETE step-by-step setup guide for {data.platform}:\n\n"
        f"1. Exact steps to create the account (what to click, what to select)\n"
        f"2. READY-TO-PASTE profile name / username suggestions (3 options)\n"
        f"3. READY-TO-PASTE bio text optimized for {data.platform} (use my real info above)\n"
        f"4. Profile picture and cover/header image specs and what to use\n"
        f"5. Every setting to configure (business category, contact info, hours, etc.)\n"
        f"6. First 3 things to post/do after account is created\n"
        f"7. SEO and discoverability tips for this platform\n\n"
        f"Use my ACTUAL business info — not placeholders. Make everything copy-paste ready."
    )

    try:
        response = await ai_router.chat(
            messages=[AIMessage(role="user", content=prompt)],
            desk="marketing",
            system_prompt=(
                f"You are Nova, the AI marketing manager for {biz}. "
                f"Generate specific, actionable setup guides with REAL copy-paste text using the business info provided. "
                f"Never use placeholders like [Your Business]. Use the actual info."
            ),
        )
        return {
            "platform": data.platform,
            "guide": response.content,
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, f"AI guide generation failed: {e}")


# ── LeadForge feed (read-only) ─────────────────────────────────────────────
# Social profiles found by LeadForge's free contact lookup (prospect websites
# linking to Instagram / Facebook / LinkedIn). Use as an engage/follow list.
# DMs stay drafts (LeadForge prospect drafts); nothing is posted or sent here.

@router.get("/prospect-targets")
async def leadforge_prospect_targets(limit: int = 100):
    from app.services.leadforge.prospect_ops import social_targets
    return social_targets(limit=max(1, min(int(limit), 500)))
