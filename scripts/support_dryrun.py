#!/usr/bin/env python3
"""CLI: isolated Empire support dry-run (Luna / tickets / Pedir ayuda / Rafael notice).

Never sends email, WhatsApp, SMS, or Telegram. Prints PASS/FAIL per step.
Exit 0 when support is working, 1 otherwise.

  python3 scripts/support_dryrun.py
  python3 scripts/support_dryrun.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    parser.add_argument("--edition", default=None, help="Override EMPIRE_EDITION for the report label.")
    args = parser.parse_args(argv)

    from app.services.support_dryrun import format_steps_text, run_support_dryrun

    report = run_support_dryrun(edition=args.edition)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_steps_text(report))
    return 0 if report.support_working else 1


if __name__ == "__main__":
    sys.exit(main())
