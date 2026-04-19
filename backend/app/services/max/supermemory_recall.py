"""Bounded Supermemory scaffold for MAX secondary recall.

This is deliberately not a source of truth. Runtime, registry, repo, and live
health checks override every recall result from this module.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.services.max.operating_registry import get_registry_load_info, load_operating_registry
from app.services.max.surface_identity import normalize_surface


STORE_PATH = Path.home() / "empire-repo" / "backend" / "data" / "max" / "supermemory_scaffold.jsonl"
MEMORY_VALID_DAYS = 30
GENERIC_SURFACES = {"", "all", "generic", None}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.fromtimestamp(0, timezone.utc)


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return ""


def _registry_baseline() -> dict[str, Any]:
    info = get_registry_load_info()
    if not info.get("registry_version") or info.get("last_error"):
        raise RuntimeError(f"registry unavailable for Supermemory write: {info.get('last_error')}")
    commit = _git_commit()
    if not commit:
        raise RuntimeError("commit hash unavailable for Supermemory write")
    return {"registry_version": info["registry_version"], "commit_hash": commit}


def _load_memories(path: Path = STORE_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    memories: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                memories.append(item)
        except Exception:
            continue
    return memories


def _append_memory(memory: dict[str, Any], path: Path = STORE_PATH) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(memory, sort_keys=True, default=str) + "\n")
    return {"written": True, "memory_id": memory["id"], "path": str(path)}


def rank_supermemory_results(
    memories: list[dict[str, Any]],
    *,
    current_surface: str,
    current_registry_version: str,
    current_commit_hash: str | None = None,
) -> list[dict[str, Any]]:
    """Rank recall by surface match, registry version match, then recency."""
    canonical = normalize_surface(current_surface).get("canonical_channel")
    current_commit_hash = current_commit_hash or _git_commit()
    now = _now()

    def decorated(memory: dict[str, Any]) -> tuple[int, int, int, float]:
        meta = memory.get("metadata") or {}
        surface = meta.get("surface") or memory.get("surface")
        memory_surface = normalize_surface(surface).get("canonical_channel") if surface not in GENERIC_SURFACES else "generic"
        surface_score = 2 if memory_surface == canonical else (1 if memory_surface == "generic" else 0)
        registry_score = 1 if meta.get("registry_version") == current_registry_version else 0
        commit_score = 1 if current_commit_hash and meta.get("commit_hash") == current_commit_hash else 0
        written_at = _parse_time(memory.get("written_at") or meta.get("written_at"))
        stale_penalty = -1 if memory.get("stale") or _parse_time(meta.get("valid_until")) < now else 0
        return (surface_score, registry_score, commit_score + stale_penalty, written_at.timestamp())

    return sorted(memories, key=decorated, reverse=True)


def query_supermemory_recall(
    query: str,
    *,
    surface: str = "web",
    limit: int = 5,
    path: Path = STORE_PATH,
) -> dict[str, Any]:
    """Return ranked secondary recall after surface identity resolution."""
    baseline = _registry_baseline()
    canonical = normalize_surface(surface).get("canonical_channel")
    query_text = (query or "").lower()
    memories = _load_memories(path)
    if query_text:
        filtered = [
            memory for memory in memories
            if query_text in (memory.get("content") or "").lower()
            or any(query_text in str(tag).lower() for tag in memory.get("tags") or [])
            or query_text in str(memory.get("product") or "").lower()
        ]
        if filtered:
            memories = filtered
    ranked = rank_supermemory_results(
        memories,
        current_surface=canonical,
        current_registry_version=baseline["registry_version"],
        current_commit_hash=baseline["commit_hash"],
    )
    return {
        "source": "supermemory_scaffold",
        "authority": "secondary_recall_only",
        "runtime_truth_override": True,
        "surface": canonical,
        "registry_version": baseline["registry_version"],
        "commit_hash": baseline["commit_hash"],
        "results": ranked[:limit],
    }


def write_supermemory_memory(
    *,
    bucket: str,
    content: str,
    surface: str = "generic",
    tags: list[str] | None = None,
    product: str | None = None,
    trigger: str,
    path: Path = STORE_PATH,
) -> dict[str, Any]:
    """Write a guarded secondary recall memory with registry/commit metadata."""
    baseline = _registry_baseline()
    written_at = _now()
    valid_until = written_at + timedelta(days=MEMORY_VALID_DAYS)
    canonical = normalize_surface(surface).get("canonical_channel") if surface not in GENERIC_SURFACES else "generic"
    memory = {
        "id": f"sm-{uuid4().hex[:12]}",
        "bucket": bucket,
        "content": content[:1600],
        "surface": canonical,
        "product": product,
        "tags": sorted(set(tags or [])),
        "trigger": trigger,
        "stale": False,
        "written_at": _iso(written_at),
        "metadata": {
            "registry_version": baseline["registry_version"],
            "commit_hash": baseline["commit_hash"],
            "surface": canonical,
            "product": product,
            "written_at": _iso(written_at),
            "valid_until": _iso(valid_until),
            "version_ceiling": baseline["registry_version"],
            "authority": "secondary_recall_only",
        },
    }
    return _append_memory(memory, path)


def write_handoff_memory_from_packet(packet: dict[str, Any]) -> dict[str, Any]:
    tier_1 = packet.get("tier_1") or {}
    surface = (tier_1.get("founder_surface_identity") or {}).get("canonical_channel") or "web_chat"
    runtime = tier_1.get("last_runtime_truth_result") or {}
    content = (
        f"Handoff refreshed. Current task: {tier_1.get('current_task')}. "
        f"Surface: {surface}. Runtime commit: {runtime.get('commit')}. "
        f"Registry: {tier_1.get('registry_version')}. "
        f"Last eval: {(packet.get('last_evaluation_score') or {}).get('overall_score')}."
    )
    return write_supermemory_memory(
        bucket="session/handoff memory",
        content=content,
        surface=surface,
        tags=["empirebox", "founder", "max", "handoff"],
        product="max",
        trigger="verified_handoff_refresh",
    )


def write_product_snapshots(path: Path = STORE_PATH) -> dict[str, Any]:
    registry = load_operating_registry()
    targets = {"relistapp", "finance", "openclaw", "max"}
    writes = []
    for product in registry.get("ecosystem_products", []):
        key = product.get("key")
        if key not in targets:
            continue
        content = (
            f"{key} status: {product.get('status')}. "
            f"Canonical frontend: {product.get('canonical_frontend_path')}. "
            f"Canonical routes: {', '.join(product.get('canonical_backend_routes') or [])}. "
            f"Limitations: {'; '.join(product.get('limitations') or [])}."
        )
        writes.append(write_supermemory_memory(
            bucket="product snapshots",
            content=content,
            surface="generic",
            tags=["empirebox", "founder", "max", key],
            product=key,
            trigger="registry_version_update" if key == "max" else "verified_product_snapshot",
            path=path,
        ))

    surfaces = registry.get("surfaces", [])
    surface_content = "; ".join(
        f"{item.get('name')}={item.get('status')} channel={item.get('canonical_channel') or 'none'}"
        for item in surfaces
    )
    writes.append(write_supermemory_memory(
        bucket="product snapshots",
        content=f"MAX surfaces: {surface_content}. Phone MAX is not implemented.",
        surface="generic",
        tags=["empirebox", "founder", "max", "registry"],
        product="max_surfaces",
        trigger="registry_version_update",
        path=path,
    ))
    return {"written_count": sum(1 for item in writes if item.get("written")), "writes": writes, "path": str(path)}


def render_supermemory_for_prompt(channel: str = "web", limit: int = 3) -> str:
    try:
        recall = query_supermemory_recall("max", surface=channel, limit=limit)
    except Exception as exc:
        return f"Supermemory secondary recall unavailable: {exc}"
    results = recall.get("results") or []
    if not results:
        return "Supermemory secondary recall: no matching verified scaffold memories."
    lines = [
        "Supermemory secondary recall only. Runtime, registry, repo, and live health checks override these memories."
    ]
    for memory in results:
        meta = memory.get("metadata") or {}
        lines.append(
            f"- [{memory.get('bucket')}] {memory.get('content')} "
            f"(registry={meta.get('registry_version')} commit={meta.get('commit_hash')} surface={meta.get('surface')})"
        )
    return "\n".join(lines)
