"""
Growth layer on top of LeadForge (Oct 2026, approved by Rafael):

  1. Deposit paid -> lead won       on_invoice_paid(), reconcile_paid_deposits()
  2. One-tap approval queue          enqueue(), list_queue(), approve(), dismiss(), edit_item()
  3. ROI dashboard                   roi_report(), spend CRUD (manual spend per channel)
  4. Social proof from finished jobs social_proof_for_job(), scan_completed_jobs()
  5. Morning brief / weekly search   morning_brief_text() (sending lives in scripts/growth_jobs.py)

Hard rules:
  * Nothing here sends on its own. The only send path is approve() on an email item,
    which is called by Rafael's tap in the studio (POST /api/v1/growth/approvals/{id}/approve
    with confirm=true) and goes through the existing LeadForge campaign send path
    (campaign_service.send_draft -> EmailService, Gmail SMTP).
  * Instagram / Facebook / SMS / social posts never send: approve() returns the text and a
    link to open; the studio copies it to the clipboard.
  * Max tools may enqueue drafts and read the queue. They can never approve.
"""
from __future__ import annotations

import html
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def _db_path() -> str:
    return os.getenv("EMPIRE_TASK_DB", str(Path.home() / "empire-data" / "empire.db"))


@contextmanager
def _db():
    conn = sqlite3.connect(_db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _has_table(conn, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _cols(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


_SCHEMA_DONE: set = set()


def ensure_schema(conn) -> None:
    key = _db_path()
    if key in _SCHEMA_DONE:
        return
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS approval_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,              -- email | ig_dm | social_post | followup
        channel TEXT NOT NULL,           -- email | instagram | facebook | sms | social
        title TEXT,
        to_name TEXT, to_address TEXT, subject TEXT, body TEXT NOT NULL,
        media_urls TEXT, open_url TEXT,
        source TEXT NOT NULL, source_ref TEXT,
        prospect_id INTEGER, lead_id INTEGER, customer_id TEXT, job_id TEXT,
        status TEXT NOT NULL DEFAULT 'pending',  -- pending | sent | copied | dismissed | failed
        result TEXT, created_by TEXT DEFAULT 'max',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        decided_at TEXT, sent_at TEXT,
        UNIQUE (source, source_ref)
    );
    CREATE TABLE IF NOT EXISTS marketing_spend (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,             -- YYYY-MM
        channel TEXT NOT NULL,
        amount REAL NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE (month, channel)
    );
    CREATE TABLE IF NOT EXISTS social_proof_drafts (
        job_id TEXT PRIMARY KEY,
        post_ids TEXT, queue_ids TEXT, photo_count INTEGER, note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    if _has_table(conn, "lf_leads"):
        have = _cols(conn, "lf_leads")
        for col, typ in (("won_at", "TEXT"), ("won_value", "REAL"), ("won_invoice_id", "TEXT")):
            if col not in have:
                conn.execute(f"ALTER TABLE lf_leads ADD COLUMN {col} {typ}")
    _SCHEMA_DONE.add(key)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Deposit paid -> lead won
# ═══════════════════════════════════════════════════════════════════════════

def _digits(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    return d[-10:] if len(d) >= 10 else ""


def _find_lead_for_invoice(conn, inv: dict) -> Optional[sqlite3.Row]:
    if not _has_table(conn, "lf_leads"):
        return None
    q = "SELECT * FROM lf_leads WHERE {} ORDER BY (status IN ('won','lost')), id DESC LIMIT 1"
    if inv.get("quote_id"):
        r = conn.execute(q.format("quote_id = ?"), (inv["quote_id"],)).fetchone()
        if r:
            return r
    if inv.get("customer_id"):
        r = conn.execute(q.format("customer_id = ?"), (inv["customer_id"],)).fetchone()
        if r:
            return r
    email = (inv.get("client_email") or "").strip().lower()
    cust = None
    if inv.get("customer_id") and _has_table(conn, "customers"):
        cust = conn.execute("SELECT email, phone FROM customers WHERE id = ?", (inv["customer_id"],)).fetchone()
    if not email and cust:
        email = (cust["email"] or "").strip().lower()
    if email:
        r = conn.execute(q.format("lower(trim(email)) = ?"), (email,)).fetchone()
        if r:
            return r
    phone = _digits(inv.get("client_phone") or (cust["phone"] if cust else ""))
    if phone:
        for r in conn.execute("SELECT * FROM lf_leads WHERE phone IS NOT NULL AND phone <> '' "
                              "ORDER BY (status IN ('won','lost')), id DESC"):
            if _digits(r["phone"]) == phone:
                return r
    return None


def mark_lead_won_for_invoice(conn, invoice_id: str, source: str = "payment") -> dict:
    inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if not inv:
        return {"invoice_id": invoice_id, "status": "invoice_not_found"}
    inv = dict(inv)
    paid = float(inv.get("amount_paid") or 0)
    if paid <= 0 and (inv.get("payment_status") or inv.get("status")) not in ("paid", "partial"):
        return {"invoice_id": invoice_id, "status": "not_paid"}
    lead = _find_lead_for_invoice(conn, inv)
    if not lead:
        return {"invoice_id": invoice_id, "status": "no_matching_lead",
                "hint": "Lead links by quote_id, customer_id, email or phone."}
    if lead["status"] == "won" and (lead["won_invoice_id"] or "") == invoice_id:
        return {"invoice_id": invoice_id, "lead_id": lead["id"], "status": "already_won"}
    value = 0.0
    if inv.get("quote_id") and _has_table(conn, "quotes_v2"):
        qr = conn.execute("SELECT total FROM quotes_v2 WHERE id = ?", (inv["quote_id"],)).fetchone()
        value = float(qr["total"] or 0) if qr else 0.0
    value = value or float(inv.get("total") or 0) or paid
    now = _now()
    conn.execute(
        """UPDATE lf_leads SET status = 'won', won_at = COALESCE(won_at, ?), won_value = ?,
               won_invoice_id = ?, estimated_value = CASE WHEN COALESCE(estimated_value,0) < ? THEN ? ELSE estimated_value END,
               quote_id = COALESCE(quote_id, ?), customer_id = COALESCE(customer_id, ?),
               next_action = NULL, next_action_date = NULL, updated_at = ?
           WHERE id = ?""",
        (now, value, invoice_id, value, value, inv.get("quote_id"), inv.get("customer_id"), now, lead["id"]))
    if _has_table(conn, "lf_activities"):
        conn.execute(
            """INSERT INTO lf_activities (lead_id, type, channel, subject, content, ai_generated, status, completed_at, created_at)
               VALUES (?, 'note', 'deposit_paid', ?, ?, 0, 'completed', ?, ?)""",
            (lead["id"], f"Deposit paid: {inv.get('invoice_number') or invoice_id}",
             json.dumps({"invoice_id": invoice_id, "amount_paid": paid, "won_value": value, "source": source}), now, now))
    pipeline_updated = False
    if lead["prospect_id"] and _has_table(conn, "prospect_pipeline"):
        cur = conn.execute("UPDATE prospect_pipeline SET status = 'won', updated_at = ? WHERE prospect_id = ?",
                           (now, lead["prospect_id"]))
        pipeline_updated = cur.rowcount > 0
    return {"invoice_id": invoice_id, "lead_id": lead["id"], "status": "marked_won", "won_value": value,
            "amount_paid": paid, "prospect_pipeline_updated": pipeline_updated}


def on_invoice_paid(invoice_id: str, source: str = "payment") -> dict:
    """Called after a payment is recorded (Stripe webhook or manual). Never raises."""
    try:
        with _db() as conn:
            return mark_lead_won_for_invoice(conn, invoice_id, source)
    except Exception as e:  # never break the payment path
        return {"invoice_id": invoice_id, "status": "error", "error": str(e)}


def reconcile_paid_deposits() -> dict:
    """Idempotent sweep: every paid/partial invoice -> matching lead marked won."""
    out = {"checked": 0, "marked_won": [], "no_matching_lead": 0, "already_won": 0}
    with _db() as conn:
        if not _has_table(conn, "invoices"):
            return out
        rows = conn.execute("""SELECT id FROM invoices WHERE COALESCE(amount_paid,0) > 0
                               OR payment_status IN ('paid','partial') OR status IN ('paid','partial')""").fetchall()
        for r in rows:
            out["checked"] += 1
            res = mark_lead_won_for_invoice(conn, r["id"], "reconcile")
            if res["status"] == "marked_won":
                out["marked_won"].append(res)
            elif res["status"] in ("no_matching_lead",):
                out["no_matching_lead"] += 1
            elif res["status"] == "already_won":
                out["already_won"] += 1
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 2. Approval queue
# ═══════════════════════════════════════════════════════════════════════════

_CHANNEL_KIND = {"email": "email", "instagram": "ig_dm", "instagram_dm": "ig_dm", "facebook": "ig_dm",
                 "sms": "followup", "social": "social_post"}


def _row(r) -> dict:
    d = dict(r)
    try:
        d["media_urls"] = json.loads(d.get("media_urls") or "[]")
    except Exception:
        d["media_urls"] = []
    d["can_send_email"] = d["channel"] == "email" and bool(_valid_email(d.get("to_address")))
    d["action"] = ("send_email" if d["channel"] == "email" else "copy_and_open")
    return d


def _valid_email(v) -> Optional[str]:
    m = re.fullmatch(r"\s*([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})\s*", str(v or ""))
    return m.group(1) if m else None


def enqueue(*, channel: str, body: str, source: str, source_ref: Optional[str] = None, kind: Optional[str] = None,
            title: str = "", to_name: str = "", to_address: str = "", subject: str = "",
            media_urls: Optional[list] = None, open_url: str = "", prospect_id=None, lead_id=None,
            customer_id=None, job_id=None, created_by: str = "max") -> dict:
    channel = (channel or "email").lower()
    if channel == "instagram_dm":
        channel = "instagram"
    if channel not in ("email", "instagram", "facebook", "sms", "social"):
        raise ValueError(f"unknown channel {channel}")
    if not (body or "").strip():
        raise ValueError("body required")
    kind = kind or _CHANNEL_KIND.get(channel, "followup")
    if not open_url:
        open_url = {"instagram": "https://www.instagram.com/direct/inbox/", "facebook": "https://www.facebook.com/messages/",
                    "social": "https://www.instagram.com/"}.get(channel, "")
    with _db() as conn:
        if source_ref:
            ex = conn.execute("SELECT * FROM approval_queue WHERE source = ? AND source_ref = ?",
                              (source, str(source_ref))).fetchone()
            if ex:
                return {**_row(ex), "deduped": True}
        cur = conn.execute(
            """INSERT INTO approval_queue (kind, channel, title, to_name, to_address, subject, body, media_urls, open_url,
                   source, source_ref, prospect_id, lead_id, customer_id, job_id, created_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (kind, channel, title, to_name, to_address, subject, body.strip(), json.dumps(media_urls or []), open_url,
             source, str(source_ref) if source_ref is not None else None, prospect_id, lead_id, customer_id, job_id,
             created_by))
        return _row(conn.execute("SELECT * FROM approval_queue WHERE id = ?", (cur.lastrowid,)).fetchone())


def sync_campaign_drafts() -> int:
    """Pull pending LeadForge campaign drafts into the queue (read-through; send stays campaign_service)."""
    n = 0
    with _db() as conn:
        if not _has_table(conn, "campaign_drafts"):
            return 0
        rows = conn.execute("""SELECT d.* FROM campaign_drafts d WHERE d.status IN ('draft','edited','reviewed')
                               AND NOT EXISTS (SELECT 1 FROM approval_queue q WHERE q.source='campaign'
                                               AND q.source_ref = CAST(d.id AS TEXT))""").fetchall()
    for d in rows:
        d = dict(d)
        step = (d.get("step_type") or "email").lower()
        is_email = "email" in step or bool(d.get("to_email"))
        if is_email and not d.get("to_email") and d.get("prospect_id"):
            try:  # campaign drafts often lack the address; use the prospect's if we found one later
                with _db() as conn:
                    if _has_table(conn, "prospects") and "email" in _cols(conn, "prospects"):
                        r = conn.execute("SELECT email FROM prospects WHERE id=?", (d["prospect_id"],)).fetchone()
                        if r and r[0]:
                            d["to_email"] = r[0]
            except Exception:
                pass
        body = d.get("body") or d.get("linkedin_message") or d.get("script") or ""
        if not body.strip():
            continue
        enqueue(channel="email" if is_email else "sms", body=body, source="campaign", source_ref=str(d["id"]),
                kind="email" if is_email else "followup", title=f"Campaign {step.replace('_', ' ')}",
                to_name=d.get("to_name") or "", to_address=d.get("to_email") or d.get("phone_number") or "",
                subject=d.get("subject") or "", prospect_id=d.get("prospect_id"), created_by="campaign")
        n += 1
    return n


def list_queue(status: str = "pending", limit: int = 200) -> dict:
    try:
        sync_campaign_drafts()
    except Exception:
        pass
    with _db() as conn:
        if status == "all":
            rows = conn.execute("SELECT * FROM approval_queue ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM approval_queue WHERE status = ? ORDER BY id DESC LIMIT ?",
                                (status, limit)).fetchall()
        counts = {r["status"]: r["n"] for r in conn.execute(
            "SELECT status, COUNT(*) n FROM approval_queue GROUP BY status")}
    return {"items": [_row(r) for r in rows], "counts": counts,
            "policy": "Nothing sends without Rafael's tap. Email goes through the existing LeadForge send path "
                      "(Gmail). Instagram, Facebook, SMS and social posts are copy-and-open only."}


def get_item(item_id: int) -> Optional[dict]:
    with _db() as conn:
        r = conn.execute("SELECT * FROM approval_queue WHERE id = ?", (item_id,)).fetchone()
    return _row(r) if r else None


def edit_item(item_id: int, **fields) -> dict:
    allowed = {k: v for k, v in fields.items() if k in ("to_name", "to_address", "subject", "body") and v is not None}
    with _db() as conn:
        r = conn.execute("SELECT * FROM approval_queue WHERE id = ?", (item_id,)).fetchone()
        if not r:
            raise LookupError("not found")
        if r["status"] != "pending":
            raise ValueError(f"item is {r['status']}, not pending")
        if allowed:
            conn.execute(f"UPDATE approval_queue SET {', '.join(k + ' = ?' for k in allowed)} WHERE id = ?",
                         (*allowed.values(), item_id))
        return _row(conn.execute("SELECT * FROM approval_queue WHERE id = ?", (item_id,)).fetchone())


def dismiss(item_id: int) -> dict:
    with _db() as conn:
        cur = conn.execute("UPDATE approval_queue SET status='dismissed', decided_at=? WHERE id=? AND status='pending'",
                           (_now(), item_id))
        if not cur.rowcount:
            raise LookupError("not found or not pending")
        return _row(conn.execute("SELECT * FROM approval_queue WHERE id = ?", (item_id,)).fetchone())


def _to_html(text: str) -> str:
    if re.search(r"<(p|br|div|table)\b", text or "", re.I):
        return text
    paras = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paras)


async def approve(item_id: int, *, confirm: bool, approved_by: str = "rafael", **edits) -> dict:
    """Rafael's tap. Email -> existing campaign send path. Everything else -> copy-and-open."""
    if not confirm:
        raise PermissionError("confirm=true is required (Rafael's tap). Nothing was sent.")
    if edits:
        edit_item(item_id, **edits)
    item = get_item(item_id)
    if not item:
        raise LookupError("not found")
    if item["status"] != "pending":
        raise ValueError(f"item is {item['status']}, not pending. Nothing was sent.")

    if item["channel"] != "email":
        with _db() as conn:
            conn.execute("UPDATE approval_queue SET status='copied', decided_at=?, result=? WHERE id=?",
                         (_now(), f"approved by {approved_by}: copy and open", item_id))
        return {"id": item_id, "status": "copied", "sent": False, "copy_text": item["body"],
                "open_url": item.get("open_url") or "", "media_urls": item["media_urls"],
                "note": "Not sent by Empire. Paste it in the app that just opened."}

    to = _valid_email(item.get("to_address"))
    if not to:
        raise ValueError("No valid recipient email on this draft. Edit the address first. Nothing was sent.")
    from app.services.leadforge import campaign_service as cs
    if item["source"] == "campaign" and item.get("source_ref"):
        draft_id = int(item["source_ref"])
        with cs._db() as conn:
            rev = ", reviewed_at=datetime('now')" if "reviewed_at" in _cols(conn, "campaign_drafts") else ""
            conn.execute(f"""UPDATE campaign_drafts SET to_email=?, subject=?, body=?, status='reviewed'{rev}
                             WHERE id=?""", (to, item.get("subject") or "", item["body"], draft_id))
    else:
        with cs._db() as conn:
            has_rev = "reviewed_at" in _cols(conn, "campaign_drafts")
            cur = conn.execute(
                f"""INSERT INTO campaign_drafts (prospect_id, step_type, to_email, to_name, subject, body, status
                        {', reviewed_at' if has_rev else ''})
                   VALUES (?, 'email', ?, ?, ?, ?, 'reviewed' {", datetime('now')" if has_rev else ''})""",
                (item.get("prospect_id"), to, item.get("to_name") or "", item.get("subject") or "(no subject)",
                 _to_html(item["body"])))
            draft_id = cur.lastrowid
    result = await cs.send_draft(draft_id)
    ok = result.get("status") == "sent"
    with _db() as conn:
        conn.execute("UPDATE approval_queue SET status=?, decided_at=?, sent_at=?, result=? WHERE id=?",
                     ("sent" if ok else "failed", _now(), _now() if ok else None,
                      json.dumps({"campaign_draft_id": draft_id, **result})[:2000], item_id))
        if ok and item["source"] == "prospect_draft" and item.get("source_ref") and _has_table(conn, "prospect_outreach_drafts"):
            conn.execute("UPDATE prospect_outreach_drafts SET status='sent' WHERE id=?", (item["source_ref"],))
        if ok and item.get("lead_id") and _has_table(conn, "lf_leads"):
            conn.execute("UPDATE lf_leads SET last_contacted=?, status=CASE WHEN status='new' THEN 'contacted' ELSE status END WHERE id=?",
                         (_now(), item["lead_id"]))
    return {"id": item_id, "status": "sent" if ok else "failed", "sent": ok, "campaign_draft_id": draft_id,
            "detail": result.get("error") or result.get("send_result")}


# ═══════════════════════════════════════════════════════════════════════════
# 3. ROI
# ═══════════════════════════════════════════════════════════════════════════

_CHANNEL_ALIASES = [
    ("google_ads", ("google ads", "adwords", "gads", "cpc", "ppc")),
    ("instagram", ("instagram", "ig")),
    ("facebook", ("facebook", "fb", "meta")),
    ("google_maps", ("google_maps", "gbp", "google business", "maps")),
    ("website", ("website", "web", "site", "luxeforge", "intake", "workroom_intake", "form")),
    ("referral", ("referral", "referred", "word of mouth", "designer referral")),
    ("prospecting", ("prospect", "leadforge", "outreach", "cold")),
    ("quickbooks", ("quickbooks", "qb")),
    ("email", ("email", "newsletter")),
    ("houzz", ("houzz",)),
    ("yelp", ("yelp",)),
]


def normalize_channel(*vals) -> str:
    for v in vals:
        s = str(v or "").strip().lower()
        if not s:
            continue
        for name, keys in _CHANNEL_ALIASES:
            if s == name or any(k == s or k in s for k in keys):
                return name
        return re.sub(r"[^a-z0-9]+", "_", s).strip("_")[:30] or "direct"
    return "direct"


def _month(d) -> str:
    return str(d or "")[:7]


def roi_report(months: int = 12) -> dict:
    since = (datetime.now().replace(day=1) - timedelta(days=31 * max(1, months) - 31)).strftime("%Y-%m")
    ch: dict = {}

    def c(name):
        return ch.setdefault(name, {"channel": name, "leads": 0, "won_leads": 0, "quotes": 0, "quote_value": 0.0,
                                    "paid_invoices": 0, "revenue": 0.0, "spend": 0.0})

    with _db() as conn:
        cust_channel: dict = {}
        if _has_table(conn, "customers"):
            cc = _cols(conn, "customers")
            sel = ", ".join(x for x in ("id", "source", "utm_source", "utm_medium") if x in cc)
            for r in conn.execute(f"SELECT {sel} FROM customers"):
                r = dict(r)
                cust_channel[r["id"]] = normalize_channel(r.get("utm_source"), r.get("source"))
        lead_channel_by_customer: dict = {}
        if _has_table(conn, "lf_leads"):
            for r in conn.execute("SELECT * FROM lf_leads WHERE substr(created_at,1,7) >= ?", (since,)):
                r = dict(r)
                name = normalize_channel(r.get("utm_source"), r.get("source"),
                                         "prospecting" if r.get("prospect_id") else None)
                c(name)["leads"] += 1
                if r.get("status") == "won":
                    c(name)["won_leads"] += 1
                if r.get("customer_id"):
                    lead_channel_by_customer[r["customer_id"]] = name
        chan_for = lambda cid: lead_channel_by_customer.get(cid) or cust_channel.get(cid) or "direct"
        if _has_table(conn, "quotes_v2"):
            tf = "AND COALESCE(is_test,0)=0" if "is_test" in _cols(conn, "quotes_v2") else ""
            for r in conn.execute(f"""SELECT customer_id, total, status FROM quotes_v2
                                     WHERE substr(created_at,1,7) >= ? AND status NOT IN ('draft','cancelled','void') {tf}""",
                                  (since,)):
                x = c(chan_for(r["customer_id"]))
                x["quotes"] += 1
                x["quote_value"] += float(r["total"] or 0)
        if _has_table(conn, "invoices"):
            for r in conn.execute("""SELECT customer_id, amount_paid, paid_at, created_at FROM invoices
                                     WHERE COALESCE(amount_paid,0) > 0
                                       AND substr(COALESCE(paid_at, created_at),1,7) >= ?""", (since,)):
                x = c(chan_for(r["customer_id"]))
                x["paid_invoices"] += 1
                x["revenue"] += float(r["amount_paid"] or 0)
        spend_rows = [dict(r) for r in conn.execute(
            "SELECT * FROM marketing_spend WHERE month >= ? ORDER BY month DESC, channel", (since,))]
    for s in spend_rows:
        c(normalize_channel(s["channel"]))["spend"] += float(s["amount"] or 0)
    rows = []
    for k in [k for k in ch if re.search(r"mock|test|d48_|sweep|audit|dummy", k)]:
        ch.pop(k)  # test/mock data never counts toward ROI
    for x in ch.values():
        x["quote_value"] = round(x["quote_value"], 2)
        x["revenue"] = round(x["revenue"], 2)
        x["spend"] = round(x["spend"], 2)
        x["cost_per_lead"] = round(x["spend"] / x["leads"], 2) if x["spend"] and x["leads"] else None
        x["cost_per_won"] = round(x["spend"] / x["won_leads"], 2) if x["spend"] and x["won_leads"] else None
        x["roi_pct"] = round((x["revenue"] - x["spend"]) / x["spend"] * 100, 1) if x["spend"] else None
        x["lead_to_quote_pct"] = round(x["quotes"] / x["leads"] * 100, 1) if x["leads"] else None
        rows.append(x)
    rows.sort(key=lambda x: (-x["revenue"], -x["leads"]))
    tot = {k: round(sum(r[k] for r in rows), 2) for k in ("leads", "won_leads", "quotes", "quote_value",
                                                            "paid_invoices", "revenue", "spend")}
    tot["roi_pct"] = round((tot["revenue"] - tot["spend"]) / tot["spend"] * 100, 1) if tot["spend"] else None
    return {"since_month": since, "months": months, "channels": rows, "totals": tot, "spend_entries": spend_rows,
            "notes": ["Revenue = invoices.amount_paid (deposits and payments) by the customer's lead source.",
                      "Channel = lead utm_source/source, else customer utm_source/source, else 'direct'.",
                      "Spend is entered by hand per month and channel."]}


def set_spend(month: str, channel: str, amount: float, notes: str = "") -> dict:
    if not re.fullmatch(r"\d{4}-\d{2}", month or ""):
        raise ValueError("month must be YYYY-MM")
    channel = normalize_channel(channel)
    with _db() as conn:
        conn.execute("""INSERT INTO marketing_spend (month, channel, amount, notes) VALUES (?,?,?,?)
                        ON CONFLICT(month, channel) DO UPDATE SET amount=excluded.amount, notes=excluded.notes""",
                     (month, channel, float(amount), notes))
        return dict(conn.execute("SELECT * FROM marketing_spend WHERE month=? AND channel=?", (month, channel)).fetchone())


def delete_spend(spend_id: int) -> bool:
    with _db() as conn:
        return conn.execute("DELETE FROM marketing_spend WHERE id = ?", (spend_id,)).rowcount > 0


# ═══════════════════════════════════════════════════════════════════════════
# 4. Social proof from finished jobs
# ═══════════════════════════════════════════════════════════════════════════

_AFTER_HINT = re.compile(r"after|install|finished|final|complete|done|reveal", re.I)
_BEFORE_HINT = re.compile(r"before|intake|existing|site|measure", re.I)


def _photo_list(raw) -> list:
    if not raw:
        return []
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return [raw] if isinstance(raw, str) and raw.startswith(("/", "http")) else []
    out = []
    for p in v if isinstance(v, list) else [v]:
        if isinstance(p, str):
            out.append({"url": p})
        elif isinstance(p, dict) and (p.get("url") or p.get("path")):
            out.append({"url": p.get("url") or p.get("path"), "name": p.get("original_name") or p.get("filename") or "",
                        "from_intake": bool(p.get("from_intake")), "tag": p.get("tag") or p.get("kind") or ""})
    return out


def job_photos(conn, job: dict) -> dict:
    before, after, other = [], [], []
    seen = set()

    def put(p, default):
        url = p["url"]
        if url in seen:
            return
        seen.add(url)
        hint = f"{p.get('tag', '')} {p.get('name', '')} {url}"
        if p.get("from_intake") or _BEFORE_HINT.search(hint):
            before.append(url)
        elif _AFTER_HINT.search(hint):
            after.append(url)
        else:
            (before if default == "before" else after if default == "after" else other).append(url)

    for p in _photo_list(job.get("photos")):
        put(p, "other")
    if _has_table(conn, "job_documents"):
        args = [job["id"]] + ([job["quote_id"]] if job.get("quote_id") else [])
        q = "SELECT url, filename, created_at FROM job_documents WHERE document_type='photo' AND (job_id = ?" + \
            (" OR quote_id = ?" if job.get("quote_id") else "") + ") ORDER BY created_at"
        prod = job.get("production_start") or job.get("install_date") or ""
        for r in conn.execute(q, args):
            default = "after" if prod and (r["created_at"] or "") >= prod else "other"
            put({"url": r["url"], "name": r["filename"] or ""}, default)
    if job.get("quote_id") and _has_table(conn, "quotes_v2"):
        qr = conn.execute("SELECT photos_json FROM quotes_v2 WHERE id = ?", (job["quote_id"],)).fetchone()
        for p in _photo_list(qr["photos_json"] if qr else None):
            p["from_intake"] = True if p.get("from_intake") is not False else p["from_intake"]
            put(p, "before")
    if not before and other:
        before = other[:2]
        other = other[2:]
    return {"before": before[:4], "after": after[:4], "other": other[:4]}


def _first_name(name: str) -> str:
    n = (name or "").strip()
    return n.split()[0] if n and not re.search(r"\b(llc|inc|design|studio|group)\b", n, re.I) else ""


def social_proof_for_job(job_id: str, force: bool = False) -> dict:
    """Finished job -> before/after post drafts in SocialForge (status draft) + approval-queue items."""
    with _db() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise LookupError("job not found")
        job = dict(job)
        done = conn.execute("SELECT * FROM social_proof_drafts WHERE job_id = ?", (job_id,)).fetchone()
        if done and not force:
            return {"job_id": job_id, "status": "already_drafted", "post_ids": json.loads(done["post_ids"] or "[]")}
        photos = job_photos(conn, job)
    if not (photos["before"] or photos["after"] or photos["other"]):
        return {"job_id": job_id, "status": "no_photos", "posted": False,
                "note": "No photos on this job or its quote yet. Add before/after photos, then draft again."}
    room = job.get("room") or ""
    title = re.sub(r"^Job for\s+", "", job.get("title") or "").split(" — ")[0].strip()
    city = ""
    addr = job.get("client_address") or job.get("address") or ""
    m = re.search(r",\s*([A-Za-z .]+),\s*(VA|MD|DC)\b", addr)
    if m:
        city = f"{m.group(1).strip()}, {m.group(2)}"
    what = (job.get("description") or "").strip() or "custom window treatments"
    where = f" in {city}" if city else " in the DMV"
    room_txt = f" {room.lower()}" if room else ""
    have_after = bool(photos["after"])
    caption_ig = (f"Before → after{where}. We made and installed {what} for this{room_txt or ' home'}, "
                  f"sewn in our own workroom. Swipe to see the difference.\n\n"
                  f"Thinking about drapery, Roman shades or upholstery? DM us or book a consult at the link in bio.")
    caption_fb = (f"Another finished project{where}: {what}{(' for the' + room_txt) if room_txt else ''}. "
                  f"Everything is made to measure in the Empire Workroom and installed by our team. "
                  f"Before and after photos below. Message us for a free consult.")
    hashtags = "#customdrapery #windowtreatments #romanshades #interiordesign #dmvdesign #workroom #beforeandafter"
    media = photos["before"][:2] + photos["after"][:2]
    note = None if have_after else "No after photo found on this job yet. Add one before posting."
    from app.routers import socialforge as sf
    post_ids, queue_ids = [], []
    for platform, caption in (("instagram", caption_ig), ("facebook", caption_fb)):
        pid = os.urandom(6).hex()
        post = {"id": pid, "code": sf._next_code(sf.POSTS_DIR, "POST"), "platform": platform, "content": caption,
                "hashtags": hashtags, "media_url": media[0] if media else None, "media_urls": media,
                "before_photos": photos["before"], "after_photos": photos["after"],
                "scheduled_for": None, "campaign_id": None, "status": "draft", "source": "social_proof",
                "job_id": job_id, "engagement": {"likes": 0, "comments": 0, "shares": 0, "reach": 0},
                "created_at": datetime.utcnow().isoformat(), "updated_at": datetime.utcnow().isoformat(),
                "posted_at": None, "needs_after_photo": not have_after}
        sf._save(sf.POSTS_DIR, pid, post)
        post_ids.append(pid)
        q = enqueue(channel="social", kind="social_post", body=f"{caption}\n\n{hashtags}", source="socialforge",
                    source_ref=pid, title=f"{platform.title()} before/after: {title or job_id}" + (" (needs after photo)" if not have_after else ""),
                    media_urls=media, job_id=job_id, customer_id=job.get("customer_id"),
                    open_url="https://www.instagram.com/" if platform == "instagram" else "https://www.facebook.com/",
                    created_by="social_proof")
        queue_ids.append(q["id"])
    with _db() as conn:
        conn.execute("""INSERT OR REPLACE INTO social_proof_drafts (job_id, post_ids, queue_ids, photo_count, note)
                        VALUES (?,?,?,?,?)""", (job_id, json.dumps(post_ids), json.dumps(queue_ids), len(media), note))
    return {"job_id": job_id, "status": "drafted", "post_ids": post_ids, "queue_ids": queue_ids,
            "photos": photos, "note": note, "posted": False,
            "policy": "Draft only. Posting stays manual (copy and open from the approval queue)."}


_TEST_JOB = re.compile(r"mock|test|e2e|sweep|sample|dummy", re.I)


def scan_completed_jobs(days: int = 30, include_test: bool = False) -> dict:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    out = {"drafted": [], "skipped_test": 0, "already": 0}
    with _db() as conn:
        if not _has_table(conn, "jobs"):
            return out
        rows = [dict(r) for r in conn.execute(
            """SELECT j.id, j.title, j.client_name FROM jobs j
               WHERE (j.status = 'completed' OR j.pipeline_stage IN ('completed','invoiced','paid'))
                 AND COALESCE(j.completed_date, j.install_date, j.updated_at) >= ?
                 AND NOT EXISTS (SELECT 1 FROM social_proof_drafts s WHERE s.job_id = j.id)""", (since,))]
    out["no_photos"] = 0
    for j in rows:
        if not include_test and _TEST_JOB.search(f"{j.get('title')} {j.get('client_name')}"):
            out["skipped_test"] += 1
            continue
        res = social_proof_for_job(j["id"])
        if res["status"] == "no_photos":
            out["no_photos"] += 1
        else:
            out["drafted"].append(res)
    return out


def on_job_completed(job_id: str) -> dict:
    try:
        with _db() as conn:
            j = conn.execute("SELECT title, client_name FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if j and _TEST_JOB.search(f"{j['title']} {j['client_name']}"):
            return {"job_id": job_id, "status": "skipped_test"}
        return social_proof_for_job(job_id)
    except Exception as e:
        return {"job_id": job_id, "status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# 5. Morning brief text (sent by scripts/growth_jobs.py to Rafael's Telegram chat only)
# ═══════════════════════════════════════════════════════════════════════════

def morning_brief(limit: int = 5) -> dict:
    from app.services.leadforge import prospect_ops, acquisition
    brief = prospect_ops.daily_brief(limit=max(5, limit))
    fu = acquisition.followups_due(days_ahead=0)
    q = list_queue("pending", limit=500)
    return {"prospects": brief.get("items", [])[:limit], "followups": fu, "queue_pending": len(q["items"])}


def morning_brief_text(limit: int = 5) -> str:
    b = morning_brief(limit)
    esc = html.escape
    day = datetime.now().strftime("%a %b %-d")
    lines = [f"<b>☀️ Empire growth brief, {day}</b>", ""]
    lines.append("<b>Top prospects</b>")
    if not b["prospects"]:
        lines.append("No new prospects today.")
    for i, p in enumerate(b["prospects"], 1):
        contact = p.get("contact")
        who = ""
        if isinstance(contact, dict):
            who = " · " + ", ".join(x for x in (contact.get("name"), contact.get("email") or contact.get("phone")) if x)
        why = "; ".join((p.get("why") or [])[:2])
        lines.append(f"{i}. <b>{esc(p.get('name') or '')}</b> ({esc(p.get('city') or '')}) {p.get('outreach_score')}/100{esc(who)}")
        if why:
            lines.append(f"   {esc(why)}")
    fu = b["followups"] or {}
    due = (fu.get("overdue") or []) + (fu.get("due_today") or [])
    lines += ["", f"<b>Follow-ups due ({len(due)})</b>"]
    for f in due[:6]:
        lines.append(f"• {esc(str(f.get('who')))}: {esc(str(f.get('next_action') or 'follow up'))} (due {esc(str(f.get('due')))})")
    if not due:
        lines.append("None due today.")
    qw = fu.get("quotes_waiting") or []
    lines += ["", f"<b>Quotes waiting ({len(qw)})</b>"]
    for qq in qw[:6]:
        lines.append(f"• {esc(str(qq.get('quote_number')))} {esc(str(qq.get('who')))}: ${float(qq.get('total') or 0):,.0f}")
    if not qw:
        lines.append("None.")
    lines += ["", f"📝 {b['queue_pending']} drafts waiting for your tap in Approvals. Nothing was sent."]
    return "\n".join(lines)
