"""Always pick the newest file for a job when Rafael asks for the link.

Root cause (Marley's 2026-10-22): Max generated mockup_marley_s_u_bench_c84dc1c774c6.pdf
at 2:34 PM (black seats) but 'Send me a link' at 9:17 PM reused the older
11:24 AM / Oct 8 file from conversation memory / first find_files match.

This module never reads chat history URLs. It searches the drawings dir +
file index, ranks by mtime, and returns a full studio share URL for the
file just verified on disk. No live sends. Tests use temp dirs only.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

REGISTRY_NAME = ".latest_job_drawings.json"

_SHOW_LINK = re.compile(
    r"(?i)\b(?:"
    r"send\s+me\s+(?:a\s+|the\s+)?link|"
    r"give\s+me\s+(?:a\s+|the\s+)?link|"
    r"show\s+(?:it|me(?:\s+it)?|the\s+(?:drawing|file|pdf|link))|"
    r"done\??|"
    r"(?:the\s+)?(?:studio\s+)?link|"
    r"open\s+(?:it|the\s+(?:drawing|file|pdf))|"
    r"where(?:'s| is)\s+(?:the\s+)?(?:new\s+|revised\s+)?(?:drawing|file|pdf|link)"
    r")\b",
)
_EXTERNAL_SEND = re.compile(r"(?i)\b(?:whatsapp|whats\s+app|email|gmail|text\s+me|sms)\b")
_STUDIO_WORD = re.compile(r"(?i)\b(?:studio|link|enlace|enlace\s+de\s+studio)\b")
_DRAWING_WORDS = re.compile(
    r"(?i)\b(?:drawing|drawings|dibujo|mockup|banquette|bench|layout|pdf)\b",
)


def is_show_link_request(text: str | None) -> bool:
    raw = (text or "").strip()
    if not raw or len(raw) > 240:
        return False
    return bool(_SHOW_LINK.search(raw))


def wants_studio_share(text: str | None) -> bool:
    """Voice/chat 'studio' / 'link' without an explicit WhatsApp/email send."""
    raw = (text or "").strip()
    if not raw:
        return False
    if _EXTERNAL_SEND.search(raw):
        return False
    if is_show_link_request(raw):
        return True
    return bool(_STUDIO_WORD.search(raw) and (
        _DRAWING_WORDS.search(raw) or re.search(r"(?i)\b(?:send|give|show|get|share)\b", raw)
    ))


def wants_external_send(text: str | None) -> bool:
    raw = (text or "").strip()
    if not raw:
        return False
    return bool(_EXTERNAL_SEND.search(raw) and re.search(
        r"(?i)\b(?:send|email|whatsapp|m[aá]nda|env[ií]a)\b", raw,
    ))


def _mtime_of(match: dict[str, Any] | None) -> float:
    if not match:
        return 0.0
    raw = match.get("mtime")
    if isinstance(raw, (int, float)):
        return float(raw)
    path = match.get("abs_path") or match.get("path") or ""
    if path:
        expanded = os.path.expanduser(str(path))
        try:
            return float(os.path.getmtime(expanded))
        except OSError:
            pass
    modified = str(match.get("modified") or "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return time.mktime(time.strptime(modified[:19], fmt))
        except ValueError:
            continue
    return 0.0


def pick_newest_file(matches: list[dict[str, Any]] | None) -> Optional[dict[str, Any]]:
    """Newest mtime wins. Never the first list item / conversation memory."""
    rows = [m for m in (matches or []) if isinstance(m, dict)]
    if not rows:
        return None
    return max(rows, key=_mtime_of)


def _registry_path(drawings_dir: Path) -> Path:
    return drawings_dir / REGISTRY_NAME


def record_generated_drawing(
    *,
    job_key: str,
    path: str,
    extra: dict[str, Any] | None = None,
    drawings_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Remember the file just written so 'send me a link' can verify it."""
    abs_path = os.path.realpath(os.path.expanduser(path))
    try:
        mtime = float(os.path.getmtime(abs_path))
        size = int(os.path.getsize(abs_path))
    except OSError:
        mtime = time.time()
        size = 0
    rec = {
        "job_key": (job_key or "").strip().lower(),
        "path": abs_path,
        "name": os.path.basename(abs_path),
        "mtime": mtime,
        "size": size,
        "recorded_at": time.time(),
        **(extra or {}),
    }
    out_dir = Path(drawings_dir) if drawings_dir else Path(abs_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    store = _registry_path(out_dir)
    data: dict[str, Any] = {}
    if store.exists():
        try:
            data = json.loads(store.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    jobs = dict(data.get("jobs") or {})
    key = rec["job_key"] or "job"
    jobs[key] = rec
    data["jobs"] = jobs
    data["last"] = rec
    store.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        from app.services.max import file_finder as ff
        ff.index_generated_file(abs_path)
    except Exception:
        pass
    return rec


def latest_recorded_drawing(
    job_key: str | None = None,
    drawings_dir: str | Path | None = None,
) -> Optional[dict[str, Any]]:
    dirs: list[Path] = []
    if drawings_dir:
        dirs.append(Path(drawings_dir))
    env = (os.getenv("MAX_DRAWINGS_OUTPUT_DIR") or "").strip()
    if env:
        dirs.append(Path(env))
    try:
        from app.services.drawing.canonical_path import canonical_drawings_dir
        dirs.append(Path(canonical_drawings_dir()))
    except Exception:
        pass
    needle = (job_key or "").strip().lower()
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for d in dirs:
        store = _registry_path(d)
        if not store.exists():
            continue
        try:
            data = json.loads(store.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        jobs = data.get("jobs") or {}
        last = data.get("last")
        candidates = list(jobs.values())
        if last:
            candidates.append(last)
        for rec in candidates:
            if not isinstance(rec, dict):
                continue
            path = rec.get("path")
            if not path or path in seen:
                continue
            if needle and needle not in str(rec.get("job_key") or "") and needle not in str(path).lower():
                continue
            if not os.path.isfile(path):
                continue
            rec = dict(rec)
            rec["mtime"] = float(os.path.getmtime(path))
            rec["abs_path"] = path
            seen.add(path)
            found.append(rec)
    return pick_newest_file(found)


def _scan_drawings_dir(job_key: str | None, drawings_dir: Path) -> list[dict[str, Any]]:
    if not drawings_dir.is_dir():
        return []
    tokens = [t for t in re.split(r"[^a-z0-9]+", (job_key or "").lower()) if len(t) >= 3]
    out: list[dict[str, Any]] = []
    try:
        for name in os.listdir(drawings_dir):
            if not name.lower().endswith(".pdf"):
                continue
            low = name.lower()
            if tokens and not any(t in low for t in tokens):
                continue
            path = drawings_dir / name
            try:
                st = path.stat()
            except OSError:
                continue
            out.append({
                "name": name,
                "path": str(path),
                "abs_path": str(path),
                "mtime": float(st.st_mtime),
                "size": int(st.st_size),
                "source": "drawings_dir",
            })
    except OSError:
        return []
    return out


def find_newest_job_document(
    query: str,
    history: Any = None,
    *,
    drawings_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Newest PDF for this job. Disk + index. Never a URL from chat history."""
    from app.services.max.job_drawing_intent import extract_job_hint, merge_drawing_job_context
    from app.services.max import send_me_link as sml

    ctx = merge_drawing_job_context(query, history)
    job = (ctx.get("job_hint") or extract_job_hint(query) or "").strip()
    search = " ".join(p for p in (job, "drawing mockup") if p).strip() or (query or "drawing")

    matches: list[dict[str, Any]] = []
    recorded = latest_recorded_drawing(job, drawings_dir=drawings_dir)
    if recorded:
        matches.append(recorded)

    dirs: list[Path] = []
    if drawings_dir:
        dirs.append(Path(drawings_dir))
    env = (os.getenv("MAX_DRAWINGS_OUTPUT_DIR") or "").strip()
    if env:
        dirs.append(Path(env))
    try:
        from app.services.drawing.canonical_path import canonical_drawings_dir
        dirs.append(Path(canonical_drawings_dir()))
    except Exception:
        pass
    for d in dirs:
        matches.extend(_scan_drawings_dir(job, d))

    looked = sml.find_latest_document(search, history)
    for m in looked.get("matches") or []:
        if isinstance(m, dict):
            matches.append(m)
    if looked.get("match"):
        matches.append(looked["match"])

    newest = pick_newest_file(matches)
    verified = None
    if newest:
        path = newest.get("abs_path") or newest.get("path")
        if path:
            expanded = os.path.expanduser(str(path))
            if os.path.isfile(expanded):
                verified = {
                    **newest,
                    "abs_path": os.path.realpath(expanded),
                    "path": expanded,
                    "name": os.path.basename(expanded),
                    "mtime": float(os.path.getmtime(expanded)),
                    "verified": True,
                }
    return {
        "query": search,
        "job_hint": job,
        "found": bool(verified),
        "match": verified,
        "matches": matches[:12],
    }


def studio_share_url(path: str) -> str:
    from app.services.max.doc_links import studio_found_url
    return studio_found_url(os.path.expanduser(path)) or ""


def show_link_reply(
    message: str,
    history: Any = None,
    *,
    channel: str = "web",
    drawings_dir: str | Path | None = None,
) -> Optional[dict[str, Any]]:
    """Canned-reply hook: return the newest job drawing's full studio URL."""
    if not is_show_link_request(message) and not wants_studio_share(message):
        return None
    if wants_external_send(message):
        return None
    looked = find_newest_job_document(message, history, drawings_dir=drawings_dir)
    match = looked.get("match")
    if not match:
        return {
            "text": "I don't have a new drawing file for that job yet. Ask me to revise it and I'll generate a fresh PDF.",
            "skill": "latest_job_file",
            "found": False,
        }
    path = match["abs_path"]
    url = studio_share_url(path)
    name = match.get("name") or os.path.basename(path)
    mtime = match.get("mtime") or 0
    when = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)) if mtime else ""
    if url:
        text = f"[{name}]({url})"
        if when:
            text += f" — generated {when} (newest file for this job)."
    else:
        text = f"{name} is on disk ({path}). Studio share host is not configured on this edition."
    return {
        "text": text,
        "skill": "latest_job_file",
        "found": True,
        "path": path,
        "url": url,
        "mtime": mtime,
        "name": name,
        "job_hint": looked.get("job_hint"),
    }
