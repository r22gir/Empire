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
ACTOR_TYPES = {"founder", "max", "openclaw", "hermes", "unknown"}
ACTOR_SOURCES = {
    "verified_session",
    "local_ui",
    "api",
    "max_internal",
    "openclaw",
    "system_generated",
    "unknown",
}
APPROVAL_METHODS = {"ui", "api", "max_internal", "openclaw", "unknown"}
APPROVAL_CONFIDENCE = {"verified_session", "local_ui", "system_generated", "unknown"}

APPROVAL_STATUS_WEIGHTS = {
    "approved": 1.0,
    "changes_requested": 0.45,
    "draft": 0.3,
    "rejected": 0.1,
    "superseded": 0.0,
}
SOURCE_AGENT_TRUST = {
    "founder": 1.0,
    "max": 0.9,
    "hermes": 0.85,
    "openclaw": 0.8,
}

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
QUERY_STOPWORDS = {
    "what",
    "when",
    "where",
    "which",
    "who",
    "how",
    "did",
    "does",
    "about",
    "with",
    "from",
    "that",
    "this",
    "were",
    "have",
    "has",
    "into",
    "just",
    "please",
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


def _normalize_actor_type(actor_type: str | None) -> str:
    value = (actor_type or "unknown").strip().lower()
    return value if value in ACTOR_TYPES else "unknown"


def _normalize_actor_source(actor_source: str | None) -> str:
    value = (actor_source or "unknown").strip().lower()
    return value if value in ACTOR_SOURCES else "unknown"


def _normalize_approval_method(approval_method: str | None) -> str:
    value = (approval_method or "unknown").strip().lower()
    return value if value in APPROVAL_METHODS else "unknown"


def _normalize_approval_confidence(approval_confidence: str | None) -> str:
    value = (approval_confidence or "unknown").strip().lower()
    return value if value in APPROVAL_CONFIDENCE else "unknown"


def _default_approval_method(actor_type: str, actor_source: str) -> str:
    if actor_source == "local_ui":
        return "ui"
    if actor_source in {"api", "verified_session"}:
        return "api"
    if actor_source == "openclaw" or actor_type == "openclaw":
        return "openclaw"
    if actor_source == "max_internal" or actor_type in {"max", "hermes"}:
        return "max_internal"
    return "unknown"


def _default_approval_confidence(actor_source: str, approval_method: str) -> str:
    if actor_source == "verified_session":
        return "verified_session"
    if actor_source == "local_ui" or approval_method == "ui":
        return "local_ui"
    if actor_source in {"system_generated", "max_internal", "openclaw"}:
        return "system_generated"
    if approval_method in {"max_internal", "openclaw"}:
        return "system_generated"
    return "unknown"


def _approval_identity(
    *,
    actor_id: str | None = None,
    actor_type: str | None = None,
    actor_label: str | None = None,
    actor_source: str | None = None,
    actor_note: str | None = None,
    approval_method: str | None = None,
    approval_confidence: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    normalized_actor_type = _normalize_actor_type(actor_type)
    normalized_actor_id = (actor_id or "").strip() or None
    normalized_actor_label = (actor_label or "").strip() or None
    normalized_actor_source = _normalize_actor_source(actor_source)
    if normalized_actor_source == "verified_session" and not normalized_actor_id:
        normalized_actor_source = "unknown"

    method = _normalize_approval_method(approval_method)
    if method == "unknown" and not approval_method:
        method = _default_approval_method(normalized_actor_type, normalized_actor_source)

    confidence = _normalize_approval_confidence(approval_confidence)
    if confidence == "unknown" and not approval_confidence:
        confidence = _default_approval_confidence(normalized_actor_source, method)
    if confidence == "verified_session" and normalized_actor_source != "verified_session":
        confidence = _default_approval_confidence(normalized_actor_source, method)

    event_time = timestamp or _now_iso()
    note = (actor_note or "").strip() or None
    return {
        "approval_actor_id": normalized_actor_id,
        "approval_actor_type": normalized_actor_type,
        "approval_actor_label": normalized_actor_label,
        "approval_actor_source": normalized_actor_source,
        "approval_timestamp": event_time,
        "approval_note": note,
        "approval_method": method,
        "approval_confidence": confidence,
    }


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


def _parse_iso(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def _freshness_score(ts: str | None) -> float:
    dt = _parse_iso(ts)
    if not dt:
        return 0.2
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)
    if age_days <= 1:
        return 1.0
    if age_days <= 7:
        return 0.9
    if age_days <= 30:
        return 0.75
    if age_days <= 90:
        return 0.55
    if age_days <= 180:
        return 0.35
    return 0.2


def _provenance_score(provenance: dict[str, Any]) -> float:
    score = 0.0
    if provenance.get("source_agent"):
        score += 0.3
    if provenance.get("source_prompt_hash"):
        score += 0.2
    if provenance.get("source_files"):
        score += 0.2
    if provenance.get("source_endpoints"):
        score += 0.2
    if provenance.get("truth_hierarchy"):
        score += 0.1
    return min(1.0, score)


def _artifact_stale_warning(record: dict[str, Any]) -> str | None:
    status = str(record.get("approval_status") or "").lower()
    if status == "superseded" or record.get("superseded_by"):
        return "artifact_superseded_or_not_current"
    if status in {"draft", "rejected", "changes_requested"}:
        return f"artifact_status_{status}_not_current_truth"
    if status != "approved":
        return "artifact_not_approved_current_truth"
    return None


def _is_current_approved(record: dict[str, Any]) -> bool:
    return (
        str(record.get("approval_status") or "").lower() == "approved"
        and not record.get("superseded_by")
    )


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

    creation_method = "openclaw" if source == "openclaw" else "max_internal" if source in {"max", "hermes"} else "unknown"
    creation_identity = _approval_identity(
        actor_type=source if source in ACTOR_TYPES else "unknown",
        actor_source="system_generated",
        actor_note="artifact_created",
        approval_method=creation_method,
        approval_confidence="system_generated",
        timestamp=now,
    )
    creation_history_row = {
        "approval_status": status,
        "approval_actor_id": creation_identity["approval_actor_id"],
        "approval_actor_type": creation_identity["approval_actor_type"],
        "approval_actor_label": creation_identity["approval_actor_label"],
        "approval_actor_source": creation_identity["approval_actor_source"],
        "approval_timestamp": creation_identity["approval_timestamp"],
        "approval_note": creation_identity["approval_note"],
        "approval_method": creation_identity["approval_method"],
        "approval_confidence": creation_identity["approval_confidence"],
        # Backward-compat aliases
        "actor_type": creation_identity["approval_actor_type"],
        "actor_label": creation_identity["approval_actor_label"],
        "note": creation_identity["approval_note"],
        "timestamp": creation_identity["approval_timestamp"],
    }

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
        "approval_actor_id": creation_identity["approval_actor_id"],
        "approval_actor_type": creation_identity["approval_actor_type"],
        "approval_actor_label": creation_identity["approval_actor_label"],
        "approval_actor_source": creation_identity["approval_actor_source"],
        "approval_timestamp": creation_identity["approval_timestamp"],
        "approval_note": creation_identity["approval_note"],
        "approval_method": creation_identity["approval_method"],
        "approval_confidence": creation_identity["approval_confidence"],
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
        "approval_history": [creation_history_row],
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
    warning = _artifact_stale_warning(record)
    return {
        "metadata": {k: v for k, v in record.items() if k != "_meta_path"},
        "summary": summary,
        "extracted_text": extracted,
        "artifact_path": str(files["html"]),
        "provenance": provenance,
        "approval_status": record.get("approval_status"),
        "is_current": _is_current_approved(record),
        "stale_warning": warning,
        "truth_hierarchy": list(TRUTH_HIERARCHY),
    }


def hermes_artifact_update_status(
    artifact_id: str,
    *,
    approval_status: str,
    notes: str | None = None,
    safety_status: str | None = None,
    actor_id: str | None = None,
    actor_type: str | None = None,
    actor_label: str | None = None,
    actor_source: str | None = None,
    approval_method: str | None = None,
    approval_confidence: str | None = None,
    actor_note: str | None = None,
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

    identity = _approval_identity(
        actor_id=actor_id,
        actor_type=actor_type,
        actor_label=actor_label,
        actor_source=actor_source,
        actor_note=actor_note or notes,
        approval_method=approval_method,
        approval_confidence=approval_confidence,
        timestamp=updated["updated_at"],
    )
    updated["approval_actor_id"] = identity["approval_actor_id"]
    updated["approval_actor_type"] = identity["approval_actor_type"]
    updated["approval_actor_label"] = identity["approval_actor_label"]
    updated["approval_actor_source"] = identity["approval_actor_source"]
    updated["approval_timestamp"] = identity["approval_timestamp"]
    updated["approval_note"] = identity["approval_note"]
    updated["approval_method"] = identity["approval_method"]
    updated["approval_confidence"] = identity["approval_confidence"]

    history = list(updated.get("approval_history") or [])
    history.append(
        {
            "approval_status": approval_status,
            "approval_actor_id": identity["approval_actor_id"],
            "approval_actor_type": identity["approval_actor_type"],
            "approval_actor_label": identity["approval_actor_label"],
            "approval_actor_source": identity["approval_actor_source"],
            "approval_timestamp": identity["approval_timestamp"],
            "approval_note": identity["approval_note"],
            "approval_method": identity["approval_method"],
            "approval_confidence": identity["approval_confidence"],
            # Backward-compat aliases
            "actor_type": identity["approval_actor_type"],
            "actor_label": identity["approval_actor_label"],
            "note": identity["approval_note"],
            "timestamp": identity["approval_timestamp"],
        }
    )
    updated["approval_history"] = history
    _write_json(meta_path, updated)
    _append_index(
        "artifact_update_status",
        {
            "id": artifact_id,
            "approval_status": approval_status,
            "approval_actor_id": identity["approval_actor_id"],
            "approval_actor_type": identity["approval_actor_type"],
            "approval_actor_label": identity["approval_actor_label"],
            "approval_actor_source": identity["approval_actor_source"],
            "approval_method": identity["approval_method"],
            "approval_confidence": identity["approval_confidence"],
            "metadata_path": str(meta_path),
        },
    )
    return updated


def hermes_artifact_supersede(
    *,
    superseded_id: str,
    replacement_id: str,
    notes: str | None = None,
    actor_id: str | None = None,
    actor_type: str | None = None,
    actor_label: str | None = None,
    actor_source: str | None = None,
    approval_method: str | None = None,
    approval_confidence: str | None = None,
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
    identity = _approval_identity(
        actor_id=actor_id,
        actor_type=actor_type,
        actor_label=actor_label,
        actor_source=actor_source,
        actor_note=(notes or "").strip() or "superseded_by_replacement",
        approval_method=approval_method,
        approval_confidence=approval_confidence,
        timestamp=old_payload["updated_at"],
    )
    old_payload["approval_actor_id"] = identity["approval_actor_id"]
    old_payload["approval_actor_type"] = identity["approval_actor_type"]
    old_payload["approval_actor_label"] = identity["approval_actor_label"]
    old_payload["approval_actor_source"] = identity["approval_actor_source"]
    old_payload["approval_timestamp"] = identity["approval_timestamp"]
    old_payload["approval_note"] = identity["approval_note"]
    old_payload["approval_method"] = identity["approval_method"]
    old_payload["approval_confidence"] = identity["approval_confidence"]

    old_history = list(old_payload.get("approval_history") or [])
    old_history.append(
        {
            "approval_status": "superseded",
            "approval_actor_id": identity["approval_actor_id"],
            "approval_actor_type": identity["approval_actor_type"],
            "approval_actor_label": identity["approval_actor_label"],
            "approval_actor_source": identity["approval_actor_source"],
            "approval_timestamp": identity["approval_timestamp"],
            "approval_note": identity["approval_note"],
            "approval_method": identity["approval_method"],
            "approval_confidence": identity["approval_confidence"],
            # Backward-compat aliases
            "actor_type": identity["approval_actor_type"],
            "actor_label": identity["approval_actor_label"],
            "note": identity["approval_note"],
            "timestamp": identity["approval_timestamp"],
        }
    )
    old_payload["approval_history"] = old_history

    supersedes = list(new_payload.get("supersedes") or [])
    if superseded_id not in supersedes:
        supersedes.append(superseded_id)
    new_payload["supersedes"] = supersedes
    new_payload["updated_at"] = _now_iso()
    new_identity = _approval_identity(
        actor_id=actor_id,
        actor_type=actor_type,
        actor_label=actor_label,
        actor_source=actor_source,
        actor_note=(notes or "").strip() or "registered_supersedes_link",
        approval_method=approval_method,
        approval_confidence=approval_confidence,
        timestamp=new_payload["updated_at"],
    )
    new_payload["approval_actor_id"] = new_identity["approval_actor_id"]
    new_payload["approval_actor_type"] = new_identity["approval_actor_type"]
    new_payload["approval_actor_label"] = new_identity["approval_actor_label"]
    new_payload["approval_actor_source"] = new_identity["approval_actor_source"]
    new_payload["approval_timestamp"] = new_identity["approval_timestamp"]
    new_payload["approval_note"] = new_identity["approval_note"]
    new_payload["approval_method"] = new_identity["approval_method"]
    new_payload["approval_confidence"] = new_identity["approval_confidence"]

    new_history = list(new_payload.get("approval_history") or [])
    new_history.append(
        {
            "approval_status": new_payload.get("approval_status") or "draft",
            "approval_actor_id": new_identity["approval_actor_id"],
            "approval_actor_type": new_identity["approval_actor_type"],
            "approval_actor_label": new_identity["approval_actor_label"],
            "approval_actor_source": new_identity["approval_actor_source"],
            "approval_timestamp": new_identity["approval_timestamp"],
            "approval_note": new_identity["approval_note"],
            "approval_method": new_identity["approval_method"],
            "approval_confidence": new_identity["approval_confidence"],
            # Backward-compat aliases
            "actor_type": new_identity["approval_actor_type"],
            "actor_label": new_identity["approval_actor_label"],
            "note": new_identity["approval_note"],
            "timestamp": new_identity["approval_timestamp"],
        }
    )
    new_payload["approval_history"] = new_history

    _write_json(old_path, old_payload)
    _write_json(new_path, new_payload)
    _append_index(
        "artifact_supersede",
        {
            "superseded_id": superseded_id,
            "replacement_id": replacement_id,
            "approval_actor_id": identity["approval_actor_id"],
            "approval_actor_type": identity["approval_actor_type"],
            "approval_actor_label": identity["approval_actor_label"],
            "approval_actor_source": identity["approval_actor_source"],
            "approval_method": identity["approval_method"],
            "approval_confidence": identity["approval_confidence"],
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


def _match_ratio(terms: list[str], values: list[str]) -> float:
    if not terms:
        return 0.0
    haystack = " ".join(values).lower()
    matches = sum(1 for term in terms if term and term in haystack)
    return matches / max(1, len(terms))


def _rank_artifact(
    row: dict[str, Any],
    *,
    query_l: str,
    query_terms: list[str],
    module_slug: str | None,
    artifact_type_filter: str | None,
    tag_set: set[str],
    summary: str,
    extracted_text: str,
) -> dict[str, Any]:
    status = str(row.get("approval_status") or "").lower()
    title = str(row.get("title") or "")
    module_value = str(row.get("module") or "")
    artifact_type_value = str(row.get("artifact_type") or "")
    tags_value = [str(t).strip().lower() for t in (row.get("tags") or []) if str(t).strip()]
    keywords_value = [str(t).strip().lower() for t in (row.get("retrieval_keywords") or []) if str(t).strip()]
    provenance = row.get("provenance") or {}
    source_agent = str(row.get("source_agent") or provenance.get("source_agent") or "unknown").lower()

    stale_warning = _artifact_stale_warning(row)
    current_weight = 1.0 if _is_current_approved(row) else 0.0
    approval_weight = APPROVAL_STATUS_WEIGHTS.get(status, 0.1)
    if stale_warning == "artifact_superseded_or_not_current":
        approval_weight = min(approval_weight, 0.2)

    module_weight = 0.2
    if module_slug:
        module_weight = 1.0 if module_value == module_slug else 0.0
    elif module_value and module_value in query_l:
        module_weight = 0.65

    artifact_type_weight = 0.0
    if artifact_type_filter:
        artifact_type_weight = 1.0 if artifact_type_value == artifact_type_filter else 0.0
    elif artifact_type_value and artifact_type_value in query_l:
        artifact_type_weight = 0.6

    title_l = title.lower()
    exact_phrase_match = 0.0
    if query_l:
        if query_l == title_l or query_l in title_l:
            exact_phrase_match = 1.0
        elif query_l in " ".join(keywords_value) or query_l in " ".join(tags_value):
            exact_phrase_match = 0.8
        elif query_l in extracted_text.lower():
            exact_phrase_match = 0.7

    title_weight = _match_ratio(query_terms, [title_l])
    tag_weight = _match_ratio(query_terms or sorted(tag_set), tags_value)
    retrieval_weight = _match_ratio(query_terms, keywords_value)

    freshness_score = _freshness_score(row.get("updated_at") or row.get("created_at"))
    provenance_weight = _provenance_score(provenance)
    source_agent_weight = SOURCE_AGENT_TRUST.get(source_agent, 0.45)

    matched_fields: list[str] = []
    if status:
        matched_fields.append(f"approval_status:{status}")
    if current_weight > 0:
        matched_fields.append("current")
    if module_weight > 0:
        matched_fields.append("module")
    if artifact_type_weight > 0:
        matched_fields.append("artifact_type")
    if exact_phrase_match > 0:
        matched_fields.append("exact_phrase")
    if title_weight > 0:
        matched_fields.append("title")
    if tag_weight > 0:
        matched_fields.append("tags")
    if retrieval_weight > 0:
        matched_fields.append("retrieval_keywords")
    if provenance_weight > 0:
        matched_fields.append("provenance")
    if freshness_score >= 0.75:
        matched_fields.append("freshness")
    if source_agent_weight >= 0.8:
        matched_fields.append("source_agent")

    score = (
        approval_weight * 30.0
        + current_weight * 15.0
        + module_weight * 12.0
        + exact_phrase_match * 10.0
        + title_weight * 8.0
        + tag_weight * 6.0
        + retrieval_weight * 6.0
        + artifact_type_weight * 5.0
        + freshness_score * 4.0
        + provenance_weight * 3.0
        + source_agent_weight * 1.0
    )
    return {
        "score": round(score, 4),
        "matched_fields": sorted(set(matched_fields)),
        "freshness_score": round(freshness_score, 4),
        "approval_weight": round(approval_weight, 4),
        "module_weight": round(module_weight, 4),
        "provenance_weight": round(provenance_weight, 4),
        "stale_warning": stale_warning,
        "summary": summary,
        "extracted_text": extracted_text,
    }


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
    query_terms = [
        term
        for term in re.findall(r"[a-z0-9]+", query_l)
        if len(term) >= 3 and term not in QUERY_STOPWORDS
    ]
    ranked_rows: list[dict[str, Any]] = []

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
            text_path = Path(str((row.get("paths") or {}).get("extracted_text") or ""))
            text_value = text_path.read_text(encoding="utf-8").lower() if text_path.exists() else ""
            if query_l not in haystack and query_l not in text_value:
                if query_terms:
                    matched_terms = sum(1 for term in query_terms if (term in haystack) or (term in text_value))
                    required_matches = 1
                    if matched_terms < required_matches:
                        continue
                else:
                    continue

        summary_path = Path(str((row.get("paths") or {}).get("summary_text") or ""))
        summary = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
        text_path = Path(str((row.get("paths") or {}).get("extracted_text") or ""))
        extracted = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        ranking = _rank_artifact(
            row,
            query_l=query_l,
            query_terms=query_terms,
            module_slug=module_slug,
            artifact_type_filter=artifact_type,
            tag_set=tag_set,
            summary=summary,
            extracted_text=extracted,
        )
        ranked_rows.append(
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "artifact_type": row.get("artifact_type"),
                "module": row.get("module"),
                "source_agent": row.get("source_agent"),
                "approval_status": status,
                "is_current": _is_current_approved(row),
                "safety_status": row.get("safety_status"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "summary": ranking["summary"],
                "artifact_path": (row.get("paths") or {}).get("artifact_html"),
                "provenance": row.get("provenance") or {},
                "superseded_by": row.get("superseded_by"),
                "score": ranking["score"],
                "matched_fields": ranking["matched_fields"],
                "freshness_score": ranking["freshness_score"],
                "approval_weight": ranking["approval_weight"],
                "module_weight": ranking["module_weight"],
                "provenance_weight": ranking["provenance_weight"],
                "stale_warning": ranking["stale_warning"],
                "truth_boundary": "supporting_only_beneath_runtime_repo_database_and_module_docs",
            }
        )

    ranked_rows.sort(
        key=lambda item: (
            float(item.get("score") or 0.0),
            item.get("updated_at") or "",
            item.get("created_at") or "",
        ),
        reverse=True,
    )
    out = ranked_rows[:limit]

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
        "ranking_version": "hermes_artifact_rank_v2",
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
