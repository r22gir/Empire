"""Gather every quote, invoice, document, photo, drawing, and folder file for one job.

Used by GET /jobs/{id}/related. Matching is read-only: job id, quote ids,
customer id, and the job's folder slug (jobs.metadata.job_folder_slug).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

from app.db.database import dict_row

QUOTE_PDF = "/api/v1/quotes-v2/{id}/pdf"
INVOICE_PDF = "/api/v1/finance/invoices/{id}/pdf"
IMG_RE = re.compile(r"\.(png|jpe?g|webp|gif)$", re.I)
PDF_RE = re.compile(r"\.pdf$", re.I)
QN_RE = re.compile(r"\b(EST-\d{4}-\d{3,4})\b", re.I)


def parse_json(value: Any, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", "replace")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default
    return default


def job_folder_slug(job: dict) -> str | None:
    meta = parse_json(job.get("metadata"), {}) or {}
    if not isinstance(meta, dict):
        return None
    for key in ("job_folder_slug", "folder_slug", "jobs_folder"):
        raw = meta.get(key)
        if raw:
            slug = str(raw).strip().strip("/")
            if slug and ".." not in slug and "/" not in slug:
                return slug
    return None


def visual_items(value: Any) -> list[dict]:
    """Normalize photos / drawings / mockups JSON into {url, filename, title}."""
    parsed = parse_json(value, value)
    if parsed is None:
        return []
    if isinstance(parsed, str):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return []
    out: list[dict] = []
    for i, item in enumerate(parsed):
        if item is None:
            continue
        if isinstance(item, str):
            url = item.strip()
            if not url:
                continue
            name = Path(url.split("?", 1)[0]).name or f"file-{i + 1}"
            out.append({"url": url, "filename": name, "title": name})
            continue
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("src") or item.get("path") or item.get("serverUrl") or "").strip()
        if not url:
            continue
        name = str(item.get("filename") or item.get("original_name") or item.get("name") or Path(url.split("?", 1)[0]).name or f"file-{i + 1}")
        title = str(item.get("title") or item.get("item_name") or name)
        out.append({**item, "url": url, "filename": name, "title": title})
    return out


def normalize_photo_src(url: str) -> str:
    src = str(url or "")
    m = re.match(r"^/api/v1/photos/(?!serve/)([\w-]+)/([\w-]+)/([\w.-]+)$", src)
    if m:
        return f"/api/v1/photos/serve/{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return src


def viewer_for(url: str, title: str, kind: str | None = None) -> dict:
    src = normalize_photo_src(url)
    guessed = "image" if IMG_RE.search(src) else "pdf"
    return {"src": src, "title": title, "kind": kind or guessed}


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _cols(conn, table: str) -> set[str]:
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _safe_rows(conn, sql: str, params: tuple = ()) -> list[dict]:
    try:
        return [dict_row(r) for r in conn.execute(sql, params).fetchall()]
    except Exception:
        return []


def quote_ids_for_job(conn, job: dict) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()

    def add(raw: Any) -> None:
        if raw is None or raw == "":
            return
        key = str(raw)
        if key in seen:
            return
        seen.add(key)
        ids.append(key)

    add(job.get("quote_id"))
    if _table_exists(conn, "quotes_v2"):
        for row in _safe_rows(conn, "SELECT id FROM quotes_v2 WHERE job_id = ?", (job["id"],)):
            add(row.get("id"))
        meta = parse_json(job.get("metadata"), {}) or {}
        if isinstance(meta, dict):
            add(meta.get("quote_id"))
            for extra in meta.get("quote_ids") or []:
                add(extra)
    return ids


def _in_clause(ids: Iterable[str]) -> tuple[str, list[str]]:
    vals = [str(i) for i in ids if i]
    if not vals:
        return "", []
    return ",".join("?" * len(vals)), vals


def _scan_folder(folder: Path, *, limit: int = 80) -> list[dict]:
    if not folder.is_dir():
        return []
    files: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("__pycache__", "node_modules", "src")]
        rel_dir = Path(dirpath).relative_to(folder)
        depth = len(rel_dir.parts) if str(rel_dir) != "." else 0
        if depth > 3:
            dirnames[:] = []
            continue
        for name in filenames:
            if name.startswith("."):
                continue
            if not (PDF_RE.search(name) or IMG_RE.search(name)):
                continue
            if re.search(r"-page-\d+\.png$", name, re.I):
                continue
            abs_path = Path(dirpath) / name
            rel = str(abs_path.relative_to(folder))
            kind = "photo" if IMG_RE.search(name) else (
                "drawing" if re.search(r"drawing|shop|elevation|ripplefold", rel, re.I) else
                "invoice" if re.search(r"invoice|INV-\d{4}", name, re.I) else
                "estimate" if QN_RE.search(name) or re.search(r"estimate|quote", name, re.I) else
                "other"
            )
            url = f"/api/v1/files/found?path={rel}"  # placeholder; viewer uses folder src below
            files.append({
                "filename": name,
                "title": name,
                "document_type": kind,
                "url": None,
                "folder_rel": rel,
                "location": str(abs_path),
                "source": f"job folder {folder.name}",
                "viewer": None,
            })
            if len(files) >= limit:
                return files
    return files


def gather_related(conn, job_id: str, *, jobs_dir: Path | None = None, data_dir: Path | None = None) -> dict | None:
    """Return the related payload or None if the job does not exist."""
    if not _table_exists(conn, "jobs"):
        return None
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        row = conn.execute("SELECT * FROM jobs WHERE job_number = ?", (job_id,)).fetchone() if "job_number" in _cols(conn, "jobs") else None
    if not row:
        return None
    job = dict_row(row)
    job["metadata"] = parse_json(job.get("metadata"), {}) or {}
    qids = quote_ids_for_job(conn, job)
    customer_id = job.get("customer_id")
    slug = job_folder_slug(job)

    quotes: list[dict] = []
    if _table_exists(conn, "quotes_v2"):
        seen_q: set[str] = set()
        clauses = ["job_id = ?"]
        params: list[Any] = [job["id"]]
        if qids:
            ph, vals = _in_clause(qids)
            clauses.append(f"id IN ({ph})")
            params.extend(vals)
        if customer_id:
            clauses.append("customer_id = ?")
            params.append(customer_id)
        for q in _safe_rows(conn, f"SELECT * FROM quotes_v2 WHERE {' OR '.join(clauses)} ORDER BY created_at DESC", tuple(params)):
            qid = str(q.get("id") or "")
            if not qid or qid in seen_q:
                continue
            seen_q.add(qid)
            title = q.get("quote_number") or "Estimate"
            quotes.append({
                **{k: q.get(k) for k in ("id", "quote_number", "project_name", "customer_name", "status", "total", "job_id", "customer_id", "created_at")},
                "viewer_url": QUOTE_PDF.format(id=qid),
                "viewer": viewer_for(QUOTE_PDF.format(id=qid), str(title), "pdf"),
            })

    invoices: list[dict] = []
    if _table_exists(conn, "invoices"):
        seen_i: set[str] = set()
        clauses = ["job_id = ?"]
        params = [job["id"]]
        if qids:
            ph, vals = _in_clause(qids)
            clauses.append(f"quote_id IN ({ph})")
            params.extend(vals)
        if customer_id:
            inv_cols = _cols(conn, "invoices")
            if "customer_id" in inv_cols:
                clauses.append("customer_id = ?")
                params.append(customer_id)
        for inv in _safe_rows(conn, f"SELECT * FROM invoices WHERE {' OR '.join(clauses)} ORDER BY created_at DESC", tuple(params)):
            iid = str(inv.get("id") or "")
            if not iid or iid in seen_i:
                continue
            seen_i.add(iid)
            title = inv.get("invoice_number") or "Invoice"
            invoices.append({
                **{k: inv.get(k) for k in ("id", "invoice_number", "status", "total", "balance_due", "amount_paid", "job_id", "quote_id", "customer_id", "client_name", "created_at")},
                "viewer_url": INVOICE_PDF.format(id=iid),
                "viewer": viewer_for(INVOICE_PDF.format(id=iid), str(title), "pdf"),
            })

    documents: list[dict] = []
    if _table_exists(conn, "job_documents"):
        seen_d: set[str] = set()
        clauses = ["job_id = ?"]
        params = [job["id"]]
        if qids:
            ph, vals = _in_clause(qids)
            clauses.append(f"quote_id IN ({ph})")
            params.extend(vals)
        for doc in _safe_rows(conn, f"SELECT * FROM job_documents WHERE {' OR '.join(clauses)} ORDER BY created_at DESC", tuple(params)):
            did = str(doc.get("id") or "")
            if did and did in seen_d:
                continue
            if did:
                seen_d.add(did)
            url = normalize_photo_src(str(doc.get("url") or ""))
            title = doc.get("filename") or doc.get("title") or "File"
            kind = "image" if IMG_RE.search(str(doc.get("filename") or url)) or doc.get("document_type") == "photo" else "pdf"
            documents.append({
                **doc,
                "url": url or doc.get("url"),
                "viewer": viewer_for(url, str(title), kind) if url else None,
            })

    photos = []
    for item in visual_items(job.get("photos")):
        src = normalize_photo_src(item["url"])
        photos.append({**item, "url": src, "source": "job.photos", "document_type": "photo", "viewer": viewer_for(src, item["title"], "image")})
    drawings = []
    for item in visual_items(job.get("drawings")):
        src = normalize_photo_src(item["url"])
        drawings.append({**item, "url": src, "source": "job.drawings", "document_type": "drawing", "viewer": viewer_for(src, item["title"])})
    mockups = []
    for item in visual_items(job.get("mockups")):
        src = normalize_photo_src(item["url"])
        mockups.append({**item, "url": src, "source": "job.mockups", "document_type": "drawing", "viewer": viewer_for(src, item["title"])})

    if _table_exists(conn, "drawing_versions"):
        clauses = ["job_id = ?"]
        params = [job["id"]]
        if qids:
            ph, vals = _in_clause(qids)
            clauses.append(f"quote_id IN ({ph})")
            params.extend(vals)
        for dv in _safe_rows(conn, f"SELECT * FROM drawing_versions WHERE {' OR '.join(clauses)}", tuple(params)):
            path = dv.get("file_path")
            name = Path(str(path)).name if path else (dv.get("item_name") or "drawing")
            url = f"/api/v1/drawings/files/{name}" if name else None
            if url:
                drawings.append({
                    "id": dv.get("id"),
                    "url": url,
                    "filename": name,
                    "title": dv.get("item_name") or name,
                    "source": "drawing_versions",
                    "document_type": "drawing",
                    "viewer": viewer_for(url, str(dv.get("item_name") or name), "pdf"),
                })

    folder_files: list[dict] = []
    jobs_root = Path(jobs_dir) if jobs_dir else Path(os.getenv("EMPIRE_JOBS_DIR") or (Path.home() / "jobs"))
    data_root = Path(data_dir) if data_dir else Path(os.getenv("EMPIRE_DATA_DIR") or (Path.home() / "empire-data"))
    if slug:
        folder_files = _scan_folder(jobs_root / slug)
    qnums = {str(q.get("quote_number") or "").upper() for q in quotes if q.get("quote_number")}
    for extra in (data_root / "drawings", data_root / "documents"):
        if not extra.is_dir():
            continue
        try:
            names = list(extra.iterdir())
        except OSError:
            continue
        for f in names:
            if not f.is_file():
                continue
            if not (PDF_RE.search(f.name) or IMG_RE.search(f.name)):
                continue
            hit = QN_RE.search(f.name)
            if hit and hit.group(1).upper() in qnums:
                url = f"/api/v1/drawings/files/{f.name}" if extra.name == "drawings" else None
                folder_files.append({
                    "filename": f.name,
                    "title": f.name,
                    "document_type": "drawing" if extra.name == "drawings" else "other",
                    "url": url,
                    "source": f"~/empire-data/{extra.name}",
                    "viewer": viewer_for(url, f.name) if url else None,
                })

    tasks: list[dict] = []
    if _table_exists(conn, "organizer_items"):
        tasks.extend(_safe_rows(conn, "SELECT * FROM organizer_items WHERE job_id = ? ORDER BY created_at DESC", (job["id"],)))
    if _table_exists(conn, "tasks") and "metadata" in _cols(conn, "tasks"):
        for t in _safe_rows(conn, "SELECT * FROM tasks"):
            meta = parse_json(t.get("metadata"), {}) or {}
            if isinstance(meta, dict) and str(meta.get("job_id") or "") == str(job["id"]):
                tasks.append(t)

    groups: list[dict] = []
    for q in quotes:
        groups.append({"type": "estimate", "title": q.get("quote_number") or "Estimate", "final": q["viewer"], "older": [], "source": "quotes_v2"})
    for inv in invoices:
        groups.append({"type": "invoice", "title": inv.get("invoice_number") or "Invoice", "final": inv["viewer"], "older": [], "source": "invoices"})
    for d in drawings + mockups:
        if d.get("viewer"):
            groups.append({"type": "drawing", "title": d.get("title") or d.get("filename"), "final": d["viewer"], "older": [], "source": d.get("source")})
    for p in photos:
        if p.get("viewer"):
            groups.append({"type": "photo", "title": p.get("title") or p.get("filename"), "final": p["viewer"], "older": [], "source": p.get("source")})
    for doc in documents:
        if not doc.get("viewer"):
            continue
        dtype = doc.get("document_type") or "other"
        if dtype in ("photo", "drawing", "estimate", "invoice"):
            continue  # already represented above when they have typed urls; still include untyped
        groups.append({"type": dtype if dtype in ("estimate", "presentation", "invoice", "drawing", "photo") else "other", "title": doc.get("filename") or "File", "final": doc["viewer"], "older": [], "source": "job_documents"})

    # job_documents that are photos/drawings/estimates should still appear if not already in JSON
    existing_urls = {g["final"]["src"] for g in groups if g.get("final") and g["final"].get("src")}
    for doc in documents:
        viewer = doc.get("viewer")
        if not viewer or viewer.get("src") in existing_urls:
            continue
        dtype = doc.get("document_type") or "other"
        mapped = dtype if dtype in ("estimate", "presentation", "invoice", "drawing", "photo") else "other"
        groups.append({"type": mapped, "title": doc.get("filename") or "File", "final": viewer, "older": [], "source": "job_documents"})
        existing_urls.add(viewer.get("src"))

    primary = next((g["final"] for g in groups if g["type"] == "drawing"), None) \
        or next((g["final"] for g in groups if g["type"] == "estimate"), None) \
        or next((g["final"] for g in groups if g.get("final")), None)

    return {
        "job_id": job["id"],
        "job_number": job.get("job_number"),
        "quote_id": job.get("quote_id"),
        "quote_ids": qids,
        "customer_id": customer_id,
        "job_folder_slug": slug,
        "quotes": quotes,
        "invoices": invoices,
        "documents": documents,
        "photos": photos,
        "drawings": drawings,
        "mockups": mockups,
        "folder_files": folder_files,
        "tasks": [{"id": t.get("id"), "title": t.get("title"), "status": t.get("status") or t.get("kind"), "due_at": t.get("due_at") or t.get("due_date")} for t in tasks],
        "groups": groups,
        "viewer_links": {
            "primary": primary,
            "primary_drawing": next((g["final"] for g in groups if g["type"] == "drawing"), None),
            "primary_estimate": next((g["final"] for g in groups if g["type"] == "estimate"), None),
            "primary_photo": next((g["final"] for g in groups if g["type"] == "photo"), None),
            "primary_invoice": next((g["final"] for g in groups if g["type"] == "invoice"), None),
        },
    }
