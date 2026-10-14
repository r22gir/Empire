"""Match inbound mail to a job or client. Read-only against the local DB.

A name alone (full or partial) never attaches. Attach requires an email,
estimate number, job number, sidemark, or address match. A full first-and-
last name may accompany one of those keys but is never enough by itself.
Short / common job titles (Lobby, Living, Channel, …) are ignored.
Ties or scores within 10 points go to review.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.services.job_mail_intake.extract import extract_mail_facts

COMMON_TITLE_WORDS = {
    "lobby", "living", "room", "kitchen", "dining", "bedroom", "office",
    "hall", "hallway", "bath", "bathroom", "master", "guest", "den",
    "channel", "shop", "store", "house", "home", "suite", "unit",
    "area", "space", "entry", "foyer", "patio", "porch",
}

STRONG_KEYS = {
    "client_email",
    "customer_email",
    "address",
    "customer_address",
    "sidemark",
    "job_number",
}

# Estimate numbers are a weak hint only. A lone EST-YYYY-NNN never attaches.
CLOSED_STATUSES = frozenset({"completed", "cancelled"})
COMPLETED_PENALTY = 50
ESTIMATE_SCORE = 25

MIN_TITLE_LEN = 8
MIN_ATTACH_SCORE = 40
AMBIGUOUS_GAP = 10


def _norm(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _name_parts(value: Optional[str]) -> list[str]:
    return [t for t in re.findall(r"[a-z]+", _norm(value)) if len(t) >= 2]


def _tokens(value: Optional[str]) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", _norm(value)) if t not in {
        "the", "and", "for", "from", "with", "this", "that", "your", "our",
    }}


def _addr_key(value: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]", "", _norm(value))


def _parse_from(raw: Optional[str]) -> tuple[str, str]:
    blob = (raw or "").strip()
    addr_m = re.search(r"<([^>]+)>", blob)
    email = (addr_m.group(1) if addr_m else blob).strip().lower()
    name = re.sub(r"<[^>]+>", "", blob).strip().strip('"').strip()
    if "@" in name and not addr_m:
        name = name.split("@")[0].replace(".", " ").title()
    if "@" not in email:
        email = ""
    return name, email


def _safe_rows(conn, sql: str, params: tuple = ()) -> list[dict]:
    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception:
        return []
    out = []
    for row in rows:
        try:
            out.append(dict(row))
        except Exception:
            out.append(row)
    return out


def _job_blob(job: dict) -> str:
    meta = job.get("metadata") or job.get("metadata_json") or ""
    if isinstance(meta, dict):
        meta = json.dumps(meta)
    return " ".join(
        str(job.get(k) or "")
        for k in (
            "title", "job_number", "client_name", "customer_name", "client_email",
            "client_address", "address", "notes", "description", "room",
        )
    ) + " " + str(meta)


def _usable_title(title: str) -> bool:
    t = _norm(title)
    if not t or len(t) < MIN_TITLE_LEN:
        return False
    parts = _name_parts(t)
    if parts and all(p in COMMON_TITLE_WORDS for p in parts):
        return False
    if t in COMMON_TITLE_WORDS:
        return False
    return True


def _full_name_match(left: str, right: str) -> bool:
    a = _name_parts(left)
    b = _name_parts(right)
    if len(a) < 2 or len(b) < 2:
        return False
    return a == b or (a[0] == b[0] and a[-1] == b[-1])


def _has_strong_key(reason: str) -> bool:
    parts = {p.strip() for p in (reason or "").split(",") if p.strip()}
    return bool(parts & STRONG_KEYS)


def _score_job(job: dict, *, name: str, email: str, facts: dict, blob: str) -> tuple[int, str]:
    score = 0
    reasons: list[str] = []
    job_blob = _job_blob(job)
    job_norm = _norm(job_blob)

    if email and email in _norm(job.get("client_email") or job.get("customer_email") or ""):
        score += 80
        reasons.append("client_email")

    cname = _norm(job.get("client_name") or job.get("customer_name") or "")
    if name and cname and _full_name_match(name, cname):
        score += 20
        reasons.append("client_full_name")

    addr = _addr_key(job.get("client_address") or job.get("address") or "")
    mail_addr = _addr_key(blob)
    if addr and len(addr) >= 8 and addr in mail_addr:
        score += 45
        reasons.append("address")

    for est in facts.get("estimate_numbers") or []:
        if _norm(est) in job_norm or _norm(est) == _norm(job.get("quote_number") or ""):
            score += ESTIMATE_SCORE
            reasons.append(f"estimate:{est}")

    status = _norm(job.get("status"))
    if status in CLOSED_STATUSES:
        score -= COMPLETED_PENALTY
        reasons.append("completed_low")

    for mark in facts.get("sidemarks") or []:
        if _norm(mark) and _norm(mark) in job_norm:
            score += 70
            reasons.append("sidemark")

    title = _norm(job.get("title") or "")
    if _usable_title(title) and title in _norm(blob):
        score += 25
        reasons.append("job_title")

    jn = _norm(job.get("job_number") or "")
    if jn and jn in _norm(blob):
        score += 85
        reasons.append("job_number")

    return score, ",".join(reasons) or "none"


def _load_jobs(conn) -> list[dict]:
    cols_jobs = set()
    try:
        cols_jobs = {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    except Exception:
        return []
    if not cols_jobs:
        return []
    select = ["j.*"]
    if "name" in {r[1] for r in _pragma(conn, "customers")}:
        select.append("c.name AS customer_name")
        select.append("c.email AS customer_email")
        select.append("c.address AS customer_address")
        sql = f"SELECT {', '.join(select)} FROM jobs j LEFT JOIN customers c ON c.id = j.customer_id"
    else:
        sql = "SELECT j.* FROM jobs j"
    return _safe_rows(conn, sql)


def _pragma(conn, table: str) -> list:
    try:
        return list(conn.execute(f"PRAGMA table_info({table})").fetchall())
    except Exception:
        return []


def _load_customers(conn) -> list[dict]:
    return _safe_rows(conn, "SELECT * FROM customers")


def _load_quotes(conn) -> list[dict]:
    return _safe_rows(
        conn,
        "SELECT id, quote_number, customer_name, customer_email, customer_address, "
        "project_name, notes, job_id, customer_id FROM quotes_v2",
    )


def _unmatched(name: str, email: str, facts: dict, reason: str, score: int = 0) -> dict[str, Any]:
    return {
        "matched": False,
        "confidence": score,
        "reason": reason,
        "job_id": None,
        "job_title": None,
        "job_number": None,
        "customer_id": None,
        "customer_name": None,
        "from_name": name,
        "from_email": email,
        "facts": facts,
        "sent": False,
    }


def match_message(conn, msg: dict) -> dict[str, Any]:
    """Return the best job/client match or an unmatched payload."""
    name, email = _parse_from(msg.get("from"))
    facts = extract_mail_facts(msg)
    blob = " ".join(str(msg.get(k) or "") for k in ("subject", "from", "preview", "body"))

    scored: list[tuple[int, str, dict]] = []
    for job in _load_jobs(conn):
        score, reason = _score_job(job, name=name, email=email, facts=facts, blob=blob)
        if score > 0:
            scored.append((score, reason, job))
    scored.sort(key=lambda row: row[0], reverse=True)

    best: Optional[dict] = scored[0][2] if scored else None
    best_score = scored[0][0] if scored else 0
    best_reason = scored[0][1] if scored else ""

    if len(scored) >= 2 and scored[1][0] > 0 and best_score - scored[1][0] <= AMBIGUOUS_GAP:
        return _unmatched(name, email, facts, "ambiguous", best_score)

    customer_id = None
    customer_name = None
    if not best or best_score < MIN_ATTACH_SCORE or not _has_strong_key(best_reason):
        for cust in _load_customers(conn):
            cscore = 0
            creason = []
            if email and email == _norm(cust.get("email")):
                cscore += 80
                creason.append("customer_email")
            cname = _norm(cust.get("name"))
            if name and cname and _full_name_match(name, cname):
                cscore += 20
                creason.append("customer_full_name")
            caddr = _addr_key(cust.get("address"))
            if caddr and len(caddr) >= 8 and caddr in _addr_key(blob):
                cscore += 40
                creason.append("customer_address")
            if cscore >= MIN_ATTACH_SCORE and _has_strong_key(",".join(creason)) and cscore > best_score:
                customer_id = cust.get("id")
                customer_name = cust.get("name")
                best_score = cscore
                best_reason = ",".join(creason)
                candidates = [
                    job for job in _load_jobs(conn)
                    if job.get("customer_id") == customer_id
                ]
                open_jobs = [
                    job for job in candidates
                    if _norm(job.get("status")) not in CLOSED_STATUSES
                ]
                pick = (open_jobs or candidates)
                if pick:
                    best = pick[0]
                    best_reason = best_reason + ",customer_job"

    has_strong = _has_strong_key(best_reason)
    matched = bool(best and best_score >= MIN_ATTACH_SCORE and has_strong)
    if best and best_score >= MIN_ATTACH_SCORE and not has_strong:
        return _unmatched(name, email, facts, "name_only", best_score)

    return {
        "matched": matched,
        "confidence": best_score,
        "reason": best_reason,
        "job_id": (best or {}).get("id") if matched else None,
        "job_title": (best or {}).get("title") if matched else None,
        "job_number": (best or {}).get("job_number") if matched else None,
        "customer_id": (best or {}).get("customer_id") if matched else customer_id,
        "customer_name": (best or {}).get("client_name") or (best or {}).get("customer_name") or customer_name,
        "from_name": name,
        "from_email": email,
        "facts": facts,
        "sent": False,
    }
