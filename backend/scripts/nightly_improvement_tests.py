#!/usr/bin/env python3
"""Nightly isolated test run that files failures as Max 'fix' improvements.

Documented timer: 2:30 AM America/New_York (see deploy/systemd/empire-nightly-improvements.timer).
NOT auto-installed. Enable on the Dell with the steps in docs/max/MAX_SELF_IMPROVEMENT_LOOP.md.

Hard rules:
  * Isolated temp data only (never live empire.db / ~/empire-data).
  * Email / WhatsApp / SMS / Telegram forced off. Nothing is sent.
  * No live-data writes. No amp/maxine code path.
  * Failures become kind=fix improvements (proposed). They are NOT auto-approved.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "empire-command-center"
LOG_DIR = Path(os.getenv("MAX_IMPROVE_NIGHTLY_LOG_DIR") or (Path.home() / "empire-data" / "logs"))

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


def _force_outbound_off(env: dict[str, str]) -> None:
    env["EMPIRE_OUTBOUND_DISABLED"] = "1"
    env["EMPIRE_ALLOW_OUTBOUND"] = "0"
    env["SOCIALFORGE_ALLOW_LIVE_PUBLISH"] = "0"
    env["APOSTAPP_ALLOW_CLIENT_EMAIL_SEND"] = "0"
    env["MINIMAX_FAMILY_TTS"] = "0"
    env["MINIMAX_H3_ENABLED"] = "0"
    env["WHATSAPP_CALLING_ENABLED"] = "0"
    for key in OUTBOUND_KILL:
        env.pop(key, None)
        env[key] = ""


def _isolated_env(tmp: Path) -> dict[str, str]:
    env = os.environ.copy()
    data = tmp / "data"
    data.mkdir(parents=True, exist_ok=True)
    env["EMPIRE_DATA_DIR"] = str(data)
    env["EMPIRE_BRAIN_DIR"] = str(data / "brain")
    env["EMPIRE_TASK_DB"] = str(data / "empire.db")
    env["EMPIRE_DB_PATH"] = str(data / "empire.db")
    env["EMPIRE_DB"] = str(data / "empire.db")
    env["EMPIRE_PHOTOS_DIR"] = str(data / "photos")
    env["MAX_IMPROVE_SPEC_DIR"] = str(data / "improvements")
    env["MINIMAX_METER_DIR"] = str(data / "minimax-meter")
    env["EMPIRE_EDITION"] = "studio"
    _force_outbound_off(env)
    return env


def _run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: int) -> dict:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (p.stdout or "") + "\n" + (p.stderr or "")
        return {
            "cmd": cmd,
            "returncode": p.returncode,
            "ok": p.returncode == 0,
            "output": out[-12000:],
        }
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + "\n" + (exc.stderr or "")
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return {"cmd": cmd, "returncode": 124, "ok": False, "output": f"TIMEOUT\n{out}"[-12000:]}


def _parse_pytest_failures(text: str) -> list[str]:
    names = []
    for line in (text or "").splitlines():
        m = re.search(r"FAILED\s+(\S+)", line)
        if m:
            names.append(m.group(1))
        m = re.search(r"^(\S+::\S+)\s+FAILED", line)
        if m:
            names.append(m.group(1))
    # unique, keep order
    seen = set()
    out = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _parse_node_failures(text: str) -> list[str]:
    names = []
    for line in (text or "").splitlines():
        m = re.search(r"not ok \d+ (.+)", line)
        if m:
            names.append(m.group(1).strip())
        m = re.search(r"^#\s+fail\s+\d+", line)
        if m and "node" not in names:
            pass
    seen = set()
    out = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _file_fix(title: str, problem: str, proposed: str) -> dict:
    from app.services.max import improvements as imp

    existing = imp.list_requests()
    for item in existing.get("items") or []:
        if item.get("title") == title and item.get("status") in (
            "proposed", "approved", "planning", "awaiting_build", "pr_open",
        ):
            return {"deduped": True, "id": item["id"], "title": title}
    req = imp.create_request(
        title=title[:200],
        problem=problem[:4000],
        proposed_change=proposed[:2000],
        affected_modules=["tests"],
        risk="medium",
        acceptance="Nightly suite is green in isolated temp data. No outbound messages.",
        requested_via="nightly",
        kind="fix",
    )
    return {"deduped": False, "id": req["id"], "title": req["title"]}


def run_nightly(*, dry_run: bool = False, full: bool = False) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="empire_nightly_imp_"))
    env = _isolated_env(tmp)
    backend_cmd = [sys.executable, "-m", "pytest", "-q", "--tb=line"]
    if full or (os.getenv("MAX_IMPROVE_NIGHTLY_FULL") or "").strip() in {"1", "true", "yes"}:
        backend_cmd.append(str(BACKEND / "tests"))
    else:
        default = os.getenv(
            "MAX_IMPROVE_NIGHTLY_PYTEST",
            "tests/test_growth.py tests/test_improvement_loop.py tests/test_minimax_meter.py tests/test_live_data_firewall.py",
        )
        backend_cmd.extend(default.split())

    frontend_cmd = [
        "node",
        "--experimental-strip-types",
        "--test",
        "app/lib",
        "app/components",
    ]

    results = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "tmp": str(tmp),
        "outbound": False,
        "dry_run": dry_run,
        "backend": None,
        "frontend": None,
        "filed": [],
        "merged": False,
        "deployed": False,
    }

    results["backend"] = _run(backend_cmd, BACKEND, env, timeout=int(os.getenv("MAX_IMPROVE_NIGHTLY_BACKEND_TIMEOUT", "900")))
    results["frontend"] = _run(frontend_cmd, FRONTEND, env, timeout=int(os.getenv("MAX_IMPROVE_NIGHTLY_FRONTEND_TIMEOUT", "300")))

    failures = []
    for name in _parse_pytest_failures(results["backend"]["output"]):
        failures.append(("backend", name, results["backend"]["output"][-1500:]))
    if not results["backend"]["ok"] and not failures:
        failures.append(("backend", "pytest-suite", results["backend"]["output"][-1500:]))
    for name in _parse_node_failures(results["frontend"]["output"]):
        failures.append(("frontend", name, results["frontend"]["output"][-1500:]))
    if not results["frontend"]["ok"] and not _parse_node_failures(results["frontend"]["output"]):
        failures.append(("frontend", "node-test-suite", results["frontend"]["output"][-1500:]))

    if not dry_run:
        # File into the LIVE task DB only if the operator pointed EMPIRE_TASK_DB
        # at the real box. The isolated env above is for the suite itself.
        # Filing uses the process env (Dell) so Rafael sees the cards in Studio.
        os.environ.setdefault("EMPIRE_OUTBOUND_DISABLED", "1")
        sys.path.insert(0, str(BACKEND))
        for suite, name, excerpt in failures:
            title = f"Nightly fix: {suite} {name}"[:200]
            results["filed"].append(
                _file_fix(
                    title,
                    f"Nightly isolated suite failed: {name}\n\n```\n{excerpt}\n```",
                    f"Diagnose and fix {name} so the isolated nightly {suite} suite passes. "
                    "No live-data writes. No outbound messages. Draft PR only.",
                )
            )

    results["failed_count"] = len(failures)
    results["ok"] = results["backend"]["ok"] and results["frontend"]["ok"]
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        (LOG_DIR / "nightly_improvements.json").write_text(json.dumps(results, indent=2)[:20000])
    except Exception:
        pass
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Isolated nightly tests → fix improvements")
    ap.add_argument("--dry-run", action="store_true", help="Run tests; do not file improvements")
    ap.add_argument("--full", action="store_true", help="Run the entire backend/tests tree")
    args = ap.parse_args()
    res = run_nightly(dry_run=args.dry_run, full=args.full)
    print(json.dumps({k: res[k] for k in ("ok", "failed_count", "filed", "dry_run", "tmp") if k in res}, indent=2))
    print("backend ok=", res["backend"]["ok"], "frontend ok=", res["frontend"]["ok"])
    sys.exit(0 if res["ok"] else 1)
