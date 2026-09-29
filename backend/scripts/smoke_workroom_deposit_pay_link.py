#!/usr/bin/env python3
"""Smoke: Workroom quote → deposit invoice → Stripe pay link, then double-click.

Uses a temporary database and a fake Stripe client inside
backend/tests/test_workroom_deposit_pay_link.py. It does not call live Stripe
and it does not treat https://studio.empirebox.store as reachable.

Command Center smoke on EmpireDell (Tailscale or on the box, port 3005).
Do not use the public host if it returns Cloudflare 521.

  http://<empire-dell-tailscale>:3005/?product=workroom&section=quotes
  http://<empire-dell-tailscale>:3005/?product=workroom&section=quotes&business=woodcraft
  http://<empire-dell-tailscale>:3005/?product=workroom&section=invoices

On the machine itself the same paths are http://127.0.0.1:3005/?product=workroom&section=quotes
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend") + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "backend/tests/test_workroom_deposit_pay_link.py",
    ]
    print("Workroom deposit pay-link smoke", flush=True)
    print("CC (Tailscale): http://<empire-dell>:3005/?product=workroom&section=quotes", flush=True)
    print("Public studio.empirebox.store is not assumed up.", flush=True)
    return subprocess.call(cmd, cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
