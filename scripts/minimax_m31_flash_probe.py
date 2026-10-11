#!/usr/bin/env python3
"""One tiny MiniMax-M3.1-Flash-Preview self-test.

Default is dry-run (no HTTP). Pass --live AND MINIMAX_M31_FLASH_PROBE=1
to make one max_tokens=1 ping. Uses the existing MINIMAX_API_KEY.

Never prints the API key. Clear error if the plan does not include
MiniMax-M3.1-Flash-Preview (M Plan / MiniMax Code only).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _redact(text: str) -> str:
    key = os.getenv("MINIMAX_API_KEY") or ""
    out = str(text or "")
    if key and len(key) >= 6:
        out = out.replace(key, "[KEY_REDACTED]")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="One tiny chat call.")
    args = parser.parse_args(argv)

    from app.services.minimax_m31_flash import probe_m31_flash

    if args.live and (os.getenv("MINIMAX_M31_FLASH_PROBE") or "").strip().lower() not in {"1", "true", "yes", "on"}:
        print("refusing --live without MINIMAX_M31_FLASH_PROBE=1", file=sys.stderr)
        return 2

    report = probe_m31_flash(live=bool(args.live))
    print(_redact(json.dumps(report, indent=2)))
    if not report.get("ok"):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
