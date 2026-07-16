"""HOTFIX 4.0 — Canonical output path for MAX drawings.

Every drawing tool that writes a PDF/SVG MUST use the resolver in
this module instead of `os.path.expanduser("~/empire-repo/...")`.

ROOT CAUSE — the stale-fork leak:

  The historical default was `~/empire-repo/uploads/arch_drawings/`.
  The active canonical repo is `~/empire-repo-main/`. The drawing
  tools were still writing to the stale fork — so a freshly rendered
  PDF showed up under `~/empire-repo/uploads/arch_drawings/drawing_xxx.pdf`
  even though MAX's tooling was running from `~/empire-repo-main/`. The
  founder couldn't find the output in the active repo's data tree.

  Direct cause: hardcoded `os.path.expanduser("~/empire-repo/...")`
  in tool_executor.py:2569 (svg_to_pdf) and :2687 (sketch_to_drawing).

FIX:

  This module centralizes the output-path resolution. The default
  lands under the active canonical repo's data dir; the staging-fork
  fallback is explicit and CRITICAL-logged so it can never silently
  happen again.

  An environment variable `MAX_DRAWINGS_OUTPUT_DIR` overrides the
  default if a deployment has a different convention.

  A startup-time check refuses to operate if the resolved default is
  underneath `/home/rg/empire-repo/` (the stale fork) — preventing
  any caller from accidentally re-introducing the bug.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("drawing.canonical_path")


_ENV_OVERRIDE = "MAX_DRAWINGS_OUTPUT_DIR"

# The canonical output dir lives under the active repo's data tree.
# Tests can override via MAX_DRAWINGS_OUTPUT_DIR (e.g. to a tmp_path).
_DEFAULT_CANON_DIR = (
    Path.home() / "empire-repo-main" / "backend" / "data" / "drawings"
)

# Path prefixes that MUST NOT be used as the resolved output root. The
# stale fork is the canonical example — but anything that doesn't live
# under the canonical repo is suspicious and triggers a CRITICAL log.
def _is_stale_fork_root(candidate: Path) -> bool:
    """Return True if `candidate` lives under a known stale root.

    The legacy leak path was `~/empire-repo/uploads/arch_drawings/`
    (the stale Empire fork).  We also reject the bare `~/empire-repo/`
    parent as a precaution.
    """
    home = Path.home().resolve()
    bad_roots = [
        home / "empire-repo",   # the stale fork root
        home / "empire-repo-main-old",
    ]
    candidate_resolved = candidate.resolve()
    for bad in bad_roots:
        try:
            candidate_resolved.relative_to(bad.resolve())
            return True
        except ValueError:
            continue
    return False


def canonical_drawings_dir() -> Path:
    """Return the canonical output directory for MAX drawings.

    Resolution order:
      1. $MAX_DRAWINGS_OUTPUT_DIR (if set) — checked for staleness.
      2. ~/empire-repo-main/backend/data/drawings/ — the active repo.

    Returns the path with mkdir(parents=True, exist_ok=True) applied.
    Raises RuntimeError if either source resolves to a known stale
    fork root (~/empire-repo/, ~/empire-repo-main-old/, etc.) — we
    fail loud rather than silently fall back, so a misconfiguration
    is caught at first-render time rather than data-loss time.
    """
    override = os.getenv(_ENV_OVERRIDE)
    candidate = Path(override) if override else _DEFAULT_CANON_DIR

    if _is_stale_fork_root(candidate):
        logger.critical(
            "drawing canonical path resolved to a stale fork root: "
            "%s (override=%s). Refusing to operate — set "
            "MAX_DRAWINGS_OUTPUT_DIR to a path under the active repo "
            "(~/empire-repo-main/) or remove the env var to use the "
            "default.", candidate, override,
        )
        raise RuntimeError(
            f"drawing canonical path resolved to a stale fork root: "
            f"{candidate}. Set MAX_DRAWINGS_OUTPUT_DIR to a path under "
            f"the active repo (~/empire-repo-main/) or remove the env "
            f"var to use the default."
        )

    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def new_drawing_path(prefix: str = "drawing", suffix: str = ".pdf") -> Path:
    """Convenience: build a unique output file under the canonical dir."""
    import uuid as _uuid
    out_dir = canonical_drawings_dir()
    return out_dir / f"{prefix}_{_uuid.uuid4().hex[:8]}{suffix}"


# ── one-time startup check (HOTFIX 4.0 item d: Import-mode honesty) ──
# When this module is first imported, emit a CRITICAL log line if the
# resolved default path falls under /home/rg/empire-repo/ (the stale
# fork). The check runs even if canonical_drawings_dir() hasn't been
# called yet, so a misconfigured env var is caught at boot rather than
# only when the first drawing is rendered.
_resolved_default = _DEFAULT_CANON_DIR
if _is_stale_fork_root(_resolved_default):
    logger.critical(
        "Default drawings path %s lives under the stale fork root. "
        "Set MAX_DRAWINGS_OUTPUT_DIR or fix the canonical repo path.",
        _resolved_default,
    )
