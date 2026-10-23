"""Studio frozen-suite gate for Night Lab / self-improvement / auto-fix.

Any self-improvement or auto-fix change must pass the frozen suite TWICE
before it is kept. One fail → reject and revert. Mock data only; nothing
is sent (email / WhatsApp / SMS / Telegram).

Clear log line (yes/no):
  STUDIO_FROZEN_GATE: YES  passes=2/2  ...
  STUDIO_FROZEN_GATE: NO   passes=1/2  ...
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("max.studio_frozen_gate")

GATE_NAME = "STUDIO_FROZEN_GATE"
REQUIRED_PASSES = 2
FROZEN_SUITE = "tests/test_studio_frozen_gate.py"
BACKEND_ROOT = Path(__file__).resolve().parents[3]

OUTBOUND_KILL = (
    "SENDGRID_API_KEY",
    "SMTP_PASSWORD",
    "SMTP_HOST",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "WHATSAPP_TOKEN",
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "TELEGRAM_BOT_TOKEN",
    "RESEND_API_KEY",
)


def frozen_suite_path() -> Path:
    return BACKEND_ROOT / FROZEN_SUITE


def frozen_mutation_ok() -> bool:
    """Optional demo hook. Default is clean. A 'bad' mock change flips this."""
    return (os.getenv("STUDIO_FROZEN_MUTATION") or "clean").strip().lower() in {
        "clean", "good", "ok", "",
    }


def _isolated_env(base: Optional[dict[str, str]] = None) -> dict[str, str]:
    env = dict(base if base is not None else os.environ)
    env["EMPIRE_OUTBOUND_DISABLED"] = "1"
    env["EMPIRE_ALLOW_OUTBOUND"] = "0"
    env["EMPIRE_EDITION"] = env.get("EMPIRE_EDITION") or "studio"
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(BACKEND_ROOT), env.get("PYTHONPATH") or "") if p
    )
    for key in OUTBOUND_KILL:
        env[key] = ""
    return env


def _run_pytest_once(
    *,
    env: Optional[dict[str, str]] = None,
    extra_args: Optional[list[str]] = None,
    timeout: int = 120,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--tb=line",
        str(frozen_suite_path()),
    ]
    if extra_args:
        cmd.extend(extra_args)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(BACKEND_ROOT),
            env=_isolated_env(env),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "output": out[-8000:],
            "cmd": cmd,
        }
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + "\n" + (exc.stderr or "")
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return {
            "ok": False,
            "returncode": 124,
            "output": f"TIMEOUT\n{out}"[-8000:],
            "cmd": cmd,
        }


def format_gate_log_line(
    *,
    keep: bool,
    passes: int,
    required: int = REQUIRED_PASSES,
    reason: str = "",
) -> str:
    verdict = "YES" if keep else "NO"
    extra = f"  {reason}" if reason else ""
    return f"{GATE_NAME}: {verdict}  passes={passes}/{required}{extra}"


def evaluate_studio_frozen_gate(
    *,
    env: Optional[dict[str, str]] = None,
    extra_args: Optional[list[str]] = None,
    required_passes: int = REQUIRED_PASSES,
    runner: Optional[Callable[..., dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Run the frozen suite ``required_passes`` times. Keep only if every run passes.

    Returns a yes/no decision. Never sends outbound messages.
    """
    run = runner or _run_pytest_once
    runs: list[dict[str, Any]] = []
    for i in range(max(1, required_passes)):
        result = run(env=env, extra_args=extra_args)
        result["pass_index"] = i + 1
        runs.append(result)
        if not result.get("ok"):
            break

    passes = sum(1 for r in runs if r.get("ok"))
    keep = passes >= required_passes and all(r.get("ok") for r in runs)
    reason = ""
    if keep:
        reason = "frozen suite green twice — change may be kept"
    elif passes == 0:
        reason = "frozen suite failed on first pass — change rejected"
    else:
        reason = f"frozen suite failed on pass {passes + 1} — change rejected"
    log_line = format_gate_log_line(keep=keep, passes=passes, required=required_passes, reason=reason)
    if keep:
        logger.info(log_line)
    else:
        logger.warning(log_line)
    return {
        "gate": GATE_NAME,
        "keep": keep,
        "verdict": "YES" if keep else "NO",
        "log_line": log_line,
        "passes": passes,
        "required_passes": required_passes,
        "runs": runs,
        "outbound": False,
        "suite": FROZEN_SUITE,
        "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def decide_keep_change(
    *,
    apply_fn: Optional[Callable[[], Any]] = None,
    revert_fn: Optional[Callable[[], Any]] = None,
    env: Optional[dict[str, str]] = None,
    extra_args: Optional[list[str]] = None,
    runner: Optional[Callable[..., dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Apply a change, require two green frozen-suite passes, else revert.

    Used by Night Lab / self-heal / maintenance auto-fix. The change is
    kept only when the gate returns YES.
    """
    applied = False
    if apply_fn is not None:
        apply_fn()
        applied = True
    decision = evaluate_studio_frozen_gate(env=env, extra_args=extra_args, runner=runner)
    if decision["keep"]:
        decision["kept"] = True
        decision["reverted"] = False
        return decision
    if applied and revert_fn is not None:
        revert_fn()
        decision["reverted"] = True
    else:
        decision["reverted"] = False
    decision["kept"] = False
    return decision
