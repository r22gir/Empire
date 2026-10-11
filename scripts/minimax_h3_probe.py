#!/usr/bin/env python3
"""One-clip H3 probe: did plan quota move, or credit balance?

Default is dry-run (quota snapshot only, no clip). Pass --live to generate
exactly one short Pay-as-you-go H3 clip with the key already in the environment.

Never prints the API key. Gift credits must not be spent silently — if a
hard-stop is active (plan bar or remains unread for video), the live probe
refuses. A subscription-key reject is reported (key redacted) and never retried.

``generated: true`` means a real clip file was downloaded. An approval_id
without a task_id or file is a failure.

    MINIMAX_H3_MODEL=MiniMax-H3 MINIMAX_H3_PROBE_LIVE=1 \
      scripts/minimax_h3_probe.py --live
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
    from app.services.minimax_video import H3_DEFAULT_RATIO, H3_DEFAULT_RESOLUTION, H3_PROBE_PROMPT

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Generate ONE clip. Refuses unless MINIMAX_H3_PROBE_LIVE=1.",
    )
    parser.add_argument("--prompt", default=H3_PROBE_PROMPT)
    args = parser.parse_args(argv)

    if not os.getenv("MINIMAX_API_KEY"):
        print("MINIMAX_API_KEY is not set in the environment.", file=sys.stderr)
        return 2

    from app.services.minimax_quota import redact_secret
    from app.services.minimax_video import (
        clip_was_produced,
        compare_snapshots,
        estimate_h3_cost,
        snapshot_quota,
    )

    before = snapshot_quota()
    model = (os.getenv("MINIMAX_H3_MODEL") or "MiniMax-H3").strip()
    cost = estimate_h3_cost(
        model=model,
        duration=4,
        resolution=H3_DEFAULT_RESOLUTION,
    )
    report = {
        "mode": "live" if args.live else "dry-run",
        "before": before,
        "after": None,
        "compare": None,
        "generated": False,
        "task_id": None,
        "clip_path": None,
        "posted": False,
        "key_logged": False,
        "cost_estimate": cost,
        "credits_readable": bool(before.get("credits_readable")),
    }
    if not report["credits_readable"]:
        report["credits_note"] = (
            before.get("credits_reason")
            or "credit balance endpoint could not be read; recorded local estimate"
        )
        report["local_estimate"] = {
            "local_plan_used_pct": before.get("local_plan_used_pct"),
            "paygo_usd": cost["usd"],
        }
    print(_redact(json.dumps({"before": before, "cost_estimate": cost}, indent=2)))

    if not args.live:
        print(
            "dry-run: no clip generated. Re-run with --live and "
            "MINIMAX_H3_PROBE_LIVE=1 to spend one 4s 768P 16:9 clip."
        )
        return 0

    if (os.getenv("MINIMAX_H3_PROBE_LIVE") or "").strip() not in {"1", "true", "yes"}:
        print("refusing --live without MINIMAX_H3_PROBE_LIVE=1", file=sys.stderr)
        return 2

    from app.services.minimax_meter import plan_hard_stopped

    # Same snapshot reserve() uses (honors MINIMAX_REMAINS_STUB / cache).
    stop = plan_hard_stopped(kind="video", edition="workroom")
    if stop:
        report["error"] = redact_secret(stop)
        report["hard_stop"] = True
        print(_redact(json.dumps(report, indent=2)), file=sys.stderr)
        return 3

    os.environ.setdefault("MINIMAX_H3_ENABLED", "1")
    from app.services.minimax_video import (
        SubscriptionKeyRejected,
        approve,
        create_draft,
        generate_approved_clip,
    )

    draft = create_draft(
        args.prompt,
        edition="workroom",
        duration=4,
        resolution=H3_DEFAULT_RESOLUTION,
        ratio=H3_DEFAULT_RATIO,
    )
    approve(draft["id"], confirmed=True)
    report["approval_id"] = draft["id"]
    try:
        import asyncio

        row = asyncio.run(generate_approved_clip(draft["id"], caller_edition="workroom"))
        result = row.get("result") or {}
        report["task_id"] = result.get("task_id")
        report["clip_path"] = result.get("clip_path")
        report["clip_bytes"] = result.get("clip_bytes")
        report["ai_generated"] = True
        report["posted"] = False
        report["generated"] = clip_was_produced(row)
        if result.get("cost_estimate"):
            report["cost_estimate"] = result["cost_estimate"]
        if not report["generated"]:
            report["error"] = redact_secret(
                result.get("error")
                or f"generate returned without a downloaded clip (task_id={report['task_id']})"
            )
            after = snapshot_quota()
            report["after"] = after
            report["compare"] = compare_snapshots(before, after)
            print(_redact(json.dumps(report, indent=2)))
            return 1
    except SubscriptionKeyRejected as exc:
        report["error"] = redact_secret(str(exc))
        report["subscription_rejected"] = True
        after = snapshot_quota()
        report["after"] = after
        report["compare"] = compare_snapshots(before, after)
        print(_redact(json.dumps(report, indent=2)))
        return 1
    except Exception as exc:
        report["error"] = redact_secret(str(exc))
        after = snapshot_quota()
        report["after"] = after
        report["compare"] = compare_snapshots(before, after)
        print(_redact(json.dumps(report, indent=2)))
        return 1

    after = snapshot_quota()
    report["after"] = after
    report["compare"] = compare_snapshots(before, after)
    if not after.get("credits_readable"):
        report["credits_note"] = (
            after.get("credits_reason")
            or "credit balance endpoint could not be read; recorded local estimate"
        )
        report["local_estimate"] = {
            "local_plan_used_pct_before": before.get("local_plan_used_pct"),
            "local_plan_used_pct_after": after.get("local_plan_used_pct"),
            "paygo_usd": report["cost_estimate"]["usd"],
        }
    print(_redact(json.dumps(report, indent=2)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
