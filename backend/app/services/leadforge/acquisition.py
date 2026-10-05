"""
Client-acquisition helpers that sit across modules (read-mostly):
  followups_due()     pipeline reminders: lf_leads.next_action_date due/overdue, leads never
                      contacted, and sent quotes with no answer.
  set_followup()      put a reminder (next_action + date) on a pipeline lead.
  reactivation_list() past paying clients, accepted-quote clients, QuickBooks history and
                      designers/trade partners who have gone quiet, with a suggested
                      reactivation message (draft text only).
  referral_sources()  where existing customers came from (customers.source / utm_*).

Nothing here sends anything.
"""
from __future__ import annotations

import json
import re
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

DB_PATH = os.getenv("EMPIRE_TASK_DB", str(Path.home() / "empire-data" / "empire.db"))


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _has_table(conn, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _cols(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _lead_label(r) -> str:
    name = " ".join(x for x in (r["first_name"], r["last_name"]) if x)
    return (f"{name} ({r['company']})" if name and r["company"] else name or r["company"] or f"Lead #{r['id']}")


# ── Follow-up reminders ──────────────────────────────────────────────────

def followups_due(days_ahead: int = 7, stale_days: int = 5, limit: int = 50) -> dict:
    today = date.today()
    horizon = (today + timedelta(days=days_ahead)).isoformat()
    out = {"overdue": [], "due_today": [], "upcoming": [], "never_contacted": [], "quotes_waiting": []}
    with _db() as conn:
        if _has_table(conn, "lf_leads"):
            rows = conn.execute(
                """SELECT * FROM lf_leads WHERE status NOT IN ('won','lost')
                   AND next_action_date IS NOT NULL AND date(next_action_date) <= date(?)
                   ORDER BY date(next_action_date) ASC LIMIT ?""", (horizon, limit)).fetchall()
            for r in rows:
                d = (r["next_action_date"] or "")[:10]
                item = {"lead_id": r["id"], "who": _lead_label(r), "status": r["status"], "next_action": r["next_action"],
                        "due": d, "phone": r["phone"], "email": r["email"], "score": r["score"]}
                key = "overdue" if d < today.isoformat() else ("due_today" if d == today.isoformat() else "upcoming")
                out[key].append(item)
            cutoff = (datetime.utcnow() - timedelta(days=stale_days)).strftime("%Y-%m-%d %H:%M:%S")
            for r in conn.execute(
                """SELECT * FROM lf_leads WHERE status = 'new' AND last_contacted IS NULL
                   AND next_action_date IS NULL AND created_at <= ? ORDER BY score DESC LIMIT ?""",
                (cutoff, limit)).fetchall():
                out["never_contacted"].append({"lead_id": r["id"], "who": _lead_label(r), "since": r["created_at"],
                                               "score": r["score"]})
        if _has_table(conn, "quotes_v2"):
            cutoff = (datetime.utcnow() - timedelta(days=stale_days)).isoformat()
            test_filter = "AND COALESCE(is_test,0)=0" if "is_test" in _cols(conn, "quotes_v2") else ""
            for r in conn.execute(
                f"""SELECT id, quote_number, customer_name, customer_email, customer_phone, total, sent_at
                    FROM quotes_v2 WHERE status IN ('sent','proposal') AND accepted_at IS NULL {test_filter}
                    AND COALESCE(sent_at, updated_at) <= ? ORDER BY COALESCE(sent_at, updated_at) ASC LIMIT ?""",
                (cutoff, limit)).fetchall():
                out["quotes_waiting"].append({"quote_id": r["id"], "quote_number": r["quote_number"],
                                              "who": r["customer_name"], "total": r["total"], "sent_at": r["sent_at"],
                                              "email": r["customer_email"], "phone": r["customer_phone"]})
    out["counts"] = {k: len(v) for k, v in out.items() if isinstance(v, list)}
    out["generated_for"] = today.isoformat()
    return out


def set_followup(lead_id: int, when: Optional[str] = None, in_days: Optional[int] = None,
                 action: Optional[str] = None) -> dict:
    if not when:
        when = (date.today() + timedelta(days=int(in_days if in_days is not None else 2))).isoformat()
    try:
        datetime.fromisoformat(when[:10])
    except ValueError:
        return {"error": f"Bad date '{when}', use YYYY-MM-DD"}
    with _db() as conn:
        r = conn.execute("SELECT * FROM lf_leads WHERE id = ?", (lead_id,)).fetchone()
        if not r:
            return {"error": f"Lead {lead_id} not found"}
        conn.execute("UPDATE lf_leads SET next_action = ?, next_action_date = ?, updated_at = datetime('now') WHERE id = ?",
                     (action or r["next_action"] or "Follow up", when[:10], lead_id))
    return {"lead_id": lead_id, "who": _lead_label(r), "next_action": action or r["next_action"] or "Follow up",
            "next_action_date": when[:10]}


# ── Reactivation + referrals ─────────────────────────────────────────────

def _reactivation_message(name: str, kind: str, last_job: Optional[str]) -> str:
    first = (name or "").split()[0] if name else "there"
    if kind == "designer":
        return (f"Hi {first}, it's Rafael from Empire Workroom. We have new fabric books in and open capacity "
                f"for trade projects this season. Anything on your boards we can quote? Happy to drop off samples.")
    since = f" since your {last_job[:7]} project" if last_job else ""
    return (f"Hi {first}, Rafael from Empire Workroom here. Hope everything we made for you{since} is holding up "
            f"beautifully. If any other rooms need drapery, shades or upholstery, we'd love to help, and if a "
            f"friend is redoing their place we're always grateful for a referral.")


_TEST_MARKERS = ("mock", "test", "audit", "sweep", "example.", ".invalid", "d48_recreate", "dummy", "sample client")


_FAKE_PHONE = re.compile(r"555[\s.\-)]*(01\d\d|1234)\b")
_SELF_MARKERS = ("empirebox", "empireworkroom", "empire workroom")


def _clean_email(v):
    m = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", str(v or ""))
    return m.group(0).lower() if m else None


def _looks_test(p: dict) -> bool:
    blob = " ".join(str(p.get(k) or "") for k in ("name", "email", "company")).lower()
    if any(m in blob for m in _TEST_MARKERS) or any(m in blob for m in _SELF_MARKERS):
        return True
    if (p.get("name") or "").strip().lower() in ("empire", "rafael", "me"):
        return True
    return bool(_FAKE_PHONE.search(str(p.get("phone") or "")))  # 555-01xx / 555-1234 are fictional numbers


def reactivation_list(months_quiet: int = 6, limit: int = 25, include_designers: bool = True) -> dict:
    cutoff = (datetime.utcnow() - timedelta(days=30 * months_quiet)).isoformat()
    people: dict = {}

    def add(key, **kw):
        cur = people.setdefault(key, {"reasons": [], "total_paid": 0.0, "last_activity": None})
        for k, v in kw.items():
            if k == "reason":
                if v not in cur["reasons"]:
                    cur["reasons"].append(v)
            elif k == "paid":
                cur["total_paid"] += float(v or 0)
            elif k == "activity":
                if v and (not cur["last_activity"] or v > cur["last_activity"]):
                    cur["last_activity"] = v
            elif v and not cur.get(k):
                cur[k] = v

    with _db() as conn:
        if _has_table(conn, "invoices"):
            ic = _cols(conn, "invoices")
            col = lambda *names: next((c for c in names if c in ic), "NULL")  # noqa: E731  (older schemas lack client_*)
            dates = ", ".join(c for c in ("paid_at", "deposit_date", "invoice_date", "created_at") if c in ic) or "NULL"
            for r in conn.execute(
                f"""SELECT {col('customer_id')} AS customer_id, {col('client_name')} AS client_name,
                          {col('client_email')} AS client_email, {col('client_phone')} AS client_phone,
                          {col('amount_paid')} AS amount_paid, {col('total')} AS total, {col('status')} AS status,
                          COALESCE({dates}, NULL) AS d
                   FROM invoices WHERE COALESCE({col('amount_paid')},0) > 0 OR {col('status')} = 'paid'""").fetchall():
                key = r["customer_id"] or (r["client_email"] or "").lower() or r["client_name"]
                add(key, name=r["client_name"], email=r["client_email"], phone=r["client_phone"], customer_id=r["customer_id"],
                    kind="client", reason="paid invoice", paid=r["amount_paid"] or r["total"], activity=r["d"])
        if _has_table(conn, "quotes_v2"):
            for r in conn.execute(
                f"""SELECT customer_id, customer_name, customer_email, customer_phone, total, accepted_at
                   FROM quotes_v2 WHERE status = 'accepted'
                   {"AND COALESCE(is_test,0) = 0" if "is_test" in _cols(conn, "quotes_v2") else ""}""").fetchall():
                key = r["customer_id"] or (r["customer_email"] or "").lower() or r["customer_name"]
                add(key, name=r["customer_name"], email=r["customer_email"], phone=r["customer_phone"],
                    customer_id=r["customer_id"], kind="client", reason="accepted quote", activity=r["accepted_at"])
        if _has_table(conn, "customers"):
            for r in conn.execute(
                """SELECT id, name, email, phone, company, type, source, total_revenue, updated_at
                   FROM customers WHERE COALESCE(total_revenue,0) > 0 OR source = 'quickbooks'
                      OR (? AND type IN ('designer','contractor','commercial'))""", (1 if include_designers else 0,)).fetchall():
                kind = "designer" if r["type"] == "designer" else ("trade" if r["type"] in ("contractor", "commercial") else "client")
                reason = ("past revenue on file" if (r["total_revenue"] or 0) > 0 else
                          "QuickBooks customer history" if r["source"] == "quickbooks" else f"{r['type']} / trade partner")
                add(r["id"], name=r["name"], email=r["email"], phone=r["phone"], company=r["company"], customer_id=r["id"],
                    kind=kind, reason=reason, paid=r["total_revenue"], activity=None)
        # last touch from any later quote/invoice keeps active clients off the list
        recent = set()
        if _has_table(conn, "quotes_v2"):
            recent |= {x[0] for x in conn.execute("SELECT customer_id FROM quotes_v2 WHERE customer_id IS NOT NULL AND created_at >= ?", (cutoff,))}
        if _has_table(conn, "invoices"):
            recent |= {x[0] for x in conn.execute("SELECT customer_id FROM invoices WHERE customer_id IS NOT NULL AND created_at >= ?", (cutoff,))}

    items = []
    for key, p in people.items():
        if p.get("customer_id") in recent:
            continue
        if p.get("last_activity") and p["last_activity"] >= cutoff:
            continue
        if not (p.get("email") or p.get("phone")):
            continue
        if _looks_test(p):
            continue
        kind = p.get("kind") or "client"
        rank = p["total_paid"] + (5000 if "paid invoice" in p["reasons"] else 0) + (2500 if kind == "designer" else 0)
        items.append({"who": p.get("name"), "company": p.get("company"), "kind": kind, "customer_id": p.get("customer_id"),
                      "email": _clean_email(p.get("email")), "phone": p.get("phone"), "total_paid": round(p["total_paid"], 2),
                      "last_activity": p.get("last_activity"), "why": p["reasons"],
                      "suggested_message": _reactivation_message(p.get("name") or "", kind, p.get("last_activity")),
                      "_rank": rank})
    items.sort(key=lambda x: x["_rank"], reverse=True)
    for i in items:
        i.pop("_rank", None)
    by_kind: dict = {}
    for i in items:
        by_kind[i["kind"]] = by_kind.get(i["kind"], 0) + 1
    return {"months_quiet": months_quiet, "count": len(items), "by_kind": by_kind, "items": items[:limit],
            "send_policy": "Suggested text only. Ask Rafael before contacting anyone."}


def referral_sources() -> dict:
    with _db() as conn:
        if not _has_table(conn, "customers"):
            return {"sources": []}
        rows = conn.execute(
            """SELECT COALESCE(NULLIF(utm_source,''), NULLIF(source,''), 'unknown') AS src, COUNT(*) AS n,
                      SUM(COALESCE(total_revenue,0)) AS revenue
               FROM customers GROUP BY src ORDER BY n DESC""").fetchall()
    return {"sources": [dict(r) for r in rows],
            "gap": "No referral_by field on customers yet; referrals are only visible if typed into source/notes."}
