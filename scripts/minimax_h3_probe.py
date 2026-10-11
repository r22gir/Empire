#!/usr/bin/env python3
"""One-clip H3 probe: did plan quota move, or credit balance?

Default is dry-run (quota snapshot only, no clip). Pass --live to generate
exactly one short clip with the subscription key already in the environment.

Never prints the API key. Gift credits must not be spent silently — if the
plan bar is already at the hard-stop, the live probe refuses.

Docs conflict on whether H3 works with an M Plan subscription key. This
script reports what moved; it does not assume.
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
    parser.add_argument(
        "--live",
        action="store_true",
        help="Generate ONE clip. Refuses unless MINIMAX_H3_PROBE_LIVE=1.",
    )
    parser.add_argument("--prompt", default="A single silent test clip of a clock, AI-generated draft.")
    args = parser.parse_args(argv)

    if not os.getenv("MINIMAX_API_KEY"):
        print("MINIMAX_API_KEY is not set in the environment.", file=sys.stderr)
        return 2

    from app.services.minimax_quota import fetch_credits, fetch_remains, redact_secret
    from app.services.minimax_video import compare_snapshots, snapshot_quota

    before = snapshot_quota()
    report = {
        "mode": "live" if args.live else "dry-run",
        "before": before,
        "after": None,
        "compare": None,
        "generated": False,
        "key_logged": False,
    }
    print(_redact(json.dumps({"before": before}, indent=2)))

    if not args.live:
        print("dry-run: no clip generated. Re-run with --live and MINIMAX_H3_PROBE_LIVE=1 to spend one weekly clip.")
        return 0

    if (os.getenv("MINIMAX_H3_PROBE_LIVE") or "").strip() not in {"1", "true", "yes"}:
        print("refusing --live without MINIMAX_H3_PROBE_LIVE=1", file=sys.stderr)
        return 2

    from app.services.minimax_meter import plan_hard_stopped

    stop = plan_hard_stopped({"remains": fetch_remains(force=True), "credits": fetch_credits(force=True)})
    if stop:
        print(_redact(stop), file=sys.stderr)
        return 3

    os.environ.setdefault("MINIMAX_H3_ENABLED", "1")
    from app.services.minimax_video import approve, create_draft, generate_approved_clip

    draft = create_draft(args.prompt, edition="workroom", duration=5)
    approve(draft["id"], confirmed=True)
    try:
        import asyncio

        row = asyncio.run(generate_approved_clip(draft["id"]))
        report["generated"] = True
        report["approval_id"] = draft["id"]
        report["task_id"] = (row.get("result") or {}).get("task_id")
        report["ai_generated"] = True
        report["posted"] = False
    except Exception as exc:
        report["error"] = redact_secret(str(exc))
        print(_redact(json.dumps(report, indent=2)))
        return 1

    after = snapshot_quota()
    report["after"] = after
    report["compare"] = compare_snapshots(before, after)
    print(_redact(json.dumps(report, indent=2)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
