"""Hermes Knowledge Artifact Layer (v10).

Durable artifact persistence for MAX/Hermes/OpenClaw outputs.

Truth boundary:
runtime > repo_truth > database_truth > module_docs > approved_artifacts > session_context > model_opinion
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from app.services.max.hermes_memory import memory_root


TRUTH_HIERARCHY = (
    "runtime",
    "repo_truth",
    "database_truth",
    "module_docs",
    "approved_artifacts",
    "session_context",
    "model_opinion",
)

APPROVAL_STATES = {
    "draft",
    "approved",
    "rejected",
    "changes_requested",
    "superseded",
}

SOURCE_AGENTS = {"max", "hermes", "openclaw", "founder"}

DEFAULT_MODULE_SLUGS = {
    "workroom",
    "woodcraft",
    "archiveforge",
    "marketforge",
    "relistapp",
    "drawing-studio",
    "vendorops",
    "socialforge",
    "apostapp",
    "crm",
    "ai-model-control",
    "system",
}

MODULE_ALIASES = {
    "archiveforge": "archiveforge",
    "archive forge": "archiveforge",
    "marketforge": "marketforge",
    "market forge": "marketforge",
    "workroom": "workroom",
    "woodcraft": "woodcraft",
    "relistapp": "relistapp",
    "relist app": "relistapp",
    "drawing-studio": "drawing-studio",
    "drawing studio": "drawing-studio",
    "vendorops": "vendorops",
    "vendor ops": "vendorops",
    "socialforge": "socialforge",
    "social forge": "socialforge",
    "apostapp": "apostapp",
    "crm": "crm",
    "ai-model-control": "ai-model-control",
    "ai model control": "ai-model-control",
    "system": "system",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return ""


def _lane() -> str:
    return os.getenv("EMPIRE_LANE", "v10-test").strip() or "v10-test"


def _branch() -> str:
    value = _git(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return value or "unknown"


def _commit() -> str:
    value = _git(["git", "rev-parse", "--short", "HEAD"])
    return value or "unknown"


def artifacts_root() -> Path:
    return memory_root() / "ARTIFACTS"


def _index_path() -> Path:
    return artifacts_root() / "index.jsonl"


def _normalize_module(module: str | None) -> str:
    if not module:
        return "system"
    raw = module.strip().lower()
    if raw in MODULE_ALIASES:
        return MODULE_ALIASES[raw]
    slug = re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")
    if not slug:
        return "system"
    return slug


def _normalize_source_agent(source_agent: str | None) -> str:
    value = (source_agent or "max").strip().lower()
    return value if value in SOURCE_AGENTS else "max"


def _sha256_short(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def ensure_hermes_artifact_scaffold() -> dict[str, Any]:
    root = artifacts_root()
    created: list[str] = []
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
        created.append(str(root))
    for name in ("max", "hermes", "openclaw", "modules"):
        path = root / name
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))
    for slug in sorted(DEFAULT_MODULE_SLUGS):
        path = root / "modules" / slug
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))
    idx = _index_path()
    if not idx.exists():
        idx.write_text("", encoding="utf-8")
        created.append(str(idx))
    return {
        "root": str(root),
        "index_path": str(idx),
        "created": created,
        "lane": _lane(),
        "branch": _branch(),
        "commit": _commit(),
        "truth_hierarchy": list(TRUTH_HIERARCHY),
    }


def _append_index(event: str, payload: dict[str, Any]) -> None:
    ensure_hermes_artifact_scaffold()
    row = {
        "timestamp": _now_iso(),
        "event": event,
        "lane": _lane(),
        "branch": _branch(),
        "commit": _commit(),
        "payload": payload,
    }
    with _index_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _contains_external_url(value: str) -> bool:
    test = value.strip().lower()
    return (
        test.startswith("http://")
        or test.startswith("https://")
        or test.startswith("ftp://")
        or test.startswith("//")
        or test.startswith("data:")
        or test.startswith("javascript:")
    )


def sanitize_html_artifact(html_content: str) -> dict[str, Any]:
    soup = BeautifulSoup(html_content or "", "html.parser")

    removed = {
        "script": 0,
        "link": 0,
        "iframe": 0,
        "form": 0,
        "object": 0,
        "embed": 0,
        "meta_refresh": 0,
        "event_attrs": 0,
        "external_attrs": 0,
    }

    for tag_name in ("script", "link", "iframe", "form", "object", "embed"):
        for tag in list(soup.find_all(tag_name)):
            removed[tag_name] += 1
            tag.decompose()

    for meta in list(soup.find_all("meta")):
        http_equiv = (meta.get("http-equiv") or "").strip().lower()
        if http_equiv == "refresh":
            removed["meta_refresh"] += 1
            meta.decompose()

    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            attr_l = attr.lower()
            value = tag.attrs.get(attr)
            rendered = " ".join(value) if isinstance(value, list) else str(value)
            if attr_l.startswith("on"):
                removed["event_attrs"] += 1
                del tag.attrs[attr]
                continue
            if attr_l in {"href", "src", "action", "xlink:href"} and _contains_external_url(rendered):
                removed["external_attrs"] += 1
                del tag.attrs[attr]

    cleaned_html = str(soup)
    text = soup.get_text("\n", strip=True)
    headings = []
    for name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        for node in soup.find_all(name):
            label = node.get_text(" ", strip=True)
            if label:
                headings.append({"level": name, "text": label})

    changed = any(value > 0 for value in removed.values())
    safety_status = "sanitized_no_scripts_no_external_network"
    return {
        "cleaned_html": cleaned_html,
        "extracted_text": text,
        "headings": headings,
        "safety_status": safety_status,
        "had_dangerous_content": changed,
        "removed_counts": removed,
    }


def _text_to_html(title: str, content: str) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head><body>"
        f"<article><h1>{html.escape(title or 'Artifact')}</h1>"
        f"<pre>{html.escape(content or '')}</pre></article>"
        "</body></html>"
    )


def _artifact_dir(source_agent: str, module_slug: str, artifact_id: str) -> Path:
    root = artifacts_root()
    if module_slug in DEFAULT_MODULE_SLUGS:
        return root / "modules" / module_slug / artifact_id
    return root / source_agent / artifact_id


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _summary_from_text(text: str) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= 420:
        return compact
    return compact[:417].rstrip() + "..."


def _artifact_files(base: Path) -> dict[str, Path]:
    return {
        "metadata": base / "metadata.json",
        "html": base / "artifact.html",
        "text": base / "extracted.txt",
        "summary": base / "summary.txt",
        "provenance": base / "provenance.json",
    }


def _all_metadata() -> list[dict[str, Any]]:
    ensure_hermes_artifact_scaffold()
    rows: list[dict[str, Any]] = []
    for meta_path in artifacts_root().rglob("metadata.json"):
        record = _read_json(meta_path)
        if not record:
            continue
        record["_meta_path"] = str(meta_path)
        rows.append(record)
    rows.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return rows


def _find_metadata(artifact_id: str) -> dict[str, Any] | None:
    for row in _all_metadata():
        if row.get("id") == artifact_id:
            return row
    return None


def hermes_artifact_write(
    *,
    title: str,
    artifact_type: str,
    content: str,
    content_format: str = "html",
    module: str | None = None,
    source_agent: str = "max",
    approval_status: str = "draft",
    tags: list[str] | None = None,
    retrieval_keywords: list[str] | None = None,
    supersedes: list[str] | None = None,
    source_prompt: str | None = None,
    source_prompt_hash: str | None = None,
    source_files: list[str] | None = None,
    source_endpoints: list[str] | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_hermes_artifact_scaffold()

    artifact_id = f"ha_{uuid.uuid4().hex[:20]}"
    now = _now_iso()
    lane = _lane()
    branch = _branch()
    commit = _commit()
    module_slug = _normalize_module(module)
    source = _normalize_source_agent(source_agent)
    status = approval_status if approval_status in APPROVAL_STATES else "draft"

    raw_html = content or ""
    if content_format != "html":
        raw_html = _text_to_html(title=title, content=content)

    sanitized = sanitize_html_artifact(raw_html)
    summary = _summary_from_text(sanitized["extracted_text"])
    keywords = sorted(
        set(
            [k.strip().lower() for k in (retrieval_keywords or []) if k and k.strip()]
            + [module_slug, source, (artifact_type or "").lower()]
        )
    )
    normalized_tags = sorted(set([t.strip().lower() for t in (tags or []) if t and t.strip()]))
    prompt_hash = source_prompt_hash or _sha256_short(source_prompt)
    supersedes_list = list(dict.fromkeys(supersedes or []))

    base = _artifact_dir(source_agent=source, module_slug=module_slug, artifact_id=artifact_id)
    base.mkdir(parents=True, exist_ok=True)
    files = _artifact_files(base)

    provenance_payload = provenance or {}
    provenance_payload.setdefault("source_agent", source)
    provenance_payload.setdefault("source_prompt_hash", prompt_hash)
    provenance_payload.setdefault("source_files", source_files or [])
    provenance_payload.setdefault("source_endpoints", source_endpoints or [])
    provenance_payload.setdefault("truth_hierarchy", list(TRUTH_HIERARCHY))

    metadata = {
        "id": artifact_id,
        "title": title,
        "artifact_type": artifact_type,
        "content_format": content_format,
        "module": module_slug,
        "source_agent": source,
        "created_at": now,
        "updated_at": now,
        "lane": lane,
        "branch": branch,
        "commit": commit,
        "approval_status": status,
        "safety_status": sanitized["safety_status"],
        "provenance": provenance_payload,
        "supersedes": supersedes_list,
        "superseded_by": None,
        "tags": normalized_tags,
        "retrieval_keywords": keywords,
        "source_prompt_hash": prompt_hash,
        "source_files": source_files or [],
        "source_endpoints": source_endpoints or [],
        "headings": sanitized["headings"],
        "had_dangerous_content": sanitized["had_dangerous_content"],
        "removed_counts": sanitized["removed_counts"],
        "paths": {
            "artifact_dir": str(base),
            "artifact_html": str(files["html"]),
            "metadata_json": str(files["metadata"]),
            "extracted_text": str(files["text"]),
            "summary_text": str(files["summary"]),
            "provenance_json": str(files["provenance"]),
        },
    }

    files["html"].write_text(sanitized["cleaned_html"], encoding="utf-8")
    files["text"].write_text(sanitized["extracted_text"], encoding="utf-8")
    files["summary"].write_text(summary, encoding="utf-8")
    _write_json(files["provenance"], provenance_payload)
    _write_json(files["metadata"], metadata)

    _append_index(
        "artifact_write",
        {
            "id": artifact_id,
            "module": module_slug,
            "source_agent": source,
            "approval_status": status,
            "metadata_path": str(files["metadata"]),
        },
    )
    return {
        "artifact_id": artifact_id,
        "metadata": metadata,
        "summary": summary,
        "artifact_path": str(files["html"]),
        "truth_boundary": "supporting_only_beneath_runtime_repo_database_and_module_docs",
    }


def hermes_artifact_get(artifact_id: str) -> dict[str, Any] | None:
    record = _find_metadata(artifact_id)
    if not record:
        return None
    meta_path = Path(record["_meta_path"])
    base = meta_path.parent
    files = _artifact_files(base)
    summary = files["summary"].read_text(encoding="utf-8") if files["summary"].exists() else ""
    extracted = files["text"].read_text(encoding="utf-8") if files["text"].exists() else ""
    provenance = _read_json(files["provenance"]) or record.get("provenance") or {}
    warning = None
    if record.get("approval_status") == "superseded" or record.get("superseded_by"):
        warning = "artifact_superseded_or_not_current"
    return {
        "metadata": {k: v for k, v in record.items() if k != "_meta_path"},
        "summary": summary,
        "extracted_text": extracted,
        "artifact_path": str(files["html"]),
        "provenance": provenance,
        "approval_status": record.get("approval_status"),
        "stale_warning": warning,
        "truth_hierarchy": list(TRUTH_HIERARCHY),
    }


def hermes_artifact_update_status(
    artifact_id: str,
    *,
    approval_status: str,
    notes: str | None = None,
    safety_status: str | None = None,
) -> dict[str, Any]:
    if approval_status not in APPROVAL_STATES:
        raise ValueError(f"invalid approval_status: {approval_status}")
    record = _find_metadata(artifact_id)
    if not record:
        raise FileNotFoundError(f"artifact not found: {artifact_id}")
    meta_path = Path(record["_meta_path"])
    updated = {k: v for k, v in record.items() if k != "_meta_path"}
    updated["approval_status"] = approval_status
    updated["updated_at"] = _now_iso()
    if notes is not None:
        updated["status_notes"] = notes
    if safety_status is not None:
        updated["safety_status"] = safety_status
    _write_json(meta_path, updated)
    _append_index(
        "artifact_update_status",
        {
            "id": artifact_id,
            "approval_status": approval_status,
            "metadata_path": str(meta_path),
        },
    )
    return updated


def hermes_artifact_supersede(
    *,
    superseded_id: str,
    replacement_id: str,
    notes: str | None = None,
) -> dict[str, Any]:
    old = _find_metadata(superseded_id)
    new = _find_metadata(replacement_id)
    if not old:
        raise FileNotFoundError(f"artifact not found: {superseded_id}")
    if not new:
        raise FileNotFoundError(f"artifact not found: {replacement_id}")

    old_path = Path(old["_meta_path"])
    new_path = Path(new["_meta_path"])
    old_payload = {k: v for k, v in old.items() if k != "_meta_path"}
    new_payload = {k: v for k, v in new.items() if k != "_meta_path"}

    old_payload["approval_status"] = "superseded"
    old_payload["superseded_by"] = replacement_id
    old_payload["updated_at"] = _now_iso()
    if notes:
        old_payload["status_notes"] = notes

    supersedes = list(new_payload.get("supersedes") or [])
    if superseded_id not in supersedes:
        supersedes.append(superseded_id)
    new_payload["supersedes"] = supersedes
    new_payload["updated_at"] = _now_iso()

    _write_json(old_path, old_payload)
    _write_json(new_path, new_payload)
    _append_index(
        "artifact_supersede",
        {
            "superseded_id": superseded_id,
            "replacement_id": replacement_id,
            "old_metadata_path": str(old_path),
            "new_metadata_path": str(new_path),
        },
    )
    return {
        "superseded_id": superseded_id,
        "replacement_id": replacement_id,
        "old_status": old_payload["approval_status"],
        "new_supersedes": new_payload["supersedes"],
    }


def _in_range(ts: str, date_from: str | None, date_to: str | None) -> bool:
    if not ts:
        return False
    if date_from and ts < date_from:
        return False
    if date_to and ts > date_to:
        return False
    return True


def hermes_artifact_search(
    *,
    query: str | None = None,
    module: str | None = None,
    artifact_type: str | None = None,
    approval_status: str | None = None,
    tags: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_only: bool = True,
    include_superseded: bool = False,
    limit: int = 20,
) -> dict[str, Any]:
    records = _all_metadata()
    module_slug = _normalize_module(module) if module else None
    tag_set = {t.strip().lower() for t in (tags or []) if t and t.strip()}
    query_l = (query or "").strip().lower()
    out: list[dict[str, Any]] = []

    for row in records:
        status = row.get("approval_status")
        if module_slug and row.get("module") != module_slug:
            continue
        if artifact_type and row.get("artifact_type") != artifact_type:
            continue
        if approval_status and status != approval_status:
            continue
        if not _in_range(row.get("updated_at") or row.get("created_at") or "", date_from, date_to):
            continue
        if current_only and not include_superseded:
            if status == "superseded" or row.get("superseded_by"):
                continue
        elif not include_superseded and status == "superseded":
            continue
        row_tags = {t.lower() for t in (row.get("tags") or [])}
        if tag_set and not tag_set.issubset(row_tags):
            continue
        if query_l:
            haystack = " ".join(
                [
                    str(row.get("id", "")),
                    str(row.get("title", "")),
                    str(row.get("module", "")),
                    str(row.get("artifact_type", "")),
                    " ".join(row.get("retrieval_keywords") or []),
                ]
            ).lower()
            if query_l not in haystack:
                text_path = Path(str((row.get("paths") or {}).get("extracted_text") or ""))
                text_value = text_path.read_text(encoding="utf-8").lower() if text_path.exists() else ""
                if query_l not in text_value:
                    continue

        summary_path = Path(str((row.get("paths") or {}).get("summary_text") or ""))
        summary = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
        out.append(
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "artifact_type": row.get("artifact_type"),
                "module": row.get("module"),
                "approval_status": status,
                "safety_status": row.get("safety_status"),
                "updated_at": row.get("updated_at"),
                "summary": summary,
                "artifact_path": (row.get("paths") or {}).get("artifact_html"),
                "provenance": row.get("provenance") or {},
                "superseded_by": row.get("superseded_by"),
                "truth_boundary": "supporting_only_beneath_runtime_repo_database_and_module_docs",
            }
        )
        if len(out) >= limit:
            break

    return {
        "count": len(out),
        "results": out,
        "query": query or "",
        "filters": {
            "module": module_slug,
            "artifact_type": artifact_type,
            "approval_status": approval_status,
            "tags": sorted(tag_set),
            "date_from": date_from,
            "date_to": date_to,
            "current_only": current_only,
            "include_superseded": include_superseded,
        },
        "truth_hierarchy": list(TRUTH_HIERARCHY),
    }


def hermes_artifact_export(artifact_id: str, *, export_format: str = "json") -> dict[str, Any]:
    bundle = hermes_artifact_get(artifact_id)
    if not bundle:
        raise FileNotFoundError(f"artifact not found: {artifact_id}")
    metadata = bundle["metadata"]
    paths = metadata.get("paths") or {}
    if export_format == "html":
        return {
            "artifact_id": artifact_id,
            "format": "html",
            "path": paths.get("artifact_html"),
            "truth_boundary": bundle["truth_hierarchy"],
        }

    payload = {
        "metadata": metadata,
        "summary": bundle.get("summary"),
        "extracted_text": bundle.get("extracted_text"),
        "provenance": bundle.get("provenance"),
        "truth_hierarchy": bundle.get("truth_hierarchy"),
    }
    export_path = Path(str(paths.get("artifact_dir"))) / "export.json"
    _write_json(export_path, payload)
    _append_index(
        "artifact_export",
        {
            "id": artifact_id,
            "format": "json",
            "path": str(export_path),
        },
    )
    return {
        "artifact_id": artifact_id,
        "format": "json",
        "path": str(export_path),
        "truth_boundary": bundle["truth_hierarchy"],
    }


def get_hermes_artifact_layer_status() -> dict[str, Any]:
    scaffold = ensure_hermes_artifact_scaffold()
    count = len(_all_metadata())
    return {
        "enabled": True,
        "root": scaffold["root"],
        "index_path": scaffold["index_path"],
        "artifact_count": count,
        "lane": scaffold["lane"],
        "branch": scaffold["branch"],
        "commit": scaffold["commit"],
        "truth_hierarchy": scaffold["truth_hierarchy"],
    }

