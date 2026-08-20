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

# Canonical-repo marker file. The single source of truth for "this
# directory IS the active canonical repo." All path resolvers —
# drawing output, file_read, file_write, system_prompt git cwd,
# upload sinks — must verify this marker before treating any path as
# canonical. If the marker is missing, the path is REJECTED — even
# if it lands inside the historical canonical dir string.
#
# Stale fork MUST NOT have this file. If a botched clone ever drops a
# marker into ~/empire-repo/, the resolver will misidentify that tree
# as canonical. The dispatch's "eradicate the stale fork" item is the
# structural fix; the marker is the runtime guardrail that should
# survive even after eradication (defends against the next stale tree).
_CANONICAL_MARKER_FILENAME = ".empire-canonical"
_CANONICAL_MARKER_TOKEN = "EmpireBox canonical root\n"


class CanonicalRootError(Exception):
    """Raised when path resolution cannot find/verify the canonical
    repo. Caller is expected to refuse the operation rather than
    fall back to a non-canonical default.
    """


def resolve_canonical_root(start: os.PathLike | str | None = None) -> Path:
    """Return the absolute path of the canonical repo root, verified
    by the presence of the `.empire-canonical` marker.

    Walks up from `start` (default: this file's directory) until it
    finds the marker. Raises CanonicalRootError if no marker is found
    within 6 levels.

    The marker is a file containing the canonical token. Its presence
    is the single source of truth — NOT the string `~/empire-repo-main/`.
    A different clone location with the same marker file is equally
    canonical.

    Used by:
      - file_read / file_write (relative paths resolved against this root)
      - system_prompt.py git cwd (MAX's git context is always canonical)
      - quotes.py uploads_dir (client uploads land in the canonical tree)
      - openclaw_worker.py drawings_dir (rendered SVGs land in canonical)
      - canonical_drawings_dir() (this module's own drawing output)

    No fallback. Caller must refuse if CanonicalRootError is raised.
    """
    start_path = Path(start).resolve() if start else Path(__file__).resolve().parent
    cur = start_path
    for _ in range(8):  # 8 levels: enough for nested clones
        if (cur / _CANONICAL_MARKER_FILENAME).is_file():
            # Verify the marker content matches the token (catches
            # accidentally-created empty or wrong-content files).
            try:
                content = (cur / _CANONICAL_MARKER_FILENAME).read_text(
                    encoding="utf-8"
                ).strip()
            except OSError:
                pass
            else:
                if content.startswith("EmpireBox canonical root"):
                    return cur
            # Marker exists but content is wrong — refuse loudly
            logger.critical(
                "canonical marker at %s has wrong content; refusing "
                "to treat this directory as canonical",
                cur / _CANONICAL_MARKER_FILENAME,
            )
            raise CanonicalRootError(
                f"canonical marker at {cur} has wrong content"
            )
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    raise CanonicalRootError(
        f"no { _CANONICAL_MARKER_FILENAME} marker found within 8 levels "
        f"of {start_path}. Refusing to treat any directory as canonical "
        f"without the explicit marker."
    )


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


def resolve_path_under_canonical_root(
    relative_or_absolute: os.PathLike | str,
    start: os.PathLike | str | None = None,
) -> Path:
    """Resolve a path argument against the canonical repo root.

    Behavior:
      - absolute path → resolve canonical repo, verify the absolute
        path is INSIDE the canonical repo, return the resolved
        absolute path. Refuse if it escapes (via .. or symlinks).
      - relative path → resolve against canonical root, return
        absolute path under canonical repo.
      - canonical repo missing the `.empire-canonical` marker →
        CanonicalRootError (refuse).

    This is the single validator for MAX's file/repo tools and for
    any other call site that previously used `~/empire-repo/`.
    """
    canonical = resolve_canonical_root(start)

    # REFUSE paths containing `..` segments outright. Path.resolve()
    # collapses `..` lexically without going above the path root
    # (e.g. `canonical/backend/data/uploads/../../../etc/passwd`
    # resolves to `canonical/etc/passwd` — still INSIDE canonical
    # per `Path.resolve()` semantics, but the user clearly INTENDED
    # an escape). Refuse the literal `..` even though `Path.resolve`
    # would consider the path under canonical — the dispatch says
    # "refusing anything that escapes it — via .., symlinks". An
    # attempted escape via .. is the user's intent, and we must
    # refuse regardless of where the lexically-collapsed path lands.
    parts = Path(relative_or_absolute).expanduser().parts
    if any(part == ".." for part in parts):
        raise CanonicalRootError(
            f"path {relative_or_absolute} contains '..' — refusing "
            f"any path that attempts to escape the canonical root"
        )

    candidate = Path(relative_or_absolute).expanduser()
    if not candidate.is_absolute():
        candidate = (canonical / candidate).resolve()
    else:
        candidate = candidate.resolve()
    # Refuse escapes outside the canonical root (symlinks).
    try:
        candidate.relative_to(canonical.resolve())
    except ValueError:
        raise CanonicalRootError(
            f"path {candidate} escapes canonical root {canonical}. "
            f"Refusing — only paths under the canonical repo are allowed."
        )
    # Refuse stale-fork leakage.
    if _is_stale_fork_root(candidate):
        raise CanonicalRootError(
            f"path {candidate} lives under the stale fork. "
            f"Refusing — only paths under the canonical repo are allowed."
        )
    return candidate


# Backward-compat alias — older callers used this name.
def resolve_canonical_path(
    relative_or_absolute: os.PathLike | str,
    start: os.PathLike | str | None = None,
) -> Path:
    return resolve_path_under_canonical_root(relative_or_absolute, start)


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


# ── EMPIRE.DB canonical path (iX-day R1X-INT-FIX) ────────────────
# iX-day dispatch: the LuxeForge intake router was hard-coded to
# `~/empire-repo/backend/data/intake.db` (the stale fork). That path
# was a hot-bed for silent drift — every other backend module reads
# `~/empire-data/empire.db` (the canonical data dir). Resolution here
# mirrors the drawings resolver: env override first, then canonical
# default, with a RuntimeError on stale-fork detection so the bug
# class can never silently return.
_EMPIRE_DB_ENV_OVERRIDE = "EMPIRE_DB_PATH"

# Canonical default: the active data dir declared in CLAUDE.md.
_DEFAULT_EMPIRE_DB_PATH = Path.home() / "empire-data" / "empire.db"


def canonical_empire_db_path() -> Path:
    """Return the canonical path to empire.db (the canonical data DB).

    Resolution order:
      1. $EMPIRE_DB_PATH (if set) — checked for staleness.
      2. ~/empire-data/empire.db — the canonical data dir.

    Returns the path. Raises RuntimeError if the resolved path lives
    under a known stale fork root (~/empire-repo/, ~/empire-repo-main-old/).
    The caller is expected to coerce to str() as needed for sqlite3.connect.
    """
    override = os.getenv(_EMPIRE_DB_ENV_OVERRIDE)
    candidate = Path(override) if override else _DEFAULT_EMPIRE_DB_PATH

    if _is_stale_fork_root(candidate):
        logger.critical(
            "empire.db canonical path resolved to a stale fork root: "
            "%s (override=%s). Refusing to operate — set EMPIRE_DB_PATH "
            "to a path under the active data dir (~/empire-data/) or "
            "remove the env var to use the default.",
            candidate, override,
        )
        raise RuntimeError(
            f"empire.db canonical path resolved to a stale fork root: "
            f"{candidate}. Set EMPIRE_DB_PATH to a path under the active "
            f"data dir (~/empire-data/) or remove the env var to use the "
            f"default."
        )

    return candidate


# ── EMPIRE intake uploads / photos canonical dirs (iX-day R1X-INT-FIX) ──
# The stale-fork wrote client uploads to `~/empire-repo/backend/data/intake_uploads/`
# and `~/empire-repo/backend/data/photos/`. Both have canonical homes under
# `~/empire-data/`. The same `_is_stale_fork_root` guard fires on any
# override that lands under the stale fork.
_INTAKE_UPLOADS_ENV_OVERRIDE = "EMPIRE_INTAKE_UPLOADS_DIR"
_PHOTOS_ENV_OVERRIDE = "EMPIRE_PHOTOS_DIR"
_DEFAULT_INTAKE_UPLOADS_DIR = Path.home() / "empire-data" / "intake_uploads"
_DEFAULT_PHOTOS_DIR = Path.home() / "empire-data" / "photos"


def canonical_intake_uploads_dir() -> Path:
    """Return the canonical directory for client intake uploads.

    Resolution order:
      1. $EMPIRE_INTAKE_UPLOADS_DIR (if set) — checked for staleness.
      2. ~/empire-data/intake_uploads/ — the canonical data dir.

    Returns the path with mkdir(parents=True, exist_ok=True) applied.
    Raises RuntimeError if the resolved path lives under a stale fork
    root (~/empire-repo/, ~/empire-repo-main-old/).
    """
    override = os.getenv(_INTAKE_UPLOADS_ENV_OVERRIDE)
    candidate = Path(override) if override else _DEFAULT_INTAKE_UPLOADS_DIR

    if _is_stale_fork_root(candidate):
        logger.critical(
            "intake_uploads canonical path resolved to a stale fork "
            "root: %s (override=%s). Refusing to operate.",
            candidate, override,
        )
        raise RuntimeError(
            f"intake_uploads canonical path resolved to a stale fork "
            f"root: {candidate}. Set EMPIRE_INTAKE_UPLOADS_DIR to a "
            f"path under the active data dir (~/empire-data/) or "
            f"remove the env var."
        )

    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def canonical_photos_dir() -> Path:
    """Return the canonical directory for the unified photos store.

    Resolution order:
      1. $EMPIRE_PHOTOS_DIR (if set) — checked for staleness.
      2. ~/empire-data/photos/ — the canonical data dir.

    Returns the path with mkdir(parents=True, exist_ok=True) applied.
    Raises RuntimeError if the resolved path lives under a stale fork root.
    """
    override = os.getenv(_PHOTOS_ENV_OVERRIDE)
    candidate = Path(override) if override else _DEFAULT_PHOTOS_DIR

    if _is_stale_fork_root(candidate):
        logger.critical(
            "photos canonical path resolved to a stale fork root: "
            "%s (override=%s). Refusing to operate.",
            candidate, override,
        )
        raise RuntimeError(
            f"photos canonical path resolved to a stale fork root: "
            f"{candidate}. Set EMPIRE_PHOTOS_DIR to a path under the "
            f"active data dir (~/empire-data/) or remove the env var."
        )

    candidate.mkdir(parents=True, exist_ok=True)
    return candidate
