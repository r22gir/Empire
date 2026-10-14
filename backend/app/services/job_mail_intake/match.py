"""Match inbound mail to a job or client. Read-only against the local DB.

A name alone (full or partial) never attaches. Attach requires an email,
estimate number (exactly one OPEN job), job/CF number, contact, sidemark,
or address match. Completed jobs rank low. Several open jobs for one
customer go to review as ambiguous.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.services.job_mail_intake.extract import extract_mail_facts, job_codes

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
    "job_code",
    "cf_number",
    "contact_email",
    "contact_domain",
    "contact_name",
    "estimate_open",
}

SHARED_CUSTOMER_KEYS = {
    "client_email",
    "customer_email",
    "contact_email",
    "contact_domain",
    "contact_name",
    "customer_job",
}

CLOSED_STATUSES = frozenset({"completed", "cancelled"})
COMPLETED_PENALTY = 50
ESTIMATE_SCORE = 25
ESTIMATE_OPEN_SCORE = 90

PUBLIC_MAIL_DOMAINS = frozenset({
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk",
    "hotmail.com", "outlook.com", "live.com", "msn.com",
    "icloud.com", "me.com", "aol.com", "proton.me", "protonmail.com",
    "mail.com", "ymail.com",
})

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


def _email_domain(email: Optional[str]) -> str:
    addr = (email or "").strip().lower()
    if "@" not in addr:
        return ""
    return addr.rsplit("@", 1)[-1]


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


def _coerce_contact(raw: Any) -> Optional[dict]:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        if "@" in text and " " not in text.strip("<>"):
            return {"name": "", "email": text.strip("<>").lower(), "company": ""}
        return {"name": text, "email": "", "company": ""}
    if not isinstance(raw, dict):
        return None
    email = str(raw.get("email") or raw.get("address") or "").strip().lower()
    name = str(raw.get("name") or raw.get("contact") or "").strip()
    company = str(raw.get("company") or raw.get("firm") or "").strip()
    if not (email or name or company):
        return None
    return {"name": name, "email": email, "company": company}


def _parse_contacts_blob(raw: Any) -> list[dict]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [c for c in (_coerce_contact(x) for x in raw) if c]
    if isinstance(raw, dict):
        nested = raw.get("contacts")
        if isinstance(nested, list):
            return _parse_contacts_blob(nested)
        item = _coerce_contact(raw)
        return [item] if item else []
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("[") or text.startswith("{"):
            try:
                return _parse_contacts_blob(json.loads(text))
            except Exception:
                return []
    return []


def _job_contacts(job: dict) -> list[dict]:
    items = []
    items.extend(_parse_contacts_blob(job.get("contacts")))
    meta = job.get("metadata") or job.get("metadata_json")
    if isinstance(meta, str) and meta.strip():
        try:
            meta = json.loads(meta)
        except Exception:
            meta = None
    if isinstance(meta, dict):
        items.extend(_parse_contacts_blob(meta.get("contacts")))
    seen = set()
    unique = []
    for item in items:
        key = (item.get("email"), _norm(item.get("name")), _norm(item.get("company")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _job_blob(job: dict) -> str:
    meta = job.get("metadata") or job.get("metadata_json") or ""
    if isinstance(meta, dict):
        meta = json.dumps(meta)
    contacts = job.get("contacts") or ""
    if isinstance(contacts, (list, dict)):
        contacts = json.dumps(contacts)
    return " ".join(
        str(job.get(k) or "")
        for k in (
            "title", "job_number", "client_name", "customer_name", "client_email",
            "client_address", "address", "notes", "description", "room",
            "quote_number",
        )
    ) + " " + str(meta) + " " + str(contacts)


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


def _contact_name_hit(sender_name: str, contact_name: str) -> bool:
    """Full first+last only. A one-word listed name is never enough by itself."""
    return _full_name_match(sender_name, contact_name)


def _is_open(job: dict) -> bool:
    return _norm(job.get("status")) not in CLOSED_STATUSES


def _has_strong_key(reason: str) -> bool:
    parts = {p.strip() for p in (reason or "").split(",") if p.strip()}
    if "estimate_open" in parts or any(p.startswith("estimate_open:") for p in parts):
        return True
    return bool(parts & STRONG_KEYS)


def _reason_parts(reason: str) -> set[str]:
    return {p.strip() for p in (reason or "").split(",") if p.strip()}


def _only_shared_customer_keys(reason: str) -> bool:
    parts = _reason_parts(reason)
    strong = {p for p in parts if p in STRONG_KEYS or p.startswith("estimate_open")}
    if not strong:
        return False
    return strong <= SHARED_CUSTOMER_KEYS


def _score_job(job: dict, *, name: str, email: str, facts: dict, blob: str) -> tuple[int, str]:
    score = 0
    reasons: list[str] = []
    job_blob = _job_blob(job)
    job_norm = _norm(job_blob)
    domain = _email_domain(email)

    job_emails = {
        _norm(job.get("client_email") or ""),
        _norm(job.get("customer_email") or ""),
    }
    if email and email in job_emails:
        score += 80
        reasons.append("client_email")

    for contact in _job_contacts(job):
        c_email = _norm(contact.get("email"))
        c_domain = _email_domain(contact.get("email"))
        email_hit = bool(email and c_email and email == c_email)
        domain_hit = bool(
            domain and c_domain and domain == c_domain and domain not in PUBLIC_MAIL_DOMAINS
        )
        if email_hit:
            score += 80
            reasons.append("contact_email")
        elif domain_hit:
            score += 70
            reasons.append("contact_domain")
        # One-word listed names ("Emma") never attach on first name alone.
        if name and _contact_name_hit(name, contact.get("name") or ""):
            score += 75
            reasons.append("contact_name")
        elif name and contact.get("company") and _full_name_match(name, contact.get("company") or ""):
            score += 75
            reasons.append("contact_name")
        elif (
            name
            and contact.get("company")
            and len(_name_parts(contact.get("company"))) >= 2
            and _norm(contact.get("company")) in _norm(name)
        ):
            score += 75
            reasons.append("contact_name")

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

    listed_codes = set(job_codes(job_blob))
    jn = job.get("job_number") or ""
    if jn:
        listed_codes.update(job_codes(str(jn)))
    mail_codes = set(facts.get("job_codes") or [])
    overlap = listed_codes & mail_codes
    if overlap:
        score += 85
        code = sorted(overlap)[0]
        reasons.append("cf_number" if code.startswith("CF-") else "job_number")

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
    cust_cols = {r[1] for r in _pragma(conn, "customers")}
    if "name" in cust_cols:
        select.append("c.name AS customer_name")
        if "email" in cust_cols:
            select.append("c.email AS customer_email")
        if "address" in cust_cols:
            select.append("c.address AS customer_address")
        if "company" in cust_cols:
            select.append("c.company AS customer_company")
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


def _dedupe_jobs(jobs: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for job in jobs:
        key = str(job.get("id") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(job)
    return out


def _jobs_for_estimate(est: str, jobs: list[dict], quotes: list[dict]) -> list[dict]:
    est_n = _norm(est)
    hits: list[dict] = []
    for job in jobs:
        blob = _norm(_job_blob(job))
        if est_n and (est_n in blob or est_n == _norm(job.get("quote_number") or "")):
            hits.append(job)
    for q in quotes:
        if _norm(q.get("quote_number") or "") != est_n:
            continue
        if q.get("job_id"):
            for job in jobs:
                if str(job.get("id")) == str(q.get("job_id")):
                    hits.append(job)
        elif q.get("customer_id"):
            for job in jobs:
                if job.get("customer_id") == q.get("customer_id"):
                    hits.append(job)
    return _dedupe_jobs(hits)


def _unique_open_job(candidates: list[dict]) -> Optional[dict]:
    open_jobs = [j for j in _dedupe_jobs(candidates) if _is_open(j)]
    if len(open_jobs) == 1:
        return open_jobs[0]
    return None


def _unique_open_for_estimates(facts: dict, jobs: list[dict], quotes: list[dict]) -> Optional[tuple[dict, str]]:
    found: dict[str, dict] = {}
    for est in facts.get("estimate_numbers") or []:
        hit = _unique_open_job(_jobs_for_estimate(est, jobs, quotes))
        if hit:
            found[str(hit.get("id"))] = (hit, est)
    if len(found) == 1:
        job, est = next(iter(found.values()))
        return job, est
    return None


def _jobs_for_code(code: str, jobs: list[dict], quotes: list[dict]) -> list[dict]:
    hits = []
    for job in jobs:
        if code in set(job_codes(_job_blob(job))) | set(job_codes(str(job.get("job_number") or ""))):
            hits.append(job)
    for q in quotes:
        q_codes = set(job_codes(str(q.get("quote_number") or "")))
        if code not in q_codes:
            continue
        if q.get("job_id"):
            for job in jobs:
                if str(job.get("id")) == str(q.get("job_id")):
                    hits.append(job)
        elif q.get("customer_id"):
            for job in jobs:
                if job.get("customer_id") == q.get("customer_id"):
                    hits.append(job)
    return _dedupe_jobs(hits)


def _unique_open_for_codes(facts: dict, jobs: list[dict], quotes: list[dict]) -> Optional[tuple[dict, str]]:
    found: dict[str, dict] = {}
    for code in facts.get("job_codes") or []:
        hit = _unique_open_job(_jobs_for_code(code, jobs, quotes))
        if hit:
            found[str(hit.get("id"))] = (hit, code)
    if len(found) == 1:
        job, code = next(iter(found.values()))
        return job, code
    return None


def _sidemark_targets(mark: str, jobs: list[dict], quotes: list[dict], customers: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    needle = _norm(mark)
    if not needle or len(needle) < 3:
        return [], [], []
    job_hits = [j for j in jobs if needle in _norm(_job_blob(j))]
    quote_hits = [
        q for q in quotes
        if needle in _norm(" ".join(str(q.get(k) or "") for k in (
            "customer_name", "project_name", "notes", "customer_address",
        )))
    ]
    cust_hits = [
        c for c in customers
        if needle in _norm(" ".join(str(c.get(k) or "") for k in (
            "name", "company", "notes", "address",
        )))
    ]
    return job_hits, quote_hits, cust_hits


def _open_jobs_for_customer(jobs: list[dict], customer_id: Any) -> list[dict]:
    if not customer_id:
        return []
    return [j for j in jobs if j.get("customer_id") == customer_id and _is_open(j)]


def _unmatched(name: str, email: str, facts: dict, reason: str, score: int = 0, **extra) -> dict[str, Any]:
    payload = {
        "matched": False,
        "confidence": score,
        "reason": reason,
        "job_id": None,
        "job_title": None,
        "job_number": None,
        "customer_id": extra.get("customer_id"),
        "customer_name": extra.get("customer_name"),
        "from_name": name,
        "from_email": email,
        "facts": facts,
        "sent": False,
    }
    return payload


def _matched(job: dict, name: str, email: str, facts: dict, reason: str, score: int, **extra) -> dict[str, Any]:
    return {
        "matched": True,
        "confidence": score,
        "reason": reason,
        "job_id": job.get("id"),
        "job_title": job.get("title"),
        "job_number": job.get("job_number"),
        "customer_id": job.get("customer_id") or extra.get("customer_id"),
        "customer_name": (
            job.get("client_name") or job.get("customer_name") or extra.get("customer_name")
        ),
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
    jobs = _load_jobs(conn)
    quotes = _load_quotes(conn)
    customers = _load_customers(conn)

    unique_est = _unique_open_for_estimates(facts, jobs, quotes)
    if unique_est:
        job, est = unique_est
        return _matched(job, name, email, facts, f"estimate_open:{est}", ESTIMATE_OPEN_SCORE)

    unique_code = _unique_open_for_codes(facts, jobs, quotes)
    if unique_code:
        job, code = unique_code
        reason = "cf_number" if str(code).startswith("CF-") else "job_number"
        return _matched(job, name, email, facts, f"{reason}:{code}", 90)

    scored: list[tuple[int, str, dict]] = []
    for job in jobs:
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
        for cust in customers:
            cscore = 0
            creason = []
            cust_email = _norm(cust.get("email"))
            cust_domain = _email_domain(cust.get("email"))
            sender_domain = _email_domain(email)
            if email and email == cust_email:
                cscore += 80
                creason.append("customer_email")
            elif (
                sender_domain
                and cust_domain
                and sender_domain == cust_domain
                and sender_domain not in PUBLIC_MAIL_DOMAINS
            ):
                cscore += 70
                creason.append("contact_domain")
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
                open_jobs = _open_jobs_for_customer(jobs, customer_id)
                if len(open_jobs) > 1:
                    return _unmatched(
                        name, email, facts, "ambiguous", best_score,
                        customer_id=customer_id, customer_name=customer_name,
                    )
                if len(open_jobs) == 1:
                    best = open_jobs[0]
                    best_reason = best_reason + ",customer_job"
                elif open_jobs:
                    best = open_jobs[0]
                    best_reason = best_reason + ",customer_job"

    if (not best or best_score < MIN_ATTACH_SCORE or not _has_strong_key(best_reason)) and (
        facts.get("sidemarks") or facts.get("is_supplier_order")
    ):
        for mark in facts.get("sidemarks") or []:
            job_hits, quote_hits, cust_hits = _sidemark_targets(mark, jobs, quotes, customers)
            open_from_jobs = [j for j in job_hits if _is_open(j)]
            if len(open_from_jobs) == 1:
                return _matched(open_from_jobs[0], name, email, facts, "sidemark", 80)
            if len(open_from_jobs) > 1:
                return _unmatched(name, email, facts, "ambiguous", 70)
            quote_jobs = []
            for q in quote_hits:
                if q.get("job_id"):
                    quote_jobs.extend(
                        j for j in jobs if str(j.get("id")) == str(q.get("job_id"))
                    )
                elif q.get("customer_id"):
                    quote_jobs.extend(_open_jobs_for_customer(jobs, q.get("customer_id")))
            unique_q = _unique_open_job(quote_jobs)
            if unique_q:
                return _matched(unique_q, name, email, facts, "sidemark", 80)
            if len(_dedupe_jobs([j for j in quote_jobs if _is_open(j)])) > 1:
                return _unmatched(name, email, facts, "ambiguous", 70)
            if len(cust_hits) == 1:
                cid = cust_hits[0].get("id")
                open_c = _open_jobs_for_customer(jobs, cid)
                if len(open_c) == 1:
                    return _matched(
                        open_c[0], name, email, facts, "sidemark", 80,
                        customer_id=cid, customer_name=cust_hits[0].get("name"),
                    )
                if len(open_c) > 1:
                    return _unmatched(
                        name, email, facts, "ambiguous", 70,
                        customer_id=cid, customer_name=cust_hits[0].get("name"),
                    )
                # Exactly one customer, no open job — keep the customer link.
                return _unmatched(
                    name, email, facts, "sidemark_customer", 60,
                    customer_id=cid, customer_name=cust_hits[0].get("name"),
                )

    if best and _has_strong_key(best_reason) and _only_shared_customer_keys(best_reason):
        open_for = _open_jobs_for_customer(jobs, best.get("customer_id"))
        if len(open_for) > 1:
            return _unmatched(
                name, email, facts, "ambiguous", best_score,
                customer_id=best.get("customer_id"),
                customer_name=best.get("client_name") or best.get("customer_name"),
            )

    has_strong = _has_strong_key(best_reason)
    if best and best_score >= MIN_ATTACH_SCORE and has_strong:
        return _matched(best, name, email, facts, best_reason, best_score,
                       customer_id=customer_id, customer_name=customer_name)
    if best and best_score >= MIN_ATTACH_SCORE and not has_strong:
        return _unmatched(name, email, facts, "name_only", best_score)

    return _unmatched(name, email, facts, best_reason or "none", best_score,
                     customer_id=customer_id, customer_name=customer_name)
