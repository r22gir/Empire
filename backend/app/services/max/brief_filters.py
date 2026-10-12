"""Shared noise filters for the daily brief and desk jobs.

Keeps Rafael's brief to real money, real quotes, human mail, and real
yes/no approvals. Test/purge clients and marketing mail never ship as news.
"""
from __future__ import annotations

import fnmatch
import os
from datetime import datetime
from typing import Any, Iterable
from zoneinfo import ZoneInfo

# One configurable list. Exact match unless the pattern has * or ?.
# Override with BRIEF_TEST_CLIENT_PATTERNS (comma-separated) if needed.
DEFAULT_TEST_CLIENT_PATTERNS = (
    "*test*",
    "TrustTest",
    "MOCK-SWEEP*",
    "Jane Smith",
    "Customer",
    "purge candidate",
    "Empresa Prueba",
)

ET = ZoneInfo("America/New_York")

PROMO_LABELS = frozenset({
    "CATEGORY_PROMOTIONS",
    "CATEGORY_SOCIAL",
    "CATEGORY_UPDATES",
    "CATEGORY_FORUMS",
})

MARKETING_SENDERS = (
    "macy", "macys.com", "wayfair", "facebook", "fbmail", "experian",
    "etsy", "pinterest", "linkedin", "mailchimp", "substack",
    "crate and barrel", "crateandbarrel", "home depot", "homedepot",
    "pro xtra", "proxtra",
)

MARKETING_KEYWORDS = (
    "webinar", "market invite", "invitation to", "% off", "percent off",
    "lookbook", "unsubscribe", "exclusive offer", "flash sale",
    "limited time", "shop now", "don't miss",
)

NOREPLY_HINTS = ("no-reply", "noreply", "no_reply", "donotreply", "do-not-reply")

BANK_HINTS = (
    "zelle", "mobile deposit", "account statement", "e-statement",
    "estatement", "bank statement", "transaction alert", "direct deposit",
    "ach credit", "ach debit", "wire transfer", "receipt from",
    "your receipt", "payment received", "card ending",
)

BACKLOG_NOISE = (
    "jwt",
    "sqlite encryption",
    "encrypt sqlite",
    "sqlite encrypt",
    "dev backlog",
)

APPROVAL_HINTS = ("approv", "voice", "founder pin", "waiting on rafael", "decision needed")


def _blob(*parts: Any) -> str:
    return " ".join(str(p or "") for p in parts).strip()


def test_client_patterns() -> tuple[str, ...]:
    raw = (os.getenv("BRIEF_TEST_CLIENT_PATTERNS") or "").strip()
    if raw:
        return tuple(p.strip() for p in raw.split(",") if p.strip())
    return DEFAULT_TEST_CLIENT_PATTERNS


def _matches_pattern(text: str, pattern: str) -> bool:
    t = (text or "").casefold()
    p = (pattern or "").casefold()
    if not t or not p:
        return False
    if any(ch in pattern for ch in "*?["):
        return fnmatch.fnmatch(t, p)
    return t == p


def is_noise_client(name: Any) -> bool:
    text = str(name or "").strip()
    if not text:
        return False
    return any(_matches_pattern(text, pat) for pat in test_client_patterns())


def is_flagged_test(item: dict | None) -> bool:
    if not item:
        return False
    flag = item.get("is_test")
    if flag in (1, True, "1", "true", "yes"):
        return True
    return is_noise_client(item.get("customer") or item.get("name") or item.get("customer_name"))


def is_placeholder_name(name: Any) -> bool:
    return _matches_pattern(str(name or "").strip(), "Customer") or str(name or "").strip().lower() in {
        "unknown", "client", "n/a", "tbd",
    }


def is_zero_amount(value: Any) -> bool:
    try:
        return abs(float(value or 0)) < 0.005
    except (TypeError, ValueError):
        return True


def _obvious_test_body(text: str) -> bool:
    blob = str(text or "").strip()
    if not blob:
        return False
    low = blob.casefold()
    if any(tok in low for tok in ("mock-sweep", "purge candidate", "trusttest")):
        return True
    if low.startswith("test ") or low == "test" or " test ticket" in low:
        return True
    return is_noise_client(blob)


def is_test_family_ticket(item: dict) -> bool:
    """Obvious test tickets only. empirebox2026 is the founder inbox — keep those."""
    sender = _blob(item.get("customer"), item.get("sender"))
    body = _blob(item.get("name"), item.get("message"), item.get("subject"))
    founder_inbox = "empirebox2026" in sender.casefold()
    if founder_inbox:
        return _obvious_test_body(body)
    if is_noise_client(sender):
        return True
    return _obvious_test_body(body)


def format_et(value: Any) -> str:
    """Friendly Eastern date: 'Mon Oct 13, 9 AM'."""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        dt = None
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(text[:26], fmt)
                break
            except ValueError:
                continue
        if dt is None:
            try:
                raw = text.replace("Z", "+00:00") if text.endswith("Z") else text
                dt = datetime.fromisoformat(raw)
            except ValueError:
                return text
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ET)
    else:
        dt = dt.astimezone(ET)
    hour = dt.strftime("%I").lstrip("0") or "0"
    ampm = dt.strftime("%p")
    if dt.minute:
        return f"{dt.strftime('%a %b')} {dt.day}, {hour}:{dt.strftime('%M')} {ampm}"
    return f"{dt.strftime('%a %b')} {dt.day}, {hour} {ampm}"


def is_promotional_mail(msg: dict) -> bool:
    labels = {str(x) for x in (msg.get("labels") or msg.get("labelIds") or [])}
    if labels & PROMO_LABELS:
        return True
    unsub = msg.get("list_unsubscribe") or msg.get("list-unsubscribe") or ""
    if str(unsub).strip():
        return True
    blob = _blob(
        msg.get("from"), msg.get("from_email"), msg.get("from_name"),
        msg.get("subject"), msg.get("preview"),
    ).lower()
    if any(sender in blob for sender in MARKETING_SENDERS):
        return True
    if any(h in blob for h in NOREPLY_HINTS) and any(k in blob for k in MARKETING_KEYWORDS + ("sale", "offer", "deal")):
        return True
    if any(h in blob for h in NOREPLY_HINTS) and any(s in blob for s in MARKETING_SENDERS):
        return True
    if any(k in blob for k in MARKETING_KEYWORDS):
        return True
    # Bare no-reply from a store/brand is still promo.
    if any(h in blob for h in NOREPLY_HINTS) and any(
        w in blob for w in ("store", "retail", "promo", "marketing", "newsletter")
    ):
        return True
    return False


def is_bank_notice(msg: dict) -> bool:
    blob = _blob(msg.get("from"), msg.get("from_email"), msg.get("subject"), msg.get("preview"), msg.get("name")).lower()
    return any(h in blob for h in BANK_HINTS)


def mail_account_label(source: str | None) -> str:
    key = (source or "").strip().lower()
    if key in ("gmail", "business_gmail", "business-gmail"):
        return "Business Gmail"
    if key in ("outlook", "nelma", "outlook/nelma"):
        return "Outlook/Nelma"
    return source or "mail"


def mail_dedupe_key(msg: dict) -> str:
    for key in ("thread_id", "threadId", "message_id", "id"):
        val = str(msg.get(key) or "").strip()
        if val:
            return val.casefold()
    return _blob(msg.get("name"), msg.get("subject"), msg.get("from")).casefold()


def dedupe_mail(items: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        key = mail_dedupe_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def is_backlog_noise(title: Any) -> bool:
    low = str(title or "").lower()
    return any(m in low for m in BACKLOG_NOISE)


def is_approval_flagged(item: dict) -> bool:
    if item.get("needs_approval") or item.get("decision_needed"):
        return True
    title = str(item.get("name") or item.get("title") or "").lower()
    source = str(item.get("source") or item.get("kind") or "").lower()
    if "approval" in source or source == "approval_queue":
        return True
    return any(h in title for h in APPROVAL_HINTS) or "approv" in title or "voice" in title


def keep_founder_decision(item: dict) -> bool:
    """Yes/no items only: founder approvals, voice requests, approval queue."""
    return is_approval_flagged(item)


def stale_task_count(items: Iterable[dict], *, older_than_days: int = 30) -> int:
    seen: set[str] = set()
    n = 0
    for item in items:
        key = str(item.get("id") or item.get("name") or "").strip().lower()
        if key:
            if key in seen:
                continue
            seen.add(key)
        if keep_founder_decision(item):
            continue
        age = item.get("age_days")
        if age is None:
            continue
        if int(age) > older_than_days:
            n += 1
    return n


def dedupe_named(items: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        key = str(item.get("name") or item.get("id") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def filter_real_money(items: Iterable[dict]) -> list[dict]:
    real = []
    for item in items:
        if is_flagged_test(item) or is_noise_client(item.get("customer") or item.get("name")):
            continue
        if is_zero_amount(item.get("amount")):
            continue
        real.append(item)
    real.sort(key=lambda i: (-float(i.get("amount") or 0), -int(i.get("age_days") or 0)))
    return real


def filter_followup_quotes(items: Iterable[dict], *, max_age_days: int = 60) -> list[dict]:
    awaiting = {"sent", "proposal", "founder_review"}
    real = []
    for item in items:
        status = str(item.get("status") or "").lower()
        if status not in awaiting:
            continue
        if is_zero_amount(item.get("amount")):
            continue
        if is_flagged_test(item) or is_noise_client(item.get("customer")) or is_placeholder_name(item.get("customer")):
            continue
        age = item.get("window_age_days")
        if age is None:
            age = item.get("age_days")
        if age is not None and int(age) > max_age_days:
            continue
        real.append(item)
    real.sort(key=lambda i: (-int(i.get("age_days") or 0), -float(i.get("amount") or 0)))
    return real
