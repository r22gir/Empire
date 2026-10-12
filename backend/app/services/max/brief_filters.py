"""Shared noise filters for the daily brief and desk jobs.

Keeps Rafael's brief to real money, real quotes, human mail, and real
approvals. Test/purge clients and marketing mail never ship as "news".
"""
from __future__ import annotations

import re
from typing import Any, Iterable

TEST_CLIENT_MARKERS = (
    "test residue",
    "purge candidate",
    "e2e test",
    "test client",
    "pipeline test",
    "woodcraft test",
    "empresa prueba",
)

# Standalone TEST token (invoice names like "TEST-2044" or "Acme TEST")
_TEST_TOKEN = re.compile(r"(?:^|[^a-z0-9])test(?:$|[^a-z0-9])", re.I)

PLACEHOLDER_NAMES = frozenset({"customer", "unknown", "client", "n/a", "tbd", "test"})

PROMO_LABELS = frozenset({
    "CATEGORY_PROMOTIONS",
    "CATEGORY_SOCIAL",
    "CATEGORY_UPDATES",
    "CATEGORY_FORUMS",
})

MARKETING_SENDERS = (
    "macy", "macys.com", "wayfair", "facebook", "fbmail", "experian",
    "etsy", "pinterest", "linkedin", "mailchimp", "substack",
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


def is_noise_client(name: Any) -> bool:
    text = str(name or "").strip()
    if not text:
        return False
    low = text.lower()
    if any(m in low for m in TEST_CLIENT_MARKERS):
        return True
    if _TEST_TOKEN.search(text):
        return True
    return False


def is_placeholder_name(name: Any) -> bool:
    return str(name or "").strip().lower() in PLACEHOLDER_NAMES


def is_zero_amount(value: Any) -> bool:
    try:
        return abs(float(value or 0)) < 0.005
    except (TypeError, ValueError):
        return True


def is_test_family_ticket(item: dict) -> bool:
    blob = _blob(
        item.get("customer"), item.get("name"), item.get("sender"),
        item.get("message"), item.get("from_email"),
    ).lower()
    if "empirebox2026" in blob:
        return True
    return is_noise_client(blob)


def is_promotional_mail(msg: dict) -> bool:
    labels = {str(x) for x in (msg.get("labels") or msg.get("labelIds") or [])}
    if labels & PROMO_LABELS:
        return True
    unsub = msg.get("list_unsubscribe") or msg.get("list-unsubscribe") or ""
    if str(unsub).strip():
        return True
    blob = _blob(msg.get("from"), msg.get("from_email"), msg.get("from_name"), msg.get("subject")).lower()
    return any(sender in blob for sender in MARKETING_SENDERS)


def mail_account_label(source: str | None) -> str:
    key = (source or "").strip().lower()
    if key in ("gmail", "business_gmail", "business-gmail"):
        return "Business Gmail"
    if key in ("outlook", "nelma", "outlook/nelma"):
        return "Outlook/Nelma"
    return source or "mail"


def is_backlog_noise(title: Any) -> bool:
    low = str(title or "").lower()
    return any(m in low for m in BACKLOG_NOISE)


def is_approval_flagged(item: dict) -> bool:
    if item.get("needs_approval") or item.get("decision_needed"):
        return True
    title = str(item.get("name") or item.get("title") or "").lower()
    status = str(item.get("status") or "").lower()
    if status == "waiting":
        return any(h in title for h in APPROVAL_HINTS) or "approv" in title or "voice" in title
    return any(h in title for h in APPROVAL_HINTS)


def keep_founder_decision(item: dict) -> bool:
    title = str(item.get("name") or item.get("title") or "")
    if is_backlog_noise(title):
        return is_approval_flagged(item)
    if is_approval_flagged(item) or "voice" in title.lower() or "approv" in title.lower():
        return True
    if item.get("kind") == "stuck_task":
        return True
    return False


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
        if is_noise_client(item.get("customer") or item.get("name")):
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
        if is_noise_client(item.get("customer")) or is_placeholder_name(item.get("customer")):
            continue
        age = item.get("window_age_days")
        if age is None:
            age = item.get("age_days")
        if age is not None and int(age) > max_age_days:
            continue
        real.append(item)
    real.sort(key=lambda i: (-int(i.get("age_days") or 0), -float(i.get("amount") or 0)))
    return real
