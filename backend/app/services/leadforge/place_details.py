"""
Google Place Details enrichment (website + phone) for Google-sourced prospects.

Approved Oct 4, 2026 with a HARD cap of $10 per month:
  * Place Details with website/phone bills on the Enterprise SKU: first 1,000 calls per month
    free, then about $20 per 1,000 (about $0.02 per call).
  * FREE_CALLS = 1000. Paid calls allowed = $10 / $0.02 = 500. HARD_CAP = 1500 calls/month.
  * Batch runs stay inside the free 1,000 unless allow_paid=True. Nothing ever goes past HARD_CAP.
  * Every call is counted in google_api_usage (month, sku) before it is made.
  * Only our own calls are counted. Other uses of the same Google key are not visible here.

Flag: LEADFORGE_PLACE_DETAILS=0 turns it off. No key (GOOGLE_PLACES_API_KEY) -> returns
status "needs_key" and does nothing.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.services.leadforge import growth

SKU = "place_details_enterprise"
FREE_CALLS = int(os.getenv("PLACE_DETAILS_FREE_CALLS", "1000"))
PRICE_PER_CALL = 0.02
MONTHLY_BUDGET_USD = float(os.getenv("PLACE_DETAILS_MONTHLY_BUDGET", "10"))
HARD_CAP = FREE_CALLS + int(round(MONTHLY_BUDGET_USD / PRICE_PER_CALL))


def _key() -> str:
    return os.getenv("GOOGLE_PLACES_API_KEY", "")


def enabled() -> bool:
    return os.getenv("LEADFORGE_PLACE_DETAILS", "1") not in ("0", "false", "off")


def _month() -> str:
    # Google bills per calendar month (Pacific time); UTC month is close enough with the margin below.
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _ensure(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS google_api_usage (
        month TEXT NOT NULL, sku TEXT NOT NULL, calls INTEGER NOT NULL DEFAULT 0,
        errors INTEGER NOT NULL DEFAULT 0, updated_at TEXT,
        PRIMARY KEY (month, sku))""")


def usage() -> dict:
    with growth._db() as conn:
        _ensure(conn)
        r = conn.execute("SELECT calls, errors FROM google_api_usage WHERE month=? AND sku=?", (_month(), SKU)).fetchone()
    calls = r["calls"] if r else 0
    paid = max(0, calls - FREE_CALLS)
    return {"month": _month(), "sku": SKU, "calls": calls, "errors": r["errors"] if r else 0,
            "free_calls": FREE_CALLS, "hard_cap": HARD_CAP, "free_left": max(0, FREE_CALLS - calls),
            "est_cost_usd": round(paid * PRICE_PER_CALL, 2), "budget_usd": MONTHLY_BUDGET_USD,
            "key_configured": bool(_key()), "enabled": enabled()}


def _reserve(allow_paid: bool) -> bool:
    """Atomically count one call if it fits under the cap. Returns False if not allowed."""
    limit = HARD_CAP if allow_paid else FREE_CALLS
    with growth._db() as conn:
        _ensure(conn)
        conn.execute("BEGIN IMMEDIATE")
        r = conn.execute("SELECT calls FROM google_api_usage WHERE month=? AND sku=?", (_month(), SKU)).fetchone()
        calls = r["calls"] if r else 0
        if calls >= min(limit, HARD_CAP):
            return False
        conn.execute("""INSERT INTO google_api_usage (month, sku, calls, updated_at) VALUES (?,?,1,datetime('now'))
                        ON CONFLICT(month, sku) DO UPDATE SET calls = calls + 1, updated_at = datetime('now')""",
                     (_month(), SKU))
    return True


def _error():
    with growth._db() as conn:
        _ensure(conn)
        conn.execute("UPDATE google_api_usage SET errors = errors + 1 WHERE month=? AND sku=?", (_month(), SKU))


def _clean_site(url):
    if not url:
        return url
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    u = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(u.query) if not k.lower().startswith("utm_")]
    return urlunsplit((u.scheme, u.netloc, u.path, urlencode(q), ""))


def fetch_details(place_id: str, client: httpx.Client) -> dict:
    """Places API (New) first; falls back to the legacy endpoint the finder already uses. One counted call."""
    r = client.get(f"https://places.googleapis.com/v1/places/{place_id}",
                   headers={"X-Goog-Api-Key": _key(), "X-Goog-FieldMask": "websiteUri,nationalPhoneNumber"})
    if r.status_code == 200:
        d = r.json()
        return {"website": _clean_site(d.get("websiteUri")), "phone": d.get("nationalPhoneNumber"), "api": "places_new"}
    if r.status_code in (403, 404) and ("SERVICE_DISABLED" in r.text or "PERMISSION_DENIED" in r.text or r.status_code == 403):
        r2 = client.get("https://maps.googleapis.com/maps/api/place/details/json",
                        params={"place_id": place_id, "fields": "website,formatted_phone_number", "key": _key()})
        d = r2.json() if r2.status_code == 200 else {}
        if d.get("status") == "OK":
            res = d.get("result") or {}
            return {"website": _clean_site(res.get("website")), "phone": res.get("formatted_phone_number"), "api": "legacy"}
        raise RuntimeError(f"legacy {d.get('status') or r2.status_code}: {(d.get('error_message') or '')[:120]}")
    raise RuntimeError(f"places_new HTTP {r.status_code}: {r.text[:160]}")


def enrich(limit: int = 25, prospect_ids: Optional[list] = None, allow_paid: bool = False) -> dict:
    if not _key():
        return {"status": "needs_key", "note": "Set GOOGLE_PLACES_API_KEY to enable Place Details.", **usage()}
    if not enabled():
        return {"status": "disabled", "note": "LEADFORGE_PLACE_DETAILS=0", **usage()}
    limit = max(1, min(int(limit or 25), 200))
    with growth._db() as conn:
        if prospect_ids:
            qs = ",".join("?" * len(prospect_ids))
            rows = conn.execute(f"""SELECT id, name, external_id, website, phone FROM prospects
                                    WHERE id IN ({qs}) AND source='google_places' AND COALESCE(external_id,'')<>''""",
                                [int(i) for i in prospect_ids]).fetchall()
        else:
            rows = conn.execute("""SELECT id, name, external_id, website, phone FROM prospects
                                   WHERE source='google_places' AND COALESCE(external_id,'')<>''
                                     AND (COALESCE(website,'')='' OR COALESCE(phone,'')='')
                                     AND COALESCE(enrichment_note,'') NOT LIKE '%place_details:%'
                                   ORDER BY score DESC LIMIT ?""", (limit,)).fetchall()
    done, stopped = [], None
    with httpx.Client(timeout=12) as client:
        for r in rows:
            if not _reserve(allow_paid):
                stopped = "free_tier_reached" if not allow_paid else "hard_cap_reached"
                break
            try:
                d = fetch_details(r["external_id"], client)
            except Exception as e:
                _error()
                done.append({"id": r["id"], "name": r["name"], "error": str(e)[:160]})
                if "REQUEST_DENIED" in str(e) or "API key" in str(e):
                    stopped = "key_rejected"
                    break
                continue
            with growth._db() as conn:
                conn.execute("""UPDATE prospects SET website = COALESCE(NULLIF(website,''), ?),
                                   phone = COALESCE(NULLIF(phone,''), ?),
                                   has_website = CASE WHEN COALESCE(NULLIF(website,''), ?) IS NOT NULL THEN 1 ELSE has_website END,
                                   has_phone = CASE WHEN COALESCE(NULLIF(phone,''), ?) IS NOT NULL THEN 1 ELSE has_phone END,
                                   enrichment_note = trim(COALESCE(enrichment_note,'') || ' place_details:' || ?)
                                WHERE id = ?""",
                             (d["website"], d["phone"], d["website"], d["phone"], d["api"], r["id"]))
            done.append({"id": r["id"], "name": r["name"], "website": d["website"], "phone": d["phone"]})
    return {"status": "ok" if not stopped else stopped, "processed": len(done),
            "filled_website": sum(1 for x in done if x.get("website")),
            "filled_phone": sum(1 for x in done if x.get("phone")), "results": done, **usage()}
