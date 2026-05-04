"""Secure Code Execution Tools for MAX (v10 Sandbox Only)
- Enforces ~/empire-repo-v10 path restriction
- Filters dangerous commands
- Logs all actions to audit trail
- Default dry-run mode, requires explicit confirmation for live execution
"""
import os
import re
import json
import subprocess
import difflib
from pathlib import Path
from datetime import datetime
from typing import Optional

V10_ROOT = Path.home() / "empire-repo-v10"
AUDIT_LOG = Path.home() / "empire-repo-v10" / "backend" / "data" / "logs" / "code_execution_audit.jsonl"

ALLOWED_COMMANDS = {
    "git", "python", "python3", "curl", "wget", "ls", "cat", "head", "tail",
    "grep", "find", "pytest", "uvicorn", "npm", "node", "echo", "touch", "mkdir", "pip"
}

DENIED_PATTERNS = [
    r"\brm\s+-rf\b", r"\bsudo\b", r"\bchmod\b", r"\bchown\b", r"\bdd\b",
    r"\bmkfs\b", r"\bformat\b", r"\bshutdown\b", r"\breboot\b", r">\s*/dev/",
    r"\bwget\s+.*\|.*sh\b", r"\bcurl\s+.*\|.*bash\b"
]

# Critical files that cannot be written (only read is allowed)
CRITICAL_FILES = {
    "tool_executor.py", "main.py", "system_prompt.py",
    "ai_router.py", "tool_safety.py", "tool_audit.py",
}


def validate_v10_path(path: str, read_only: bool = False) -> tuple[Path, str]:
    """Ensure path is within v10 repo. Returns (resolved_path, error_message)."""
    try:
        if not os.path.isabs(path):
            resolved = (V10_ROOT / path).resolve()
        else:
            resolved = Path(os.path.expanduser(path)).resolve()
    except Exception as e:
        return None, f"Cannot resolve path: {e}"

    v10_resolved = V10_ROOT.resolve()
    if not str(resolved).startswith(str(v10_resolved)):
        return None, f"Path escapes v10 sandbox: {path}"

    return resolved, ""


def is_command_safe(command: str) -> bool:
    """Check command against allowlist/denylist."""
    if not command:
        return False
    base_cmd = command.split()[0] if command.split() else ""
    if base_cmd not in ALLOWED_COMMANDS:
        return False
    for pattern in DENIED_PATTERNS:
        if re.search(pattern, command, re.I):
            return False
    return True


def log_audit(action: str, params: dict, result: dict, dry_run: bool):
    """Append to audit log."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "params": {k: v for k, v in params.items() if k != "_founder"},
        "result": result,
        "dry_run": dry_run,
    }
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Never fail on audit log errors


def v10_read_file(path: str, max_lines: int = 200) -> dict:
    """Read file content within v10 sandbox."""
    resolved, err = validate_v10_path(path, read_only=True)
    if err:
        return {"error": err}

    if not resolved.exists():
        return {"error": f"File not found: {path}"}

    try:
        content = resolved.read_text()
        lines = content.splitlines()
        return {
            "path": path,
            "content": "\n".join(lines[:max_lines]),
            "total_lines": len(lines),
            "truncated": len(lines) > max_lines,
            "v10_root": str(V10_ROOT),
        }
    except Exception as e:
        return {"error": str(e)}


def v10_write_file(path: str, content: str, mode: str = "overwrite", dry_run: bool = True, confirm: bool = False) -> dict:
    """Write file within v10 sandbox. Default dry-run — requires explicit dry_run=False AND confirm=True."""
    resolved, err = validate_v10_path(path, read_only=False)
    if err:
        return {"error": err}

    basename = os.path.basename(path)
    if basename in CRITICAL_FILES:
        return {
            "error": f"BLOCKED: {basename} is a critical system file. Use file_edit for modifications, or execute_command with git operations instead.",
            "dry_run": dry_run,
        }

    # Live mode requires explicit confirmation
    if not dry_run and not confirm:
        return {
            "error": "Live write requires explicit confirm=True alongside dry_run=False. This is a safety guard — you must explicitly confirm you want to modify the file.",
            "dry_run": dry_run,
        }

    log_audit("write_file", {"path": path, "content_len": len(content), "mode": mode}, {"status": "dry_run_preview"}, dry_run)

    if dry_run:
        return {
            "status": "dry_run",
            "path": path,
            "mode": mode,
            "bytes_to_write": len(content),
            "preview": content[:500] + ("..." if len(content) > 500 else ""),
            "v10_root": str(V10_ROOT),
            "instruction": "To write live, set dry_run=False and confirm=True",
        }

    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            with open(resolved, "a") as f:
                f.write("\n" + content)
        else:
            resolved.write_text(content)
        log_audit("write_file", {"path": path, "content_len": len(content), "mode": mode}, {"status": "written"}, False)
        return {
            "status": "written",
            "path": path,
            "mode": mode,
            "v10_root": str(V10_ROOT),
        }
    except Exception as e:
        return {"error": str(e)}


def v10_execute_command(command: str, timeout: int = 30, dry_run: bool = True, confirm: bool = False) -> dict:
    """Execute command in v10 sandbox. Default dry-run."""
    if not command:
        return {"error": "No command provided"}

    if not is_command_safe(command):
        return {"error": f"Command blocked by safety filter: {command}"}

    log_audit("execute_command", {"command": command, "timeout": timeout}, {"status": "dry_run"}, dry_run)

    if dry_run:
        return {
            "status": "dry_run",
            "command": command,
            "timeout": timeout,
            "v10_root": str(V10_ROOT),
            "instruction": "To execute live, set dry_run=False and confirm=True",
        }

    # Live execution requires explicit confirmation
    if not confirm:
        return {
            "error": "Live execution requires explicit confirm=True alongside dry_run=False. This is a safety guard.",
            "status": "dry_run",
            "command": command,
        }

    try:
        result = subprocess.run(
            ["bash", "-c", command],
            cwd=str(V10_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        log_audit("execute_command", {"command": command}, {"exit_code": result.returncode}, False)
        return {
            "status": "completed",
            "command": command,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:500],
            "returncode": result.returncode,
            "v10_root": str(V10_ROOT),
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out", "timeout": timeout}
    except Exception as e:
        return {"error": str(e)}


def v10_diff_preview(path: str, new_content: str) -> dict:
    """Show unified diff between current file and proposed changes."""
    resolved, err = validate_v10_path(path, read_only=True)
    if err:
        return {"error": err}

    if not resolved.exists():
        return {"error": f"File not found for diff: {path}"}

    try:
        current = resolved.read_text()
        diff = list(difflib.unified_diff(
            current.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3,
        ))
        return {
            "diff": "".join(diff),
            "lines_changed": len(diff),
            "path": path,
            "current_bytes": len(current),
            "new_bytes": len(new_content),
        }
    except Exception as e:
        return {"error": str(e)}