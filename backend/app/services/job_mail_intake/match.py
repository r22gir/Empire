"""Match inbound mail to a job or client. Read-only against the local DB."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.services.job_mail_intake.extract import extract_mail_facts


def _norm(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


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


def _score_job(job: dict, *, name: str, email: str, facts: dict, blob: str) -> tuple[int, str]:
    score = 0
    reasons: list[str] = []
    job_blob = _job_blob(job)
    job_norm = _norm(job_blob)

    if email and email in _norm(job.get("client_email") or job.get("customer_email") or ""):
        score += 80
        reasons.append("client_email")

    cname = _norm(job.get("client_name") or job.get("customer_name") or "")
    if name and cname and (cname in _norm(name) or _norm(name) in cname):
        score += 50
        reasons.append("client_name")
    elif name and _tokens(name) & _tokens(cname):
        score += 30
        reasons.append("client_name_token")

    addr = _addr_key(job.get("client_address") or job.get("address") or "")
    mail_addr = _addr_key(blob)
    if addr and len(addr) >= 8 and addr in mail_addr:
        score += 45
        reasons.append("address")

    for est in facts.get("estimate_numbers") or []:
        if _norm(est) in job_norm or _norm(est) == _norm(job.get("quote_number") or ""):
            score += 90
            reasons.append(f"estimate:{est}")

    for mark in facts.get("sidemarks") or []:
        if _norm(mark) and _norm(mark) in job_norm:
            score += 70
            reasons.append("sidemark")

    title = _norm(job.get("title") or "")
    if title and len(title) >= 4 and title in _norm(blob):
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


def match_message(conn, msg: dict) -> dict[str, Any]:
    """Return the best job/client match or an unmatched payload."""
    name, email = _parse_from(msg.get("from"))
    facts = extract_mail_facts(msg)
    blob = " ".join(str(msg.get(k) or "") for k in ("subject", "from", "preview", "body"))

    best: Optional[dict] = None
    best_score = 0
    best_reason = ""
    for job in _load_jobs(conn):
        score, reason = _score_job(job, name=name, email=email, facts=facts, blob=blob)
        if score > best_score:
            best_score = score
            best = job
            best_reason = reason

    customer_id = None
    customer_name = None
    if not best or best_score < 40:
        for cust in _load_customers(conn):
            cscore = 0
            creason = []
            if email and email == _norm(cust.get("email")):
                cscore += 80
                creason.append("customer_email")
            cname = _norm(cust.get("name"))
            if name and cname and (cname in _norm(name) or _norm(name) in cname):
                cscore += 45
                creason.append("customer_name")
            caddr = _addr_key(cust.get("address"))
            if caddr and len(caddr) >= 8 and caddr in _addr_key(blob):
                cscore += 40
                creason.append("customer_address")
            if cscore >= 40 and cscore > best_score:
                customer_id = cust.get("id")
                customer_name = cust.get("name")
                best_score = cscore
                best_reason = ",".join(creason)
                # Prefer a job for this customer if one exists
                for job in _load_jobs(conn):
                    if job.get("customer_id") == customer_id:
                        best = job
                        best_reason = best_reason + ",customer_job"
                        break

    if (not best or best_score < 40) and facts.get("estimate_numbers"):
        for q in _load_quotes(conn):
            qn = (q.get("quote_number") or "").upper()
            if qn in {n.upper() for n in facts["estimate_numbers"]}:
                best_score = 95
                best_reason = f"estimate:{qn}"
                if q.get("job_id"):
                    for job in _load_jobs(conn):
                        if str(job.get("id")) == str(q.get("job_id")):
                            best = job
                            break
                customer_id = customer_id or q.get("customer_id")
                customer_name = customer_name or q.get("customer_name")
                if best:
                    break
                # Quote matched but no job — still a client match
                if q.get("customer_name"):
                    customer_id = customer_id or q.get("customer_id")
                    customer_name = customer_name or q.get("customer_name")

    matched = bool(best and best_score >= 40)
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
