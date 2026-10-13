"""Studio base ref for Max improvements.

Live deploy line is dell/studio-batch-1013b, then dell/studio-batch-1013.
Never default to main. Never open an issue or PR against main, master,
or any amp / maxine branch.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional

STUDIO_PRIMARY = "dell/studio-batch-1013b"
STUDIO_FALLBACK = "dell/studio-batch-1013"
FORBIDDEN_EXACT = frozenset({"main", "master", "head"})


class UnsafeBaseRef(ValueError):
    """Refused: main/master or a family-edition branch."""


def normalize_ref(ref: str) -> str:
    r = (ref or "").strip()
    if r.startswith("refs/heads/"):
        r = r[len("refs/heads/") :]
    return r


def is_forbidden_base_ref(ref: str) -> bool:
    r = normalize_ref(ref)
    if not r:
        return True
    low = r.lower()
    if low in FORBIDDEN_EXACT:
        return True
    parts = [p for p in re.split(r"[\\/]+", low) if p]
    for p in parts:
        if p in {"amp", "maxine"}:
            return True
        if p.startswith("amp-") or p.startswith("amp_"):
            return True
        if p.startswith("maxine-") or p.startswith("maxine_"):
            return True
    return False


def assert_safe_improve_base_ref(ref: str) -> str:
    """Hard guard: refuse main/master and amp/maxine before any issue/PR."""
    r = normalize_ref(ref)
    if is_forbidden_base_ref(r):
        raise UnsafeBaseRef(
            f"Refusing to open an issue or PR targeting {ref!r}. "
            f"Improvements must use the live Studio line ({STUDIO_PRIMARY} or "
            f"{STUDIO_FALLBACK}). main, master, and amp/maxine branches are blocked."
        )
    return r


def _listed_existing_refs() -> Optional[set[str]]:
    raw = os.getenv("MAX_IMPROVE_EXISTING_REFS")
    if raw is None:
        return None
    return {normalize_ref(x) for x in raw.split(",") if x.strip()}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def ref_exists(ref: str) -> bool:
    """True if the branch is known. Tests set MAX_IMPROVE_EXISTING_REFS.

    If we cannot probe, return True so we keep the Studio default (never main).
    """
    r = normalize_ref(ref)
    if not r:
        return False
    listed = _listed_existing_refs()
    if listed is not None:
        return r in listed
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", r],
            cwd=str(_repo_root()),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return bool((proc.stdout or "").strip())
    except Exception:
        return True


def resolve_base_ref() -> str:
    """Required-with-safe-default: 1013b, else 1013. Never main.

    MAX_IMPROVE_BASE_REF wins when set and safe. If it is the primary
    Studio name and that branch is missing, fall back to 1013.
    """
    configured = (os.getenv("MAX_IMPROVE_BASE_REF") or "").strip()
    if configured:
        safe = assert_safe_improve_base_ref(configured)
        if safe == STUDIO_PRIMARY and not ref_exists(STUDIO_PRIMARY):
            return assert_safe_improve_base_ref(STUDIO_FALLBACK)
        return safe
    candidate = STUDIO_PRIMARY
    if not ref_exists(candidate):
        candidate = STUDIO_FALLBACK
    return assert_safe_improve_base_ref(candidate)
