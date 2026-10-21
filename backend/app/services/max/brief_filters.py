"""Shared noise filters for the daily brief and desk jobs.

Keeps Rafael's brief to real money, real quotes, human mail, and real
yes/no approvals. Test/purge clients and marketing mail never ship as news.
"""
from __future__ import annotations

import fnmatch
import os
import re
from datetime import datetime
from typing import Any, Iterable
from zoneinfo import ZoneInfo

# One configurable list. Exact match unless the pattern has * or ?.
# Override with BRIEF_TEST_CLIENT_PATTERNS (comma-separated) if needed.
DEFAULT_TEST_CLIENT_PATTERNS = (
    "*test*",
    "TrustTest",
    "HOTFIX5*",
    "Canonical Customer*",
    "Routed Customer*",
    "*MOCK*",
    "MOCK-SWEEP*",
    "TruthGuard*",
    "*SMOKE*",
    "diag-probe*",
    "Jane Smith",
    "Customer",
    "purge candidate",
    "Empresa Prueba",
    "LiveProof",
    "ManualLine",
    "MAX *",
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
    "high point market", "high point", "hpmkt", "trade show",
    "tradeshow", "trade-show", "market week",
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

SELF_SEND_ADDRS = (
    "max@empirebox.store",
    "max@empirebox",
    "empirebox2026@gmail.com",
    "noreply@empirebox",
    "no-reply@empirebox",
)
SELF_SEND_SUBJECTS = (
    "empire morning brief",
    "tu acceso a amp",
    "ayuda de max-e",
    "ayuda de maxine",
)
SELF_SEND_FROM = (
    "max — empire ai",
    "max - empire ai",
    "max- empire ai",
    "empire ai",
)
FAMILY_TITLE_LEN = 60
_SUBJECT_PREFIX_RE = re.compile(r"^(re|fwd|fw):\s*", re.I)

FOUNDER_ASSIGNEES = frozenset({
    "founder", "rafael", "rg", "rafa", "r22gir", "owner",
})
FOUNDER_TODO_TAG_HINTS = (
    "founder to-do", "founder todo", "founder-todo", "founder_todo",
    "founder-to-do",
)
PRIORITY_RANK = {"urgent": 0, "high": 1, "normal": 2, "medium": 2, "low": 3}


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
    if text.casefold().startswith("max "):
        return True
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


_TESTISH_WORDS = frozenset({
    "test", "tests", "testing", "prueba", "pruebas", "mock", "sweep",
    "tres", "uno", "dos", "hola", "saludo", "ticket",
})
_TESTISH_FILLER = frozenset({"un", "una", "de", "la", "el", "a", "the", "of"})


def _obvious_test_body(text: str) -> bool:
    blob = str(text or "").strip()
    if not blob:
        return False
    low = blob.casefold()
    if "un saludo de prueba" in low:
        return True
    if any(tok in low for tok in ("mock-sweep", "purge candidate", "trusttest")):
        return True
    if low.startswith("test ") or low == "test" or " test ticket" in low:
        return True
    return is_noise_client(blob)


def _non_test_words(text: str) -> list[str]:
    words = re.findall(r"[0-9a-záéíóúñü]+", str(text or "").casefold())
    return [w for w in words if w not in _TESTISH_WORDS and w not in _TESTISH_FILLER]


def has_real_family_transcript(text: Any) -> bool:
    """Transcript is real if it is longer than ~30 chars and not just test words."""
    raw = " ".join(str(text or "").split())
    if len(raw) < 30:
        return False
    return len(" ".join(_non_test_words(raw))) >= 12


def family_has_attachments(item: dict | None) -> bool:
    if not item:
        return False
    kinds = item.get("attachment_kinds") or []
    if kinds:
        return True
    atts = item.get("attachments") or []
    return bool(atts)


def family_ticket_title(
    *,
    transcript: str = "",
    message: str = "",
    attachment_kinds: Iterable[str] | None = None,
) -> str:
    """No title column: transcript, else short message, ~60 chars + attachment kinds."""
    raw = ""
    if (transcript or "").strip():
        raw = next((ln.strip() for ln in str(transcript).splitlines() if ln.strip()), "")
        raw = raw or str(transcript).strip()
    if not raw:
        raw = str(message or "").strip()
    title = " ".join(raw.split())
    if len(title) > FAMILY_TITLE_LEN:
        title = title[: FAMILY_TITLE_LEN - 1].rstrip() + "…"
    kinds: list[str] = []
    for kind in attachment_kinds or []:
        k = str(kind or "").strip()
        if k and k not in kinds:
            kinds.append(k)
    if kinds:
        suffix = f" [{', '.join(kinds)}]"
        title = f"{title}{suffix}" if title else suffix.strip()
    return title or "Family help"


def is_test_family_ticket(item: dict) -> bool:
    """Do not drop on a short test *message* if transcript or attachments are real.

    Live tickets often have message "Test", "Test tres", or "un saludo de
    prueba" and the real ask in the transcript or an attachment.
    """
    transcript = item.get("transcript") or ""
    if has_real_family_transcript(transcript) or family_has_attachments(item):
        return False
    sender = _blob(item.get("sender"))
    body = _blob(item.get("message"), item.get("subject"))
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


def is_self_sent_mail(msg: dict) -> bool:
    """Max/Empire notifications and empirebox2026 self-sends — not unanswered mail."""
    frm = _blob(msg.get("from"), msg.get("from_email"), msg.get("from_name"), msg.get("customer")).lower()
    subj = _blob(msg.get("subject"), msg.get("name")).lower()
    if any(addr in frm for addr in SELF_SEND_ADDRS):
        return True
    if any(tag in frm for tag in SELF_SEND_FROM):
        return True
    if any(s in subj for s in SELF_SEND_SUBJECTS):
        return True
    return False


def normalize_mail_subject(msg: dict) -> str:
    text = _blob(msg.get("subject"), msg.get("name"))
    text = _SUBJECT_PREFIX_RE.sub("", text).strip().lower()
    return re.sub(r"\s+", " ", text)


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


def mail_dedupe_keys(msg: dict) -> list[str]:
    keys: list[str] = []
    for key in ("thread_id", "threadId", "message_id", "id"):
        val = str(msg.get(key) or "").strip().casefold()
        if val:
            keys.append(f"id:{val}")
    subj = normalize_mail_subject(msg)
    if subj:
        keys.append(f"subj:{subj}")
    return keys


def mail_dedupe_key(msg: dict) -> str:
    keys = mail_dedupe_keys(msg)
    return keys[0] if keys else ""


def dedupe_mail(items: Iterable[dict]) -> list[dict]:
    """Collapse repeats by thread/message id and by subject across sources/statuses."""
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        keys = mail_dedupe_keys(item)
        if not keys or any(k in seen for k in keys):
            continue
        seen.update(keys)
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


def _task_tags(item: dict) -> str:
    raw = item.get("tags")
    if isinstance(raw, (list, tuple)):
        return " ".join(str(t) for t in raw)
    return str(raw or "")


def is_founder_todo(item: dict | None) -> bool:
    if not item:
        return False
    assigned = str(item.get("assigned_to") or "").strip().casefold()
    if assigned in FOUNDER_ASSIGNEES:
        return True
    tags = _task_tags(item).casefold().replace("_", " ").replace("-", " ")
    if any(h.replace("-", " ").replace("_", " ") in tags for h in FOUNDER_TODO_TAG_HINTS):
        return True
    if "founder" in tags and "todo" in tags:
        return True
    return False


def founder_todo_sort_key(item: dict) -> tuple:
    pri = PRIORITY_RANK.get(str(item.get("priority") or "normal").lower(), 2)
    due = str(item.get("due_date") or "9999")
    return (0 if item.get("new_since_yesterday") else 1, pri, due)


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
