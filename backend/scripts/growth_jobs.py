#!/usr/bin/env python3
"""
Scheduled growth jobs on the Dell (systemd user timers, see deploy/systemd/empire-growth-*.timer).

  growth_jobs.py brief   [--dry-run]   weekdays 7:15 AM ET: reconcile paid deposits -> won, draft social
                                        proof for finished jobs, then send the morning brief to Rafael's
                                        Telegram chat (TELEGRAM_FOUNDER_CHAT_ID only).
  growth_jobs.py weekly  [--dry-run]   Mondays 6:00 AM ET: prospect searches for the standard targets in
                                        the DMV, free Place Details (website/phone, free tier only) and free
                                        contact lookup on the best new prospects. No outreach is sent.

Approved by Rafael on Oct 4, 2026. The brief is the only outbound message and it goes to Rafael only.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

LOG_DIR = Path.home() / "empire-data" / "logs"
STATE = Path.home() / "empire-data" / "growth_jobs_state.json"
WEEKLY_TARGETS = [("workroom", "interior designers"), ("workroom", "general contractors remodeling"),
                  ("workroom", "home stagers"), ("workroom", "boutique hotels")]


def _log(msg: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line)
    with open(LOG_DIR / "growth_jobs.log", "a") as f:
        f.write(line + "\n")


def _state(key: str, value: dict):
    try:
        data = json.loads(STATE.read_text()) if STATE.exists() else {}
    except Exception:
        data = {}
    data[key] = {"at": datetime.now().isoformat(timespec="seconds"), **value}
    STATE.write_text(json.dumps(data, indent=1, default=str))


async def _send_founder(text: str) -> bool:
    from app.services.max.telegram_bot import TelegramBot
    bot = TelegramBot()
    if not bot.is_configured:
        _log("telegram not configured; brief not sent")
        return False
    # Rafael's chat only: explicit founder chat id, never another chat.
    return await bot.send_message(text, chat_id=bot.founder_chat_id)


def run_brief(dry_run: bool) -> dict:
    from app.services.leadforge import growth
    rec = growth.reconcile_paid_deposits()
    sp = growth.scan_completed_jobs(days=14)
    text = growth.morning_brief_text(limit=5)
    sent = False
    if not dry_run:
        sent = asyncio.run(_send_founder(text))
    res = {"deposits_marked_won": len(rec["marked_won"]), "social_proof_drafted": len(sp["drafted"]),
           "sent": sent, "dry_run": dry_run, "chars": len(text)}
    _log(f"brief {json.dumps(res)}")
    _state("brief", res)
    if dry_run:
        print("\n" + text)
    return res


def run_weekly(dry_run: bool) -> dict:
    from app.services.leadforge.prospect_engine import run_prospect_search
    from app.services.leadforge import place_details
    from app.services.leadforge.contact_enrich import enrich_prospects
    from app.services.leadforge.prospect_ops import top_prospects
    out = {"searches": [], "dry_run": dry_run}
    if dry_run:
        out["would_search"] = WEEKLY_TARGETS
        print(json.dumps(out, indent=1))
        return out
    for unit, target in WEEKLY_TARGETS:
        try:
            r = asyncio.run(run_prospect_search(unit, "DMV", target))
            out["searches"].append({"target": target, "new": r.get("inserted_count"), "ok": r.get("success"),
                                    "failed": r.get("providers_failed")})
        except Exception as e:
            out["searches"].append({"target": target, "error": str(e)[:200]})
    pd = place_details.enrich(limit=60, allow_paid=False)
    out["place_details"] = {k: pd.get(k) for k in ("status", "processed", "filled_website", "filled_phone", "calls", "free_left")}
    ids = [p["id"] for p in top_prospects(limit=15, days=8, exclude_pipeline=True) if not p.get("is_directory_page")]
    if ids:
        er = asyncio.run(enrich_prospects(ids, discover_websites=False))
        out["contact_lookup"] = {k: er.get(k) for k in ("processed", "found", "skipped") if k in er} or {"ids": len(ids)}
    _log(f"weekly {json.dumps(out, default=str)[:2000]}")
    _state("weekly", out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("job", choices=["brief", "weekly"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    (run_brief if a.job == "brief" else run_weekly)(a.dry_run)
