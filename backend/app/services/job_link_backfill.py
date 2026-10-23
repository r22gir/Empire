"""Propose (and optionally apply) job_id / customer_id links.

Dry-run by default. Matching order:
  1. quote_id (record.quote_id == job.quote_id, or record.id == job.quote_id)
  2. normalized client name or alias
  3. date window around the quote/job dates

Ambiguous name matches (two jobs share a client, e.g. Willard and Le Midi)
are marked ``review``. Apply writes only job_id and customer_id (plus
jobs.metadata.job_folder_slug for folder-to-job rows). Never apply in CI.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

DATE_WINDOW_DAYS = 45
QN_RE = re.compile(r"\b(EST-\d{4}-\d{3,4})\b", re.I)
DROP_WORDS = ("the", "llc", "inc", "studio", "design", "designs", "interiors", "interior")


def in_ci() -> bool:
    return any(os.environ.get(k) for k in ("CI", "GITHUB_ACTIONS", "CONTINUOUS_INTEGRATION"))


def normalize_client(name: str | None) -> str:
    s = (name or "").lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    for w in DROP_WORDS:
        s = re.sub(rf"\b{w}\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_aliases(path: Path | None) -> dict[str, str]:
    """Optional alias file: { "alias": "canonical name", ... }. Never required."""
    if not path or not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    if isinstance(raw, dict):
        items = raw.items()
        # also accept { "canonical": ["alias", ...] }
        for k, v in items:
            if isinstance(v, list):
                canon_n = normalize_client(str(k))
                for alias in v:
                    an = normalize_client(str(alias))
                    if an:
                        out[an] = canon_n
                if canon_n:
                    out[canon_n] = canon_n
            else:
                an = normalize_client(str(k))
                cn = normalize_client(str(v))
                if an and cn:
                    out[an] = cn
    return out


def resolve_name(name: str | None, aliases: dict[str, str]) -> str:
    n = normalize_client(name)
    return aliases.get(n, n)


def parse_when(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "")
    if "T" in text:
        text = text.replace("T", " ")
    text = text[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[: len("2000-01-01 00:00:00") if " " in text else 10], fmt)
        except ValueError:
            continue
    return None


def within_window(a: datetime | None, b: datetime | None, days: int = DATE_WINDOW_DAYS) -> bool:
    if not a or not b:
        return False
    return abs(a - b) <= timedelta(days=days)


@dataclass
class ProposedLink:
    kind: str  # quotes | invoices | job_documents | folder-to-job
    record_id: str
    record_ref: str
    job_id: str
    job_ref: str
    customer_id: str
    match_by: str
    confidence: str  # auto | review
    reason: str
    proposed_job_id: str
    proposed_customer_id: str
    current_job_id: str = ""
    current_customer_id: str = ""


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    try:
        cur = conn.execute(sql, params)
    except sqlite3.Error:
        return []
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone())


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.Error:
        return set()


def _job_when(job: dict) -> datetime | None:
    for key in ("quote_date", "created_at", "updated_at", "intake_date", "scheduled_date"):
        dt = parse_when(job.get(key))
        if dt:
            return dt
    return None


def _record_when(row: dict) -> datetime | None:
    for key in ("created_at", "updated_at", "quote_date", "invoice_date", "due_date"):
        dt = parse_when(row.get(key))
        if dt:
            return dt
    return None


def build_job_indexes(jobs: list[dict], aliases: dict[str, str]) -> dict[str, Any]:
    by_quote_id: dict[str, dict] = {}
    by_name: dict[str, list[dict]] = {}
    by_customer_id: dict[str, list[dict]] = {}
    for job in jobs:
        qid = job.get("quote_id")
        if qid:
            by_quote_id[str(qid)] = job
        name = resolve_name(job.get("client_name") or job.get("customer_name") or job.get("title"), aliases)
        if name:
            by_name.setdefault(name, []).append(job)
        cid = str(job.get("customer_id") or "").strip()
        if cid:
            by_customer_id.setdefault(cid, []).append(job)
        for extra in job.get("client_ids") or []:
            extra_id = str(extra or "").strip()
            if extra_id:
                bucket = by_customer_id.setdefault(extra_id, [])
                if job not in bucket:
                    bucket.append(job)
    return {"by_quote_id": by_quote_id, "by_name": by_name, "by_customer_id": by_customer_id, "jobs": jobs}


def pick_job(record: dict, indexes: dict[str, Any], aliases: dict[str, str], *, record_quote_id: str | None, record_name: str | None) -> tuple[dict | None, str, str, str]:
    """Return (job, match_by, confidence, reason)."""
    if record_quote_id:
        job = indexes["by_quote_id"].get(str(record_quote_id))
        if job:
            return job, "quote_id", "auto", f"quote_id {record_quote_id} matches job.quote_id"

    record_cid = str(record.get("customer_id") or "").strip()
    if record_cid:
        cid_jobs = list(indexes.get("by_customer_id", {}).get(record_cid) or [])
        if len(cid_jobs) > 1:
            refs = ", ".join(str(j.get("job_number") or j.get("id")) for j in cid_jobs[:6])
            return cid_jobs[0], "customer_id_shared", "review", f"shared client {record_cid} maps to {len(cid_jobs)} jobs ({refs})"
        if len(cid_jobs) == 1:
            return cid_jobs[0], "customer_id", "auto", f"unique customer_id {record_cid}"

    name = resolve_name(record_name, aliases)
    if not name:
        return None, "", "", "no quote_id or client name"

    candidates: list[dict] = list(indexes["by_name"].get(name) or [])
    if not candidates:
        return None, "client_name", "", f"no job with client '{name}'"

    if len(candidates) > 1:
        dated = [j for j in candidates if within_window(_record_when(record), _job_when(j))]
        chosen = dated[0] if len(dated) == 1 else candidates[0]
        refs = ", ".join(str(j.get("job_number") or j.get("id")) for j in candidates[:6])
        return chosen, "client_name_ambiguous", "review", f"shared client '{name}' matches {len(candidates)} jobs ({refs})"

    job = candidates[0]
    rec_dt = _record_when(record)
    job_dt = _job_when(job)
    if rec_dt and job_dt and within_window(rec_dt, job_dt):
        return job, "client_name+date", "auto", f"unique client '{name}' within {DATE_WINDOW_DAYS} days"
    if rec_dt and job_dt:
        return job, "client_name", "review", f"unique client '{name}' but dates are outside {DATE_WINDOW_DAYS}-day window"
    return job, "client_name", "review", f"unique client '{name}' but missing dates to confirm"


def propose_links(
    conn: sqlite3.Connection,
    *,
    aliases: dict[str, str] | None = None,
    jobs_dir: Path | None = None,
) -> list[ProposedLink]:
    aliases = aliases or {}
    jobs = []
    if _table_exists(conn, "jobs"):
        jcols = _cols(conn, "jobs")
        want = [c for c in ("id", "job_number", "title", "quote_id", "customer_id", "client_name",
                            "created_at", "updated_at", "quote_date", "intake_date", "scheduled_date", "metadata") if c in jcols]
        jobs = _rows(conn, f"SELECT {', '.join(want or ['id'])} FROM jobs") if want else []
    # customer_name is not always a column
    if jobs and "client_name" not in jobs[0] and "title" in jobs[0]:
        pass
    if jobs and _table_exists(conn, "job_clients"):
        extra: dict[str, list[str]] = {}
        for row in _rows(conn, "SELECT job_id, customer_id FROM job_clients"):
            extra.setdefault(str(row["job_id"]), []).append(str(row["customer_id"]))
        for job in jobs:
            extra_ids = extra.get(str(job.get("id") or ""), [])
            if extra_ids:
                job["client_ids"] = extra_ids
            cid = str(job.get("customer_id") or "").strip()
            if cid and cid not in extra_ids:
                extra_ids = [cid, *extra_ids]
                job["client_ids"] = extra_ids
    indexes = build_job_indexes(jobs, aliases)
    q_by_num: dict[str, dict] = {}
    q_by_id: dict[str, dict] = {}
    if _table_exists(conn, "quotes_v2"):
        qpreload = [c for c in ("id", "quote_number", "job_id", "customer_id", "customer_name", "project_name", "created_at") if c in _cols(conn, "quotes_v2")]
        for q in _rows(conn, f"SELECT {', '.join(qpreload)} FROM quotes_v2"):
            q_by_id[str(q["id"])] = q
            if q.get("quote_number"):
                q_by_num[str(q["quote_number"]).upper()] = q
    indexes["q_by_num"] = q_by_num
    out: list[ProposedLink] = []

    if _table_exists(conn, "quotes_v2"):
        qcols = _cols(conn, "quotes_v2")
        qwant = [c for c in ("id", "quote_number", "job_id", "customer_id", "customer_name", "project_name", "created_at", "updated_at") if c in qcols]
        for q in _rows(conn, f"SELECT {', '.join(qwant)} FROM quotes_v2"):
            if q.get("job_id") and q.get("customer_id"):
                continue
            job, match_by, conf, reason = pick_job(
                q, indexes, aliases, record_quote_id=q.get("id"), record_name=q.get("customer_name") or q.get("project_name")
            )
            # also: jobs that already point at this quote
            if not job:
                job = indexes["by_quote_id"].get(str(q.get("id") or ""))
                if job:
                    match_by, conf, reason = "quote_id", "auto", "job.quote_id points at this quote"
            if not job:
                continue
            out.append(ProposedLink(
                kind="quotes",
                record_id=str(q["id"]),
                record_ref=str(q.get("quote_number") or q["id"]),
                job_id=str(job["id"]),
                job_ref=str(job.get("job_number") or job.get("title") or job["id"]),
                customer_id=str(job.get("customer_id") or q.get("customer_id") or ""),
                match_by=match_by,
                confidence=conf,
                reason=reason,
                proposed_job_id=str(job["id"]),
                proposed_customer_id=str(job.get("customer_id") or ""),
                current_job_id=str(q.get("job_id") or ""),
                current_customer_id=str(q.get("customer_id") or ""),
            ))

    if _table_exists(conn, "invoices"):
        inv_cols = _cols(conn, "invoices")
        iwant = [c for c in ("id", "invoice_number", "job_id", "quote_id", "client_name", "customer_id", "created_at", "updated_at") if c in inv_cols]
        for inv in _rows(conn, f"SELECT {', '.join(iwant)} FROM invoices"):
            if inv.get("job_id"):
                continue
            job, match_by, conf, reason = pick_job(
                inv, indexes, aliases, record_quote_id=inv.get("quote_id"), record_name=inv.get("client_name")
            )
            if not job:
                continue
            out.append(ProposedLink(
                kind="invoices",
                record_id=str(inv["id"]),
                record_ref=str(inv.get("invoice_number") or inv["id"]),
                job_id=str(job["id"]),
                job_ref=str(job.get("job_number") or job.get("title") or job["id"]),
                customer_id=str(job.get("customer_id") or inv.get("customer_id") or ""),
                match_by=match_by,
                confidence=conf,
                reason=reason,
                proposed_job_id=str(job["id"]),
                proposed_customer_id=str(job.get("customer_id") or ""),
                current_job_id=str(inv.get("job_id") or ""),
                current_customer_id=str(inv.get("customer_id") or ""),
            ))

    if _table_exists(conn, "job_documents"):
        dcols = _cols(conn, "job_documents")
        dwant = [c for c in ("id", "job_id", "quote_id", "filename", "url", "document_type", "created_at") if c in dcols]
        for doc in _rows(conn, f"SELECT {', '.join(dwant)} FROM job_documents"):
            if doc.get("job_id"):
                continue
            qid = doc.get("quote_id")
            qn = None
            if not qid and doc.get("filename"):
                m = QN_RE.search(str(doc.get("filename") or "") + " " + str(doc.get("url") or ""))
                if m:
                    qn = m.group(1).upper()
                    qrow = q_by_num.get(qn)
                    if qrow:
                        qid = qrow.get("id")
            qrow = q_by_id.get(str(qid)) if qid else None
            job, match_by, conf, reason = pick_job(
                doc, indexes, aliases,
                record_quote_id=str(qid) if qid else None,
                record_name=(qrow or {}).get("customer_name") or (qrow or {}).get("project_name"),
            )
            if job and qn and match_by == "quote_id":
                reason = f"filename {qn} → quote {qid}"
            if not job:
                continue
            out.append(ProposedLink(
                kind="job_documents",
                record_id=str(doc["id"]),
                record_ref=str(doc.get("filename") or doc["id"]),
                job_id=str(job["id"]),
                job_ref=str(job.get("job_number") or job.get("title") or job["id"]),
                customer_id=str(job.get("customer_id") or ""),
                match_by=match_by or "quote_id",
                confidence=conf or "auto",
                reason=reason or "document quote_id matches job",
                proposed_job_id=str(job["id"]),
                proposed_customer_id=str(job.get("customer_id") or ""),
                current_job_id=str(doc.get("job_id") or ""),
            ))

    jobs_root = Path(jobs_dir) if jobs_dir else Path(os.getenv("EMPIRE_JOBS_DIR") or (Path.home() / "jobs"))
    if jobs_root.is_dir():
        for entry in sorted(jobs_root.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            slug = entry.name
            folder_qns: set[str] = set()
            for qid_file in ("quote_id.txt", "p1/quote_id.txt", "p2/quote_id.txt", "max/quote_id.txt"):
                p = entry / qid_file
                if p.is_file():
                    try:
                        text = p.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        text = ""
                    m = QN_RE.search(text)
                    if m:
                        folder_qns.add(m.group(1).upper())
            try:
                for dirpath, dirnames, filenames in os.walk(entry):
                    dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                    if Path(dirpath).relative_to(entry).parts[:1] and len(Path(dirpath).relative_to(entry).parts) > 3:
                        dirnames[:] = []
                        continue
                    for fn in filenames:
                        m = QN_RE.search(fn)
                        if m:
                            folder_qns.add(m.group(1).upper())
            except OSError:
                pass

            job = None
            match_by = conf = reason = ""
            for qn in sorted(folder_qns):
                qrow = q_by_num.get(qn)
                if not qrow:
                    continue
                job, match_by, conf, reason = pick_job(
                    {"created_at": None}, indexes, aliases,
                    record_quote_id=str(qrow.get("id")),
                    record_name=qrow.get("customer_name") or qrow.get("project_name"),
                )
                if job and match_by == "quote_id":
                    reason = f"folder quote {qn}"
                    break
                if job:
                    reason = f"folder quote {qn}: {reason}"
                    break
            if not job:
                job, match_by, conf, reason = pick_job(
                    {"created_at": None, "client_name": slug.replace("-", " ")},
                    indexes, aliases, record_quote_id=None, record_name=slug.replace("-", " "),
                )
                if job:
                    match_by = match_by or "folder_slug"
            if not job:
                continue
            out.append(ProposedLink(
                kind="folder-to-job",
                record_id=slug,
                record_ref=f"~/jobs/{slug}",
                job_id=str(job["id"]),
                job_ref=str(job.get("job_number") or job.get("title") or job["id"]),
                customer_id=str(job.get("customer_id") or ""),
                match_by=match_by or "folder_slug",
                confidence=conf or "review",
                reason=reason or f"folder slug {slug}",
                proposed_job_id=str(job["id"]),
                proposed_customer_id=str(job.get("customer_id") or ""),
            ))

    # Client on more than one job: never auto-link by client match.
    by_cid = indexes.get("by_customer_id") or {}
    for row in out:
        if row.match_by == "quote_id":
            continue
        cid = str(row.current_customer_id or row.proposed_customer_id or row.customer_id or "").strip()
        mapped = by_cid.get(cid) or []
        if cid and len(mapped) > 1:
            row.confidence = "review"
            if "shared client" not in row.reason.lower():
                refs = ", ".join(str(j.get("job_number") or j.get("id")) for j in mapped[:6])
                row.reason = f"shared client {cid} maps to {len(mapped)} jobs ({refs}); {row.reason}"
            if "shared" not in row.match_by:
                row.match_by = f"{row.match_by or 'customer_id'}_shared"

    return out


def write_csv(rows: Iterable[ProposedLink], dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "kind", "record_id", "record_ref", "job_id", "job_ref", "customer_id",
        "match_by", "confidence", "reason", "proposed_job_id", "proposed_customer_id",
        "current_job_id", "current_customer_id",
    ]
    with dest.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(asdict(row))
    return dest


def backup_db(db_path: Path) -> Path:
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    dest = db_path.with_name(db_path.name + f".bak-{stamp}")
    src = sqlite3.connect(str(db_path))
    try:
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    if not dest.is_file() or dest.stat().st_size == 0:
        shutil.copy2(db_path, dest)
    return dest


def apply_links(conn: sqlite3.Connection, rows: list[ProposedLink], *, only_auto: bool = True) -> dict[str, int]:
    """Write only job_id and customer_id (and job folder slug in metadata)."""
    counts = {"quotes": 0, "invoices": 0, "job_documents": 0, "folder-to-job": 0, "skipped_review": 0}
    q_cols = _cols(conn, "quotes_v2") if _table_exists(conn, "quotes_v2") else set()
    i_cols = _cols(conn, "invoices") if _table_exists(conn, "invoices") else set()
    for row in rows:
        if only_auto and row.confidence != "auto":
            counts["skipped_review"] += 1
            continue
        if row.kind == "quotes" and _table_exists(conn, "quotes_v2"):
            sets = ["job_id = ?"]
            params: list[Any] = [row.proposed_job_id]
            if "customer_id" in q_cols and row.proposed_customer_id:
                sets.append("customer_id = ?")
                params.append(row.proposed_customer_id)
            params.append(row.record_id)
            conn.execute(f"UPDATE quotes_v2 SET {', '.join(sets)} WHERE id = ?", params)
            counts["quotes"] += 1
        elif row.kind == "invoices" and _table_exists(conn, "invoices"):
            sets = ["job_id = ?"]
            params = [row.proposed_job_id]
            if "customer_id" in i_cols and row.proposed_customer_id:
                sets.append("customer_id = ?")
                params.append(row.proposed_customer_id)
            params.append(row.record_id)
            conn.execute(f"UPDATE invoices SET {', '.join(sets)} WHERE id = ?", params)
            counts["invoices"] += 1
        elif row.kind == "job_documents" and _table_exists(conn, "job_documents"):
            conn.execute("UPDATE job_documents SET job_id = ? WHERE id = ?", (row.proposed_job_id, row.record_id))
            counts["job_documents"] += 1
        elif row.kind == "folder-to-job" and _table_exists(conn, "jobs"):
            existing = conn.execute("SELECT metadata FROM jobs WHERE id = ?", (row.proposed_job_id,)).fetchone()
            meta: dict[str, Any] = {}
            if existing and existing[0]:
                try:
                    parsed = json.loads(existing[0]) if isinstance(existing[0], str) else existing[0]
                    if isinstance(parsed, dict):
                        meta = parsed
                except (json.JSONDecodeError, TypeError):
                    meta = {}
            meta["job_folder_slug"] = row.record_id
            conn.execute("UPDATE jobs SET metadata = ? WHERE id = ?", (json.dumps(meta), row.proposed_job_id))
            counts["folder-to-job"] += 1
    return counts
