"""Ignore system, founder, and Max mail before any job match.

Own-address and help-ticket filters live here so job-mail does not
import brief_filters. Never treats Empire / EmpireBox as a supplier.
"""

from __future__ import annotations

import os
import re
from typing import Optional

_SUBJECT_PREFIX_RE = re.compile(r"^(re|fwd|fw):\s*", re.I)

INTERNAL_ADDRS = frozenset({
    "empirebox2026@gmail.com",
    "rafa22giraldo@gmail.com",
    "max@empirebox.store",
    "workroom@empirebox.store",
    "woodcraft@empirebox.store",
    "noreply@empirebox.store",
    "no-reply@empirebox.store",
    "info@empirebox.store",
})

INTERNAL_DOMAINS = frozenset({
    "empirebox.store",
})

INTERNAL_SUBJECTS = (
    "ayuda de max-e",
    "ayuda de maxine",
    "empire morning brief",
    "tu acceso a amp",
)

INTERNAL_FROM_NAMES = (
    "max — empire ai",
    "max - empire ai",
    "max- empire ai",
    "max — empire",
    "empire ai",
)

_ENV_ADDR_KEYS = (
    "FOUNDER_EMAIL",
    "FOUNDER_EMAILS",
    "FOUNDER_ACCESS_EMAILS",
    "WORKROOM_EMAIL",
    "WOODCRAFT_EMAIL",
)

_EMPIRE_NAME_RE = re.compile(r"\bempire(?:box)?\b", re.I)


def parse_from_header(raw: Optional[str]) -> tuple[str, str]:
    blob = (raw or "").strip()
    addr_m = re.search(r"<([^>]+)>", blob)
    email = (addr_m.group(1) if addr_m else blob).strip().lower()
    name = re.sub(r"<[^>]+>", "", blob).strip().strip('"').strip()
    if "@" in name and not addr_m:
        name = name.split("@")[0].replace(".", " ").title()
    if "@" not in email:
        email = ""
    return name, email


def _norm(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def own_addresses() -> set[str]:
    out = set(INTERNAL_ADDRS)
    for key in _ENV_ADDR_KEYS:
        raw = os.getenv(key) or ""
        for part in raw.split(","):
            addr = part.strip().lower()
            if "@" in addr:
                out.add(addr)
    return out


def _email_is_own(email: str) -> bool:
    addr = (email or "").strip().lower()
    if not addr or "@" not in addr:
        return False
    if addr in own_addresses():
        return True
    domain = addr.rsplit("@", 1)[-1]
    return domain in INTERNAL_DOMAINS


def _subject_is_internal(subject: Optional[str]) -> bool:
    text = _SUBJECT_PREFIX_RE.sub("", _norm(subject))
    return any(tag in text for tag in INTERNAL_SUBJECTS)


def _from_name_is_internal(name: Optional[str]) -> bool:
    n = _norm(name)
    if not n:
        return False
    if any(tag in n for tag in INTERNAL_FROM_NAMES):
        return True
    return n in {"max", "max-e", "maxine", "empire"}


def is_empire_identity(msg: dict) -> bool:
    """True when the sender is Empire / Max / our own mailbox."""
    name, email = parse_from_header(msg.get("from"))
    if not name:
        name = str(msg.get("from_name") or "")
    if not email:
        email = str(msg.get("from_email") or "").strip().lower()
    if _email_is_own(email):
        return True
    if _from_name_is_internal(name):
        return True
    if _EMPIRE_NAME_RE.search(name or ""):
        return True
    return False


def is_internal_mail(msg: dict) -> bool:
    """Help tickets, founder self-sends, and Max notifications — never a job."""
    name, email = parse_from_header(msg.get("from"))
    if not email:
        email = str(msg.get("from_email") or "").strip().lower()
    if _email_is_own(email):
        return True
    if _from_name_is_internal(name or msg.get("from_name")):
        return True
    if _subject_is_internal(msg.get("subject")):
        return True
    return False
