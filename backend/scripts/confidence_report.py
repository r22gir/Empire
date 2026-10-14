#!/usr/bin/env python3
"""Print a week of Max shadow-confidence scores vs founder corrections.

Never sends WhatsApp / email / SMS. Never writes live chats.
Optional --feed files draft improvements (proposed only, never approved).

  python3 backend/scripts/confidence_report.py
  python3 backend/scripts/confidence_report.py --days 7 --feed
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow confidence weekly report")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument(
        "--feed",
        action="store_true",
        help="File unique low-score cases as proposed improvements (never approve)",
    )
    args = parser.parse_args()
    os.environ.setdefault("MAX_CONFIDENCE_GATE", "shadow")
    from app.services.max.confidence import feed_low_scores_to_improvements, week_report

    report = week_report(args.days)
    if args.feed:
        report["filed"] = feed_low_scores_to_improvements(args.days)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
