"""Lane-aware runtime metadata helpers for git freshness and status endpoints."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


def _lane() -> str:
    return (os.getenv("EMPIRE_LANE", "unknown").strip() or "unknown").lower()


def _port(env_key: str, default: int) -> int:
    raw = (os.getenv(env_key, str(default)) or "").strip()
    return int(raw) if raw.isdigit() else default


def _public_base_url_for_lane(lane: str) -> str | None:
    env_override = (os.getenv("EMPIRE_PUBLIC_BASE_URL") or "").strip()
    if env_override:
        return env_override.rstrip("/")

    mapping = {
        "main": "https://studio.empirebox.store",
        "stable": "https://studio.empirebox.store",
        "v10-test": "https://test-studio.empirebox.store",
    }
    return mapping.get(lane)


def _expected_worktree_for_lane(lane: str) -> Path | None:
    env_override = (os.getenv("EMPIRE_WORKTREE_ROOT") or "").strip()
    if env_override:
        return Path(env_override).expanduser().resolve()

    mapping = {
        "main": "/home/rg/empire-repo-main",
        "stable": "/home/rg/empire-repo-main",
        "v10-test": "/home/rg/empire-repo-v10",
        "feature-v10": "/home/rg/empire-repo-feature",
    }
    raw = mapping.get(lane)
    return Path(raw) if raw else None


def _run_git(cwd: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.stdout.strip() if proc.returncode == 0 else ""
    except Exception:
        return ""


def _resolve_repo_root(backend_cwd: Path, expected_worktree: Path | None) -> tuple[Path, str]:
    top_level = _run_git(backend_cwd, "rev-parse", "--show-toplevel")
    if top_level:
        return Path(top_level), "git_rev_parse_show_toplevel"

    if expected_worktree and expected_worktree.exists():
        return expected_worktree, "lane_expected_worktree"

    if backend_cwd.name == "backend" and (backend_cwd.parent / ".git").exists():
        return backend_cwd.parent, "backend_parent_git_fallback"

    return backend_cwd, "backend_cwd_fallback"


def get_lane_git_metadata() -> dict[str, Any]:
    lane = _lane()
    backend_port = _port("EMPIRE_BACKEND_PORT", 8000)
    frontend_port = _port("EMPIRE_FRONTEND_EXPECTED_PORT", 3005)
    backend_cwd = Path.cwd().resolve()
    expected_worktree = _expected_worktree_for_lane(lane)
    repo_root, source_path_used = _resolve_repo_root(backend_cwd, expected_worktree)

    branch = _run_git(repo_root, "branch", "--show-current")
    commit_hash = _run_git(repo_root, "rev-parse", "--short", "HEAD")
    commit_message = _run_git(repo_root, "log", "--oneline", "-1")
    uncommitted = _run_git(repo_root, "status", "--porcelain")
    uncommitted_count = len([row for row in uncommitted.splitlines() if row.strip()])

    mismatch_reason: str | None = None
    if expected_worktree and repo_root != expected_worktree:
        mismatch_reason = f"repo_root_mismatch expected={expected_worktree} actual={repo_root}"

    freshness_status = "ok" if commit_hash else "unavailable"
    if mismatch_reason:
        freshness_status = "mismatch"

    return {
        "lane": lane,
        "worktree_path": str(repo_root),
        "backend_cwd": str(backend_cwd),
        "source_path_used": source_path_used,
        "expected_worktree_path": str(expected_worktree) if expected_worktree else None,
        "branch": branch,
        "commit": commit_hash,
        "message": commit_message,
        "uncommitted_count": uncommitted_count,
        "expected_backend_port": backend_port,
        "expected_frontend_port": frontend_port,
        "public_base_url": _public_base_url_for_lane(lane),
        "freshness_status": freshness_status,
        "mismatch_reason": mismatch_reason,
    }

