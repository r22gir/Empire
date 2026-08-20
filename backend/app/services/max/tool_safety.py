"""Tool Safety — path and command validation for MAX tool execution.

All tool operations that touch the filesystem or run shell commands MUST
pass through these validators first. Blocks dangerous paths and commands.

H57 PHASE 3 (2026-08-19): Path validation now resolves against the
canonical repo marker (`canonical_path.resolve_path_under_canonical_root`)
— NOT a hardcoded `~/empire-repo/` allow-list. The stale fork is
UNREACHABLE: any path that resolves under `~/empire-repo/` is refused
because the resolver explicitly checks for it. The previous `ALLOWED_ROOTS`
list contained `~/empire-repo/` (the stale fork root) as an allowed path —
that was the bug.
"""
import os
import re
import logging

logger = logging.getLogger("max.tool_safety")

# ── Path Safety ──────────────────────────────────────────────────

# Relative-path / write sinks that the canonical-path resolver permits
# alongside the canonical repo. None of these are the stale fork.
# All paths under the canonical repo are allowed by default; these are
# OUTSIDE-CANONICAL exemptions that tools need (e.g. /tmp for tests).
_NON_CANONICAL_EXEMPTIONS = [
    "/tmp",
    "/data/empire/self_heal_tests",
]

# Critical system files that require extra caution for writes
CRITICAL_FILES = [
    "tool_executor.py", "main.py", "system_prompt.py",
    "ai_router.py", "tool_safety.py", "tool_audit.py",
]


def is_critical_file(path: str) -> bool:
    """Check if a path points to a critical system file."""
    basename = os.path.basename(path)
    return basename in CRITICAL_FILES


def validate_path(path: str) -> tuple[bool, str]:
    """Validate that a file path is within allowed boundaries.

    Per H57 Phase 3 (2026-08-19), this delegates to the single
    canonical-path resolver in canonical_path. The resolver:
      1. Verifies the `.empire-canonical` marker is present (refuses
         if missing — the active repo is identified by the marker,
         not by a hardcoded path string).
      2. Refuses any path that resolves under `~/empire-repo/` (the
         stale fork — the previous ALLOWED_ROOTS bug).
      3. Refuses any path that escapes the canonical root via `..`
         or symlinks.
      4. Permits paths under the canonical repo, plus the
         non-canonical exemptions (e.g. /tmp for tests).

    Resolves symlinks to prevent escapes.
    Returns (allowed: bool, reason: str).
    """
    try:
        from app.services.drawing.canonical_path import (
            resolve_path_under_canonical_root,
            CanonicalRootError,
        )
    except ImportError as exc:
        return False, f"canonical_path import failed: {exc}"

    try:
        resolve_path_under_canonical_root(path)
    except CanonicalRootError as exc:
        return False, str(exc)
    except Exception as exc:
        return False, f"canonical-path resolver failed: {exc}"

    # Non-canonical exemptions (e.g. /tmp) are explicitly permitted
    # OUTSIDE the canonical resolver — they're sandboxed paths the
    # canonical marker does not cover.
    try:
        resolved = os.path.realpath(os.path.expanduser(path))
    except Exception as e:
        return False, f"Cannot resolve path: {e}"
    for exemption in _NON_CANONICAL_EXEMPTIONS:
        if resolved.startswith(exemption):
            return True, "OK"
    return True, "OK"


# ── Command Safety ───────────────────────────────────────────────

BLOCKED_COMMANDS = [
    r"rm\s+-rf\s+/\s",
    r"rm\s+-rf\s+~\s",
    r"rm\s+-rf\s+\$HOME",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\bsensors-detect\b",
    r"\bchmod\s+777\b",
    r"curl\s.*\|\s*bash",
    r"curl\s.*\|\s*sh",
    r"wget\s.*\|\s*bash",
    r"wget\s.*\|\s*sh",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\binit\s+[0-6]",
]

# pkill -f is allowed ONLY for these targeted process names
ALLOWED_PKILL_TARGETS = [
    "uvicorn", "next", "openclaw", "ollama",
    "server.py", "recoveryforge", "ollama_bulk_classify",
]


def validate_command(cmd: str) -> tuple[bool, str]:
    """Validate that a shell command is safe to execute.

    Returns (allowed: bool, reason: str).
    """
    if not cmd or not cmd.strip():
        return False, "Empty command"

    cmd_lower = cmd.lower().strip()

    # Check blocked patterns
    for pattern in BLOCKED_COMMANDS:
        if re.search(pattern, cmd_lower):
            return False, f"Blocked command pattern: {pattern}"

    # Check pkill -f usage — must target a specific allowed process
    if "pkill" in cmd_lower and "-f" in cmd_lower:
        has_allowed_target = any(
            target in cmd_lower for target in ALLOWED_PKILL_TARGETS
        )
        if not has_allowed_target:
            return False, (
                f"pkill -f requires a specific target. "
                f"Allowed: {', '.join(ALLOWED_PKILL_TARGETS)}"
            )

    return True, "OK"
