"""Tool Safety — path and command validation for MAX tool execution.

All tool operations that touch the filesystem or run shell commands MUST
pass through these validators first. Blocks dangerous paths and commands.
"""
import os
import re
import logging

logger = logging.getLogger("max.tool_safety")

# ── Path Safety ──────────────────────────────────────────────────

ALLOWED_ROOTS = [
    os.path.expanduser("~/empire-repo"),
    "/tmp",
    "/data/empire/self_heal_tests",
]

BLOCKED_PATHS = [
    "/etc/", "/usr/", "/bin/", "/sbin/",
    "/boot/", "/proc/", "/sys/", "/dev/",
    os.path.expanduser("~/.ssh/"),
    os.path.expanduser("~/.gnupg/"),
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

    Resolves symlinks to prevent escapes.
    Returns (allowed: bool, reason: str).
    """
    try:
        resolved = os.path.realpath(os.path.expanduser(path))
    except Exception as e:
        return False, f"Cannot resolve path: {e}"

    # Check blocked paths first
    for blocked in BLOCKED_PATHS:
        if resolved.startswith(blocked):
            return False, f"Path blocked: {blocked} is a protected system directory"

    # Check allowed roots
    for root in ALLOWED_ROOTS:
        real_root = os.path.realpath(root)
        if resolved.startswith(real_root):
            return True, "OK"

    return False, f"Path outside allowed directories. Allowed: {', '.join(ALLOWED_ROOTS)}"


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
    # EmpireDell GPU stability lock — NVIDIA 470 / kernel 6.8.0-31 is the known-good stack
    r"\bapt\s+autoremove\b",
    r"\bapt\s+upgrade\b",
    r"\bapt\s+full-upgrade\b",
    r"\bapt-get\s+dist-upgrade\b",
    r"\bapt\s+remove\b.*\s+nvidia",
    r"\bapt\s+purge\b.*\s+nvidia",
    r"\bapt\s+install\b.*\s+nvidia-driver",
    r"\bapt\s+install\b.*\s+nvidia-dkms",
    r"\bapt\s+install\b.*\s+nvidia-kernel-source",
    r"\bapt\s+install\b.*\s+nvidia-kernel-common",
    r"\bapt\s+install\b.*\s+linux-generic-hwe",
    r"\bapt\s+install\b.*\s+linux-image-generic-hwe",
    r"\bapt\s+install\b.*\s+linux-headers-generic-hwe",
    r"\bubuntu-drivers\s+autoinstall\b",
    r"\bapt-mark\s+unhold\b",
    r"\bupdate-initramfs\s+-u\b",
    r"\bgrub-set-default\b",
    r"\bgrub-install\b",
    r"\bdkms\s+remove\b",
    r"\bdkms\s+add\b",
    r"\bdkms\s+build\b",
    r"\bmodprobe\s+-r\s+nvidia\b",
    r"\bnvidia-smi\s+--reset\b",
    r"\bnvidia-settings\b",
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
