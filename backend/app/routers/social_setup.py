"""
SocialForge Account Setup Wizard — Backend (Part I + Part II)
Business profiles, setup wizard, token harvest, verify, test-publish, draft publish, status.
All data in ~/empire-repo/backend/data/empire.db via sqlite3.
"""
import os
import re
import json
import sqlite3
import shutil
import logging
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import httpx

logger = logging.getLogger(__name__)

router = APIRouter(tags=["social-setup"])

DB_PATH = os.getenv(
    "EMPIRE_TASK_DB",
    str(Path(__file__).resolve().parent.parent.parent / "data" / "empire.db"),
)
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
GRAPH_API = "https://graph.facebook.com/v21.0"


# ── Platform Capabilities ────────────────────────────────────────────────────

PLATFORM_CAPABILITIES = {
    "facebook": {
        "create_via_api": True,
        "verify_via_api": True,
        "publish_via_api": True,
        "signup_url": "https://www.facebook.com/pages/create",
        "requires": [],
    },
    "instagram": {
        "create_via_api": False,
        "verify_via_api": True,
        "publish_via_api": True,
        "signup_url": "https://www.instagram.com/accounts/emailsignup/",
        "requires": ["facebook_page_linked"],
    },
    "tiktok": {
        "create_via_api": False,
        "verify_via_api": False,
        "publish_via_api": False,
        "signup_url": "https://www.tiktok.com/signup",
        "requires": [],
    },
    "linkedin": {
        "create_via_api": False,
        "verify_via_api": False,
        "publish_via_api": False,
        "signup_url": "https://www.linkedin.com/company/setup/new/",
        "requires": [],
    },
    "pinterest": {
        "create_via_api": False,
        "verify_via_api": False,
        "publish_via_api": False,
        "signup_url": "https://www.pinterest.com/business/create/",
        "requires": [],
    },
    "google_business": {
        "create_via_api": False,
        "verify_via_api": False,
        "publish_via_api": False,
        "signup_url": "https://business.google.com/create",
        "requires": [],
    },
}


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def _dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ── Safe .env helper ─────────────────────────────────────────────────────────

def safe_update_env(key: str, value: str):
    """Backup .env, remove existing key line, append new key=value. No duplicates."""
    env_path = str(ENV_PATH)
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write(f"{key}={value}\n")
        return

    # Backup
    backup = env_path + f".bak.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(env_path, backup)

    with open(env_path, "r") as f:
        lines = f.readlines()

    # Remove any existing line for this key
    pattern = re.compile(rf"^{re.escape(key)}\s*=")
    new_lines = [l for l in lines if not pattern.match(l)]

    # Ensure trailing newline before append
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    new_lines.append(f"{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    # Also update the running process env
    os.environ[key] = value


# ── Table init on import ──────────────────────────────────────────────────────

def _init_tables():
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS business_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_key TEXT UNIQUE NOT NULL,
                business_name TEXT NOT NULL,
                tagline TEXT,
                bio_short TEXT,
                bio_long TEXT,
                category TEXT,
                subcategory TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                city TEXT,
                state TEXT,
                zip TEXT,
                country TEXT DEFAULT 'US',
                website TEXT,
                logo_url TEXT,
                cover_photo_url TEXT,
                hours TEXT,
                social_handles TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS social_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_unit TEXT NOT NULL,
                platform TEXT NOT NULL,
                account_name TEXT,
                account_id TEXT,
                access_token TEXT,
                token_expires_at TIMESTAMP,
                status TEXT DEFAULT 'not_configured',
                last_posted_at TIMESTAMP,
                post_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(business_unit, platform)
            );

            CREATE TABLE IF NOT EXISTS social_post_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                business_unit TEXT NOT NULL,
                platform TEXT NOT NULL,
                status TEXT NOT NULL,
                external_post_id TEXT,
                external_url TEXT,
                error TEXT,
                published_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ALTER social_accounts — add new columns (try/except each)
        alter_cols = [
            ("last_attempted_at", "TIMESTAMP"),
            ("last_verified_at", "TIMESTAMP"),
            ("verification_result", "TEXT"),
            ("last_error", "TEXT"),
            ("next_owner_action", "TEXT"),
            ("setup_progress", "TEXT DEFAULT 'not_started'"),
        ]
        for col_name, col_type in alter_cols:
            try:
                conn.execute(f"ALTER TABLE social_accounts ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass  # column already exists

        conn.commit()

        # Seed business profiles if empty
        existing = conn.execute("SELECT COUNT(*) FROM business_profiles").fetchone()[0]
        if existing == 0:
            conn.execute("""
                INSERT INTO business_profiles
                    (business_key, business_name, tagline, bio_short, category, email, phone, address, city, state, zip, website, social_handles)
                VALUES
                    ('workroom', 'Empire Workroom', 'Custom Upholstery & Fabrication',
                     'Custom Window Treatments & Upholstery | AI-Powered Design | DC • MD • VA',
                     'Interior Designer', 'workroom@empirebox.store', '(703) 213-6484',
                     '5124 Frolich Ln', 'Hyattsville', 'MD', '20781',
                     'studio.empirebox.store',
                     '{"instagram":"empire_workroom","facebook":"Empire Workroom"}')
            """)
            conn.execute("""
                INSERT INTO business_profiles
                    (business_key, business_name, tagline, bio_short, category, email, phone, address, city, state, zip, website, social_handles)
                VALUES
                    ('woodcraft', 'Empire WoodCraft', 'Custom Woodwork & CNC Fabrication',
                     'Custom Woodwork & CNC | Built-ins • Furniture • Millwork | DC • MD • VA',
                     'Carpenter', 'woodcraft@empirebox.store', '(703) 213-6484',
                     '5124 Frolich Ln', 'Hyattsville', 'MD', '20781',
                     'studio.empirebox.store',
                     '{"instagram":"empirewoodcraft","facebook":"Empire WoodCraft"}')
            """)
            conn.commit()
            logger.info("Seeded 2 business profiles (workroom, woodcraft)")

    except Exception as e:
        logger.error("social_setup table init failed: %s", e)
    finally:
        conn.close()


_init_tables()


# ── Credential Routing ────────────────────────────────────────────────────────

def get_publish_credentials(business_key: str, platform: str) -> dict | None:
    """Return the correct token/page_id for a specific business+platform.
    NEVER falls back to another business's token.
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT access_token, account_id, account_name FROM social_accounts WHERE business_unit = ? AND platform = ?",
            (business_key, platform),
        ).fetchone()
        if not row:
            return None
        d = _dict(row)
        if not d.get("access_token"):
            return None
        # Normalize to common keys used by publish logic
        return {
            "token": d["access_token"],
            "account_id": d.get("account_id", ""),
            "page_id": d.get("account_id", ""),  # for FB, account_id stores the page_id
            "account_name": d.get("account_name", ""),
        }
    finally:
        conn.close()


# ── Pydantic models ──────────────────────────────────────────────────────────

class BusinessProfileUpdate(BaseModel):
    business_name: Optional[str] = None
    tagline: Optional[str] = None
    bio_short: Optional[str] = None
    bio_long: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    cover_photo_url: Optional[str] = None
    hours: Optional[str] = None
    social_handles: Optional[str] = None


class TestPublishRequest(BaseModel):
    content: Optional[str] = None
    media_url: Optional[str] = None


class PublishDraftsRequest(BaseModel):
    business_key: Optional[str] = None  # if None, publish all businesses


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Business Profiles
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/business-profiles")
async def list_business_profiles():
    """List all business profiles."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM business_profiles ORDER BY business_key").fetchall()
        return _dicts(rows)
    finally:
        conn.close()


@router.get("/business-profiles/{key}")
async def get_business_profile(key: str):
    """Get a single business profile by key."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM business_profiles WHERE business_key = ?", (key,)).fetchone()
        if not row:
            raise HTTPException(404, f"Business profile '{key}' not found")
        return _dict(row)
    finally:
        conn.close()


@router.put("/business-profiles/{key}")
async def update_business_profile(key: str, data: BusinessProfileUpdate):
    """Update a business profile."""
    conn = _get_conn()
    try:
        existing = conn.execute("SELECT id FROM business_profiles WHERE business_key = ?", (key,)).fetchone()
        if not existing:
            raise HTTPException(404, f"Business profile '{key}' not found")

        updates = data.model_dump(exclude_none=True)
        if not updates:
            raise HTTPException(400, "No fields to update")

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [key]
        conn.execute(f"UPDATE business_profiles SET {set_clause} WHERE business_key = ?", values)
        conn.commit()

        row = conn.execute("SELECT * FROM business_profiles WHERE business_key = ?", (key,)).fetchone()
        return _dict(row)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Setup Wizard
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/socialforge/setup-wizard/{business_key}")
async def setup_wizard(business_key: str):
    """Returns all platform signup URLs, pre-fill data from business_profiles,
    and progress from social_accounts."""
    conn = _get_conn()
    try:
        profile = conn.execute(
            "SELECT * FROM business_profiles WHERE business_key = ?", (business_key,)
        ).fetchone()
        if not profile:
            raise HTTPException(404, f"Business '{business_key}' not found")

        profile_dict = _dict(profile)

        # Get existing social account records for this business
        accounts = conn.execute(
            "SELECT * FROM social_accounts WHERE business_unit = ?", (business_key,)
        ).fetchall()
        account_map = {row["platform"]: _dict(row) for row in accounts}

        platforms = {}
        for plat, caps in PLATFORM_CAPABILITIES.items():
            acct = account_map.get(plat, {})
            platforms[plat] = {
                **caps,
                "status": acct.get("status", "not_configured"),
                "setup_progress": acct.get("setup_progress", "not_started"),
                "handle": acct.get("account_name", ""),
                "account_id": acct.get("account_id", ""),
                "last_verified_at": acct.get("last_verified_at"),
                "last_error": acct.get("last_error"),
                "next_owner_action": acct.get("next_owner_action"),
            }

        # Parse social handles for pre-fill hints
        handles = {}
        try:
            handles = json.loads(profile_dict.get("social_handles") or "{}")
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "business_key": business_key,
            "business_profile": profile_dict,
            "suggested_handles": handles,
            "platforms": platforms,
            "prefill": {
                "business_name": profile_dict.get("business_name", ""),
                "tagline": profile_dict.get("tagline", ""),
                "bio_short": profile_dict.get("bio_short", ""),
                "category": profile_dict.get("category", ""),
                "email": profile_dict.get("email", ""),
                "phone": profile_dict.get("phone", ""),
                "address": profile_dict.get("address", ""),
                "city": profile_dict.get("city", ""),
                "state": profile_dict.get("state", ""),
                "zip": profile_dict.get("zip", ""),
                "website": profile_dict.get("website", ""),
            },
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Verify Connection
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/socialforge/verify-connection/{business_key}/{platform}")
async def verify_connection(business_key: str, platform: str):
    """Check Meta Graph API for facebook/instagram connection.
    Updates social_accounts + .env."""
    if platform not in ("facebook", "instagram"):
        raise HTTPException(400, f"Verify via API not supported for '{platform}'. Manual setup required.")

    token = os.getenv("META_ACCESS_TOKEN", "")
    if not token:
        raise HTTPException(400, "META_ACCESS_TOKEN not set in .env — complete OAuth first")

    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if platform == "facebook":
                resp = await client.get(
                    f"{GRAPH_API}/me",
                    params={"fields": "id,name,category", "access_token": token},
                )
                if resp.status_code != 200:
                    _upsert_social_account(conn, business_key, platform, {
                        "status": "error",
                        "last_attempted_at": now,
                        "last_error": resp.text,
                        "verification_result": "failed",
                        "next_owner_action": "Check META_ACCESS_TOKEN — may be expired",
                    })
                    conn.commit()
                    raise HTTPException(400, f"Facebook verify failed: {resp.text}")

                data = resp.json()
                _upsert_social_account(conn, business_key, platform, {
                    "status": "connected",
                    "page_id": data.get("id", ""),
                    "handle": data.get("name", ""),
                    "token": token,
                    "last_attempted_at": now,
                    "last_verified_at": now,
                    "verification_result": "success",
                    "setup_progress": "complete",
                    "last_error": None,
                    "next_owner_action": None,
                })
                conn.commit()

                # Save page token to .env
                safe_update_env(f"FACEBOOK_PAGE_TOKEN_{business_key.upper()}", token)
                safe_update_env("FACEBOOK_PAGE_TOKEN", token)

                return {"verified": True, "platform": "facebook", "page_name": data.get("name"), "page_id": data.get("id")}

            elif platform == "instagram":
                # First need the FB page to get the linked IG account
                me_resp = await client.get(
                    f"{GRAPH_API}/me",
                    params={"fields": "id,instagram_business_account", "access_token": token},
                )
                if me_resp.status_code != 200:
                    _upsert_social_account(conn, business_key, platform, {
                        "status": "error",
                        "last_attempted_at": now,
                        "last_error": me_resp.text,
                        "verification_result": "failed",
                        "next_owner_action": "Check META_ACCESS_TOKEN",
                    })
                    conn.commit()
                    raise HTTPException(400, f"Instagram verify failed (page lookup): {me_resp.text}")

                page_data = me_resp.json()
                ig_account = page_data.get("instagram_business_account")
                if not ig_account:
                    _upsert_social_account(conn, business_key, platform, {
                        "status": "not_linked",
                        "last_attempted_at": now,
                        "verification_result": "no_ig_linked",
                        "last_error": "No Instagram Business Account linked to this Facebook Page",
                        "next_owner_action": "Link an Instagram Business Account to your Facebook Page in Meta Business Suite",
                    })
                    conn.commit()
                    return {"verified": False, "error": "No Instagram Business Account linked to Facebook Page"}

                ig_id = ig_account["id"]
                ig_resp = await client.get(
                    f"{GRAPH_API}/{ig_id}",
                    params={"fields": "id,username,name", "access_token": token},
                )
                if ig_resp.status_code != 200:
                    _upsert_social_account(conn, business_key, platform, {
                        "status": "error",
                        "last_attempted_at": now,
                        "last_error": ig_resp.text,
                        "verification_result": "failed",
                    })
                    conn.commit()
                    raise HTTPException(400, f"Instagram verify failed: {ig_resp.text}")

                ig_data = ig_resp.json()
                _upsert_social_account(conn, business_key, platform, {
                    "status": "connected",
                    "account_id": ig_id,
                    "handle": ig_data.get("username", ""),
                    "token": token,
                    "page_id": page_data.get("id", ""),
                    "last_attempted_at": now,
                    "last_verified_at": now,
                    "verification_result": "success",
                    "setup_progress": "complete",
                    "last_error": None,
                    "next_owner_action": None,
                })
                conn.commit()

                safe_update_env(f"INSTAGRAM_TOKEN_{business_key.upper()}", token)

                return {
                    "verified": True,
                    "platform": "instagram",
                    "username": ig_data.get("username"),
                    "account_id": ig_id,
                }

    finally:
        conn.close()


def _upsert_social_account(conn: sqlite3.Connection, business_key: str, platform: str, fields: dict):
    """Insert or update a social_accounts row.
    Accepts logical field names and maps them to actual DB columns:
      handle -> account_name, token -> access_token, page_id -> account_id (for FB)
    """
    # Map logical names to actual column names
    col_map = {
        "handle": "account_name",
        "token": "access_token",
        "updated_at": None,  # column does not exist in table, skip
    }
    mapped = {}
    for k, v in fields.items():
        dest = col_map.get(k, k)
        if dest is None:
            continue
        mapped[dest] = v

    # page_id for facebook is stored as account_id
    if "page_id" in mapped and platform == "facebook":
        mapped["account_id"] = mapped.pop("page_id")
    elif "page_id" in mapped:
        mapped.pop("page_id")  # instagram stores its own account_id separately

    existing = conn.execute(
        "SELECT id FROM social_accounts WHERE business_unit = ? AND platform = ?",
        (business_key, platform),
    ).fetchone()

    if existing:
        set_parts = ", ".join(f"{k} = ?" for k in mapped)
        vals = list(mapped.values()) + [business_key, platform]
        conn.execute(
            f"UPDATE social_accounts SET {set_parts} WHERE business_unit = ? AND platform = ?",
            vals,
        )
    else:
        mapped["business_unit"] = business_key
        mapped["platform"] = platform
        mapped["created_at"] = datetime.now(timezone.utc).isoformat()
        cols = ", ".join(mapped.keys())
        placeholders = ", ".join("?" for _ in mapped)
        conn.execute(f"INSERT INTO social_accounts ({cols}) VALUES ({placeholders})", list(mapped.values()))


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Token Harvest
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/socialforge/harvest-tokens")
async def harvest_tokens():
    """Read META_ACCESS_TOKEN, call Graph API me/accounts, discover all pages +
    Instagram links, save tokens to .env, update social_accounts."""
    token = os.getenv("META_ACCESS_TOKEN", "")
    if not token:
        raise HTTPException(400, "META_ACCESS_TOKEN not set in .env")

    conn = _get_conn()
    harvested = []
    now = datetime.now(timezone.utc).isoformat()

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            # Get all pages this user/token manages
            resp = await client.get(
                f"{GRAPH_API}/me/accounts",
                params={"fields": "id,name,access_token,category,instagram_business_account", "access_token": token},
            )
            if resp.status_code != 200:
                raise HTTPException(400, f"Graph API me/accounts failed: {resp.text}")

            pages = resp.json().get("data", [])
            if not pages:
                return {"harvested": [], "message": "No pages found for this token"}

            for page in pages:
                page_id = page.get("id", "")
                page_name = page.get("name", "")
                page_token = page.get("access_token", "")
                ig_account = page.get("instagram_business_account")

                # Try to match page to a business_key based on name
                business_key = _match_page_to_business(conn, page_name)

                entry = {
                    "page_id": page_id,
                    "page_name": page_name,
                    "business_key": business_key,
                    "facebook_saved": False,
                    "instagram_saved": False,
                }

                if page_token and business_key:
                    # Save Facebook page token
                    env_key = f"FACEBOOK_PAGE_TOKEN_{business_key.upper()}"
                    safe_update_env(env_key, page_token)
                    entry["facebook_saved"] = True

                    _upsert_social_account(conn, business_key, "facebook", {
                        "status": "connected",
                        "page_id": page_id,
                        "handle": page_name,
                        "token": page_token,
                        "last_verified_at": now,
                        "verification_result": "harvested",
                        "setup_progress": "complete",
                    })

                    # Check for linked Instagram
                    if ig_account:
                        ig_id = ig_account["id"]
                        ig_resp = await client.get(
                            f"{GRAPH_API}/{ig_id}",
                            params={"fields": "id,username,name", "access_token": page_token},
                        )
                        if ig_resp.status_code == 200:
                            ig_data = ig_resp.json()
                            ig_env_key = f"INSTAGRAM_TOKEN_{business_key.upper()}"
                            safe_update_env(ig_env_key, page_token)
                            entry["instagram_saved"] = True
                            entry["instagram_username"] = ig_data.get("username", "")

                            _upsert_social_account(conn, business_key, "instagram", {
                                "status": "connected",
                                "account_id": ig_id,
                                "handle": ig_data.get("username", ""),
                                "token": page_token,
                                "page_id": page_id,
                                "last_verified_at": now,
                                "verification_result": "harvested",
                                "setup_progress": "complete",
                            })

                harvested.append(entry)

            conn.commit()

        return {"harvested": harvested, "pages_found": len(pages)}

    finally:
        conn.close()


def _match_page_to_business(conn: sqlite3.Connection, page_name: str) -> str | None:
    """Try to match a Facebook page name to a business_key in business_profiles."""
    rows = conn.execute("SELECT business_key, business_name, social_handles FROM business_profiles").fetchall()
    page_lower = page_name.lower()

    for row in rows:
        bk = row["business_key"]
        bn = (row["business_name"] or "").lower()

        # Direct name match
        if bn and bn in page_lower or page_lower in bn:
            return bk

        # Check social_handles JSON
        try:
            handles = json.loads(row["social_handles"] or "{}")
            fb_handle = (handles.get("facebook") or "").lower()
            if fb_handle and (fb_handle in page_lower or page_lower in fb_handle):
                return bk
        except (json.JSONDecodeError, TypeError):
            pass

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Test Publish
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/socialforge/test-publish/{business_key}/{platform}")
async def test_publish(business_key: str, platform: str, data: TestPublishRequest = None):
    """Attempt a real test publish to the specified platform.
    Stores result in social_post_results."""
    if data is None:
        data = TestPublishRequest()

    creds = get_publish_credentials(business_key, platform)
    if not creds:
        raise HTTPException(400, f"No credentials found for {business_key}/{platform}. Run verify-connection first.")

    token = creds["token"]
    page_id = creds.get("page_id", "")
    account_id = creds.get("account_id", "")
    now = datetime.now(timezone.utc).isoformat()
    content = data.content or f"Test post from Empire SocialForge - {business_key} - {now}"

    conn = _get_conn()
    try:
        result = {"status": "failed", "post_id": None, "error": None, "api_response": None}

        async with httpx.AsyncClient(timeout=30) as client:
            if platform == "facebook":
                if not page_id:
                    result["error"] = "No page_id stored for this Facebook account"
                else:
                    resp = await client.post(
                        f"{GRAPH_API}/{page_id}/feed",
                        params={"message": content, "access_token": token},
                    )
                    result["api_response"] = resp.text
                    if resp.status_code == 200:
                        result["status"] = "success"
                        result["post_id"] = resp.json().get("id", "")
                    else:
                        result["error"] = resp.text

            elif platform == "instagram":
                if not data.media_url:
                    result["error"] = "Instagram requires media_url for publishing"
                elif not account_id:
                    result["error"] = "No Instagram account_id stored. Run verify-connection first."
                else:
                    # Step 1: Create container
                    container_resp = await client.post(
                        f"{GRAPH_API}/{account_id}/media",
                        params={
                            "image_url": data.media_url,
                            "caption": content,
                            "access_token": token,
                        },
                    )
                    if container_resp.status_code != 200:
                        result["error"] = f"Container creation failed: {container_resp.text}"
                        result["api_response"] = container_resp.text
                    else:
                        container_id = container_resp.json().get("id")
                        # Step 2: Publish
                        pub_resp = await client.post(
                            f"{GRAPH_API}/{account_id}/media_publish",
                            params={"creation_id": container_id, "access_token": token},
                        )
                        result["api_response"] = pub_resp.text
                        if pub_resp.status_code == 200:
                            result["status"] = "success"
                            result["post_id"] = pub_resp.json().get("id", "")
                        else:
                            result["error"] = pub_resp.text
            else:
                result["error"] = f"Publishing not implemented for '{platform}'"

        # Store result in DB
        import uuid as _uuid
        internal_post_id = f"test-{_uuid.uuid4().hex[:8]}"
        conn.execute(
            """INSERT INTO social_post_results
               (post_id, business_unit, platform, status, external_post_id, error, published_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (internal_post_id, business_key, platform, result["status"],
             result.get("post_id"), result.get("error"),
             now if result["status"] == "success" else None, now),
        )
        conn.commit()

        if result["status"] == "success":
            return {"published": True, "post_id": result["post_id"], "platform": platform, "business_key": business_key}
        else:
            raise HTTPException(400, result.get("error", "Publish failed"))

    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Publish Drafts
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/socialforge/publish-drafts")
async def publish_drafts(req: PublishDraftsRequest = None):
    """Publish all draft posts to their target platforms using correct per-business credentials."""
    if req is None:
        req = PublishDraftsRequest()

    # Load drafts from the JSON-based socialforge posts
    posts_dir = os.path.expanduser("~/empire-repo/backend/data/socialforge/posts")
    if not os.path.isdir(posts_dir):
        return {"published": [], "errors": [], "message": "No posts directory found"}

    published = []
    errors = []
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()

    try:
        for fname in os.listdir(posts_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(posts_dir, fname)
            with open(fpath) as f:
                post = json.load(f)

            if post.get("status") != "draft":
                continue

            platform = post.get("platform", "")
            content = post.get("content", "")
            media_url = post.get("media_url")

            # Determine business_key — check post field or default to workroom
            business_key = post.get("business_key", "workroom")
            if req.business_key and business_key != req.business_key:
                continue

            creds = get_publish_credentials(business_key, platform)
            if not creds:
                errors.append({
                    "post_id": post.get("id"),
                    "error": f"No credentials for {business_key}/{platform}",
                })
                continue

            token = creds["token"]
            page_id = creds.get("page_id", "")
            account_id = creds.get("account_id", "")
            result = {"status": "failed", "post_id": None, "error": None}

            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    if platform == "facebook" and page_id:
                        hashtags = post.get("hashtags", "")
                        full_content = f"{content}\n\n{hashtags}".strip() if hashtags else content
                        resp = await client.post(
                            f"{GRAPH_API}/{page_id}/feed",
                            params={"message": full_content, "access_token": token},
                        )
                        if resp.status_code == 200:
                            result = {"status": "success", "post_id": resp.json().get("id", "")}
                        else:
                            result["error"] = resp.text

                    elif platform == "instagram" and account_id and media_url:
                        hashtags = post.get("hashtags", "")
                        full_caption = f"{content}\n\n{hashtags}".strip() if hashtags else content
                        container_resp = await client.post(
                            f"{GRAPH_API}/{account_id}/media",
                            params={"image_url": media_url, "caption": full_caption, "access_token": token},
                        )
                        if container_resp.status_code == 200:
                            cid = container_resp.json().get("id")
                            pub_resp = await client.post(
                                f"{GRAPH_API}/{account_id}/media_publish",
                                params={"creation_id": cid, "access_token": token},
                            )
                            if pub_resp.status_code == 200:
                                result = {"status": "success", "post_id": pub_resp.json().get("id", "")}
                            else:
                                result["error"] = pub_resp.text
                        else:
                            result["error"] = container_resp.text
                    else:
                        result["error"] = f"Cannot publish to {platform} (missing creds or unsupported)"

            except Exception as e:
                result["error"] = str(e)

            # Store publish result
            import uuid as _uuid
            conn.execute(
                """INSERT INTO social_post_results
                   (post_id, business_unit, platform, status, external_post_id, error, published_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (post.get("id", _uuid.uuid4().hex[:8]), business_key, platform,
                 result["status"], result.get("post_id"), result.get("error"),
                 now if result["status"] == "success" else None, now),
            )

            if result["status"] == "success":
                # Update the draft JSON file to "posted"
                post["status"] = "posted"
                post["posted_at"] = now
                post["external_post_id"] = result.get("post_id", "")
                post["updated_at"] = now
                with open(fpath, "w") as f:
                    json.dump(post, f, indent=2)
                published.append({"post_id": post.get("id"), "platform": platform, "external_id": result.get("post_id")})
            else:
                errors.append({"post_id": post.get("id"), "platform": platform, "error": result.get("error")})

        conn.commit()

        return {
            "published": published,
            "errors": errors,
            "total_published": len(published),
            "total_errors": len(errors),
        }

    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Status
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/socialforge/status")
async def socialforge_status():
    """Full status of all accounts + publish results + command readiness."""
    conn = _get_conn()
    try:
        # All social accounts
        accounts = _dicts(conn.execute(
            "SELECT * FROM social_accounts ORDER BY business_unit, platform"
        ).fetchall())

        # Recent publish results
        results = _dicts(conn.execute(
            "SELECT * FROM social_post_results ORDER BY created_at DESC LIMIT 50"
        ).fetchall())

        # Business profiles
        profiles = _dicts(conn.execute(
            "SELECT business_key, business_name FROM business_profiles ORDER BY business_key"
        ).fetchall())

        # Compute readiness per business
        readiness = {}
        for profile in profiles:
            bk = profile["business_key"]
            bk_accounts = [a for a in accounts if a.get("business_unit") == bk]
            connected = [a for a in bk_accounts if a.get("status") in ("connected", "active")]
            readiness[bk] = {
                "business_name": profile["business_name"],
                "total_accounts": len(bk_accounts),
                "connected": len(connected),
                "platforms": {a["platform"]: a.get("status", "unknown") for a in bk_accounts},
                "can_publish_facebook": any(
                    a["platform"] == "facebook" and a.get("status") in ("connected", "active") and a.get("access_token")
                    for a in bk_accounts
                ),
                "can_publish_instagram": any(
                    a["platform"] == "instagram" and a.get("status") in ("connected", "active") and a.get("access_token")
                    for a in bk_accounts
                ),
            }

        # Env token presence (no values exposed)
        env_tokens = {
            "META_ACCESS_TOKEN": bool(os.getenv("META_ACCESS_TOKEN")),
            "FACEBOOK_PAGE_TOKEN": bool(os.getenv("FACEBOOK_PAGE_TOKEN")),
            "INSTAGRAM_API_TOKEN": bool(os.getenv("INSTAGRAM_API_TOKEN")),
        }

        return {
            "accounts": accounts,
            "recent_publish_results": results,
            "readiness": readiness,
            "env_tokens_present": env_tokens,
            "platform_capabilities": PLATFORM_CAPABILITIES,
        }
    finally:
        conn.close()
