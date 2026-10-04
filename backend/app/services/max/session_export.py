"""Daily export of Rafael's Max sessions for Chief e review.

Output (one folder per America/New_York date):

  ~/empire-data/max-sessions/YYYY-MM-DD/
      <HHMM>_<channel>_<session8>.jsonl   one line per turn (header line first)
      <HHMM>_<channel>_<session8>.md      same session, readable
      images/                             every image/file Rafael sent that day
      summary.json                        counts + review flags

Sources, in order of preference per session:
  1. max_session_journal.db (full turns, tool summaries, archived images)
  2. unified_messages.db (legacy rows written before the journal existed,
     or turns the journal missed) — images resolved from the upload dirs
     and archived on the way through.

Main studio only. The exporter refuses to run inside a family edition
(EMPIRE_EDITION set, or a data dir under /data/amp or /data/maxine) and
reads only rows stamped edition='main'.

CLI:
    cd ~/empire-repo-main/backend
    venv/bin/python scripts/export_max_sessions.py --date 2026-10-04
API:
    POST /api/v1/max/sessions/export?date=2026-10-04
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import date, datetime, time, timedelta, timezone
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.services.max import session_journal as sj

STUDIO_CHANNELS = ["web_chat", "web", "web_cc", "dashboard", "command_center", "mobile_browser", "studio_browser"]
EXPORT_CHANNELS = STUDIO_CHANNELS + ["telegram", "voice", "whatsapp"]
FAMILY_MARKERS = ("/data/amp", "/data/maxine", "empire-amp", "empire-maxine")

REFUSAL_RE = re.compile(
    r"(I can['’]t help with that request|I (?:can['’]t|cannot|won['’]t) (?:help|assist) with|"
    r"I must decline|I['’]m not (?:allowed|permitted) to|not authori[sz]ed to|requires founder (?:PIN|approval)|"
    r"I (?:can['’]t|cannot) do that|no puedo ayudar)", re.I)
CANT_RE = re.compile(
    r"\bI\s*(?:can['’]t|cannot|can not|am unable|['’]m unable|am not able|['’]m not able|"
    r"don['’]t have (?:access|the ability|a way)|do not have (?:access|the ability))\b|"
    r"\bno puedo\b|\bIMAGE_NOT_AVAILABLE\b|\bnot able to (?:do|access|see|open)\b", re.I)
CORRECTION_RE = re.compile(
    r"^\s*(?:no[,.! ]|nope\b|wrong\b|not that\b|that['’]?s not\b|that is not\b|i said\b|i meant\b|i told you\b|"
    r"again\b|actually\b|try again\b|te dije\b|no es\b|eso no\b|otra vez\b|incorrecto\b|mal\b)"
    r"|\b(?:i already (?:told|said|asked)|you didn['’]t|you did not|ya te dije|that['’]s wrong|you missed|"
    r"you forgot|not what i (?:asked|said|meant)|i asked (?:you )?(?:for|to))\b", re.I)


# ── guards / paths ───────────────────────────────────────────────────────
class FamilyEditionError(RuntimeError):
    pass


def main_data_dir() -> Path:
    return Path(os.getenv("EMPIRE_DATA_DIR") or (Path.home() / "empire-data"))


def assert_main_studio(data_dir: Path) -> None:
    ed = (os.getenv("EMPIRE_EDITION") or "main").strip().lower()
    if ed not in ("", "main"):
        raise FamilyEditionError(f"refusing to export: EMPIRE_EDITION={ed} (family edition)")
    resolved = str(Path(data_dir).expanduser().resolve())
    if any(m in resolved for m in FAMILY_MARKERS):
        raise FamilyEditionError(f"refusing to export from family-edition data dir {resolved}")


def unified_db_path(data_dir: Path) -> Path:
    brain = os.getenv("EMPIRE_BRAIN_DIR")
    return (Path(brain) if brain else data_dir / "brain") / "unified_messages.db"


def local_day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    tz = sj._local_tz()
    start = datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc)
    return start, end


# ── test-traffic detection ───────────────────────────────────────────────
@lru_cache(maxsize=1)
def test_fixture_messages() -> frozenset:
    """String literals used as chat messages in backend/tests.

    The test suite has historically posted to the live unified store; a
    legacy session whose user text exactly matches one of these is flagged
    as suspected test traffic and left out of the review (counted in
    summary.json → excluded_sessions)."""
    tests_dir = Path(__file__).resolve().parents[3] / "tests"
    out: set[str] = set()
    if not tests_dir.is_dir():
        return frozenset()
    for f in tests_dir.rglob("test_*.py"):
        if f.name == "test_max_session_journal.py":  # this exporter's own tests
            continue
        try:
            tree = ast.parse(f.read_text(errors="ignore"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                s = node.value.strip()
                if 12 <= len(s) <= 400 and "\n" not in s:
                    out.add(s.lower())
    return frozenset(out)


# ── loaders ──────────────────────────────────────────────────────────────
def _jsonish(v: Any, default: Any) -> Any:
    if v in (None, ""):
        return default
    if isinstance(v, (list, dict)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return default if not isinstance(v, str) else [v] if isinstance(default, list) else default


def load_journal(day: date, data_dir: Path) -> list[dict]:
    db = Path(os.getenv("EMPIRE_MAX_JOURNAL_DB") or (data_dir / "brain" / "max_session_journal.db"))
    turns = []
    for r in sj.turns_for_date(day.isoformat(), db_path=db, edition_name="main"):
        ts = sj.parse_ts(r["created_at"])
        turns.append({
            "source": "journal",
            "session_id": r["conversation_id"],
            "channel": r["channel"],
            "input_channel": r.get("input_channel"),
            "role": r["role"],
            "text": r.get("content") or "",
            "model": r.get("model"),
            "tool_calls": r.get("tool_calls") or [],
            "attachments": r.get("attachments") or [],
            "status": r.get("status") or "ok",
            "latency_ms": r.get("latency_ms"),
            "endpoint": r.get("endpoint"),
            "ts": ts,
        })
    return turns


def load_unified(day: date, data_dir: Path) -> list[dict]:
    db = unified_db_path(data_dir)
    if not db.exists():
        return []
    start, end = local_day_bounds_utc(day)
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"""SELECT * FROM unified_messages
                 WHERE channel IN ({','.join('?' for _ in EXPORT_CHANNELS)})
                   AND datetime(created_at) >= datetime(?) AND datetime(created_at) < datetime(?)
                 ORDER BY datetime(created_at), id""",
            (*EXPORT_CHANNELS, start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        d = dict(r)
        meta = _jsonish(d.get("metadata"), {}) or {}
        if not isinstance(meta, dict):
            meta = {}
        if str(meta.get("edition") or "main").lower() not in ("main", ""):
            continue
        atts_raw = _jsonish(d.get("attachment_refs"), []) or []
        if isinstance(atts_raw, dict):
            atts_raw = [atts_raw]
        if not atts_raw and meta.get("image_filename"):
            atts_raw = [{"type": "upload", "ref": meta["image_filename"]}]
        if not atts_raw and meta.get("image"):
            atts_raw = [{"type": "telegram_image", "ref": meta["image"]}]
        attachments = []
        for a in atts_raw:
            ref = a.get("ref") if isinstance(a, dict) else str(a)
            if ref:
                attachments.append({"legacy_ref": ref, "kind": "image"})
        role = d.get("role") or "user"
        tool_calls = []
        for tr in _jsonish(d.get("tool_results"), []) or []:
            s = sj.summarize_tool_call(tr) if isinstance(tr, dict) else None
            if s:
                if s.get("success") is False and not s.get("error") and role != "tool":
                    s["error"] = "(failed; legacy store kept no error detail)"
                if role == "tool" and not s.get("summary"):
                    s["summary"] = sj._short(d.get("content"), 400)
                if s.get("success") is False and not s.get("error") and role == "tool":
                    s["error"] = sj._short(d.get("content"), 300)
                tool_calls.append(s)
        out.append({
            "source": "unified_messages",
            "session_id": d.get("conversation_id"),
            "channel": sj.normalize_channel(d.get("channel")),
            "input_channel": meta.get("input_channel") or d.get("channel"),
            "role": role,
            "text": d.get("content") or "",
            "model": d.get("model"),
            "tool_calls": tool_calls,
            "attachments": attachments,
            "status": "ok",
            "latency_ms": None,
            "endpoint": meta.get("source"),
            "ts": sj.parse_ts(d.get("created_at")),
            "kind": meta.get("kind"),
        })
    return out


def merge_sources(journal: list[dict], legacy: list[dict]) -> dict[str, list[dict]]:
    sessions: dict[str, list[dict]] = {}
    first_journal: dict[str, datetime] = {}
    for t in journal:
        sessions.setdefault(t["session_id"], []).append(t)
        ts = t["ts"]
        if ts and (t["session_id"] not in first_journal or ts < first_journal[t["session_id"]]):
            first_journal[t["session_id"]] = ts
    for t in legacy:
        sid = t["session_id"]
        cutoff = first_journal.get(sid)
        if cutoff is not None and (t["ts"] is None or t["ts"] >= cutoff - timedelta(seconds=2)):
            continue  # journal already has this part of the session
        if sid in first_journal and t["role"] == "assistant" and t["ts"] and t["ts"] >= cutoff - timedelta(seconds=2):
            continue
        sessions.setdefault(sid, []).append(t)
    for sid in sessions:
        sessions[sid].sort(key=lambda t: (t["ts"] or datetime.min.replace(tzinfo=timezone.utc)))
    return sessions


def is_suspected_test(turns: list[dict]) -> bool:
    fixtures = test_fixture_messages()
    users = [t["text"].strip().lower() for t in turns if t["role"] == "user" and t["text"].strip()]
    # ALL user lines must be verbatim test fixtures: real sessions that
    # happen to reuse one quoted phrase (tests copy real prompts) stay in.
    return bool(users) and all(u in fixtures for u in users)


# ── analysis ─────────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    return re.sub(r"[^\w ]+", "", re.sub(r"\s+", " ", (s or "").lower())).strip()


def analyse_session(sid: str, turns: list[dict], file_name: str) -> dict:
    flags: dict[str, list] = {"tool_errors": [], "refusals": [], "cant_replies": [], "repeats": [], "corrections": []}
    prev_users: list[str] = []
    for idx, t in enumerate(turns):
        ref = {"session": sid, "file": file_name, "turn": idx, "time": t.get("ts_local"), "channel": t["channel"]}
        text = t.get("text") or ""
        for tc in t.get("tool_calls") or []:
            if tc.get("success") is False:
                flags["tool_errors"].append({**ref, "tool": tc.get("tool"), "error": tc.get("error") or tc.get("summary")})
        if t["role"] == "assistant":
            if REFUSAL_RE.search(text) or (t.get("model") == "guardrail"):
                flags["refusals"].append({**ref, "text": sj._short(text, 240)})
            elif CANT_RE.search(text):
                m = CANT_RE.search(text)
                lo = max(0, m.start() - 80)
                flags["cant_replies"].append({**ref, "text": sj._short(text[lo:m.end() + 160], 260)})
            if t.get("status") in ("error", "interrupted"):
                flags["tool_errors"].append({**ref, "tool": "(reply)", "error": f"reply {t['status']}"})
        elif t["role"] == "user" and text.strip():
            n = _norm(text)
            if len(n) >= 6:
                for p in prev_users[-3:]:
                    if n == p or SequenceMatcher(None, n, p).ratio() >= 0.85:
                        flags["repeats"].append({**ref, "text": sj._short(text, 240)})
                        break
            if CORRECTION_RE.search(text):
                flags["corrections"].append({**ref, "text": sj._short(text, 240)})
            prev_users.append(n)
    return flags


# ── writer ───────────────────────────────────────────────────────────────
def _slug(s: str, n: int = 40) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s or "")[:n].strip("_") or "x"


def _copy_attachment(att: dict, images_dir: Path, prefix: str, seq: int) -> dict:
    out = dict(att)
    src: Optional[Path] = None
    if att.get("archive_path") and Path(att["archive_path"]).is_file():
        src = Path(att["archive_path"])
    elif att.get("legacy_ref"):
        rec = sj.archive_attachment(att["legacy_ref"], kind="image", source="legacy_unified")
        if rec:
            out.update(rec)
            if rec.get("archived"):
                src = Path(rec["archive_path"])
    if src is None:
        out["exported"] = False
        out["missing"] = True
        return out
    images_dir.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}_{seq:02d}_{_slug(att.get('original_name') or att.get('legacy_ref') or src.name, 60)}"
    if not Path(name).suffix:
        name += src.suffix
    dest = images_dir / name
    if not dest.exists():
        shutil.copy2(src, dest)
    out["exported"] = True
    out["export_path"] = f"images/{name}"
    for k in ("source_path", "archive_path"):
        out.pop(k, None)
    return out


def _md(session_meta: dict, turns: list[dict]) -> str:
    lines = [f"# Max session {session_meta['session_id']}",
             "", f"- Channel: {session_meta['channel']}",
             f"- Started: {session_meta['started_local']}  ·  Last: {session_meta['ended_local']} (ET)",
             f"- Turns: {session_meta['turns']}  ·  Images/files: {session_meta['attachments']}",
             f"- Source: {', '.join(session_meta['sources'])}", ""]
    for t in turns:
        who = {"user": "Rafael", "assistant": "Max", "tool": "Tool", "system": "System"}.get(t["role"], t["role"])
        hdr = f"## {t.get('ts_local', '')[11:19]} ET — {who}"
        if t.get("model") and t["role"] == "assistant":
            hdr += f" ({t['model']})"
        if t.get("status") not in (None, "ok"):
            hdr += f" [{t['status']}]"
        lines += [hdr, "", t.get("text") or "_(empty)_", ""]
        for a in t.get("attachments") or []:
            if a.get("export_path"):
                lines.append(f"![{a.get('original_name') or 'image'}]({a['export_path']})")
            else:
                lines.append(f"- attachment missing: {a.get('original_name') or a.get('legacy_ref')}")
        for tc in t.get("tool_calls") or []:
            ok = "ok" if tc.get("success") else ("FAILED" if tc.get("success") is False else "?")
            detail = tc.get("error") or tc.get("summary") or ""
            lines.append(f"- tool `{tc.get('tool')}` → {ok}{': ' + detail if detail else ''}")
        lines.append("")
    return "\n".join(lines)


def export_day(day: date | str, *, out_root: Optional[Path] = None, data_dir: Optional[Path] = None,
               include_tests: bool = False) -> dict:
    if isinstance(day, str):
        day = date.fromisoformat(day)
    data_dir = Path(data_dir or main_data_dir()).expanduser()
    assert_main_studio(data_dir)
    out_root = Path(out_root or (data_dir / "max-sessions")).expanduser()
    assert_main_studio(out_root)
    day_dir = out_root / day.isoformat()
    tmp_dir = out_root / f".{day.isoformat()}.tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    try:
        out_root.chmod(0o700)
    except OSError:
        pass
    images_dir = tmp_dir / "images"

    journal = load_journal(day, data_dir)
    legacy = load_unified(day, data_dir)
    sessions = merge_sources(journal, legacy)

    summary: dict[str, Any] = {
        "date": day.isoformat(), "timezone": sj.LOCAL_TZ_NAME,
        "generated_at": datetime.now(sj._local_tz()).isoformat(timespec="seconds"),
        "scope": "Rafael main studio only (studio chat, Telegram, live voice); family editions excluded",
        "sources": {"journal_turns": len(journal), "legacy_unified_turns": len(legacy)},
        "sessions": 0, "turns": 0, "user_turns": 0, "assistant_turns": 0, "tool_calls": 0,
        "images": {"exported": 0, "missing": 0}, "by_channel": {},
        "tool_errors": [], "refusals": [], "cant_replies": [], "repeats": [], "corrections": [],
        "counts": {}, "session_index": [], "excluded_sessions": [],
    }
    for sid, turns in sorted(sessions.items(), key=lambda kv: kv[1][0]["ts"] or datetime.min.replace(tzinfo=timezone.utc)):
        if not include_tests and is_suspected_test(turns):
            summary["excluded_sessions"].append({"session": sid, "reason": "suspected_test_traffic",
                                                 "turns": len(turns), "first_text": sj._short(next((t["text"] for t in turns if t["role"] == "user"), ""), 80)})
            continue
        channel = next((t["channel"] for t in turns if t["channel"]), "studio")
        first_ts = turns[0]["ts"] or datetime.now(timezone.utc)
        short = re.sub(r"^(telegram|voice|studio|whatsapp|anon)-", "", sid or "")[:10]
        prefix = f"{sj.to_local(first_ts).strftime('%H%M')}_{channel}_{_slug(short, 10)}"
        att_seq = 0
        rendered = []
        for t in turns:
            ts = t["ts"]
            r = {k: v for k, v in t.items() if k not in ("ts",)}
            r["ts_utc"] = ts.astimezone(timezone.utc).isoformat() if ts else None
            r["ts_local"] = sj.to_local(ts).isoformat() if ts else ""
            atts = []
            for a in t.get("attachments") or []:
                att_seq += 1
                ca = _copy_attachment(a, images_dir, prefix, att_seq)
                summary["images"]["exported" if ca.get("exported") else "missing"] += 1
                atts.append(ca)
            r["attachments"] = atts
            rendered.append(r)
        meta = {
            "type": "session", "session_id": sid, "channel": channel, "date": day.isoformat(),
            "started_local": rendered[0]["ts_local"], "ended_local": rendered[-1]["ts_local"],
            "turns": len(rendered), "attachments": att_seq,
            "sources": sorted({t["source"] for t in rendered}),
        }
        jsonl = tmp_dir / f"{prefix}.jsonl"
        with open(jsonl, "w") as fh:
            fh.write(json.dumps(meta, default=str) + "\n")
            for i, r in enumerate(rendered):
                fh.write(json.dumps({"type": "turn", "turn": i, **r}, default=str, ensure_ascii=False) + "\n")
        (tmp_dir / f"{prefix}.md").write_text(_md(meta, rendered))
        flags = analyse_session(sid, rendered, jsonl.name)
        for k, v in flags.items():
            summary[k].extend(v)
        n_user = sum(1 for r in rendered if r["role"] == "user")
        n_asst = sum(1 for r in rendered if r["role"] == "assistant")
        n_tools = sum(len(r.get("tool_calls") or []) for r in rendered)
        summary["sessions"] += 1
        summary["turns"] += len(rendered)
        summary["user_turns"] += n_user
        summary["assistant_turns"] += n_asst
        summary["tool_calls"] += n_tools
        bc = summary["by_channel"].setdefault(channel, {"sessions": 0, "turns": 0})
        bc["sessions"] += 1
        bc["turns"] += len(rendered)
        summary["session_index"].append({**{k: meta[k] for k in ("session_id", "channel", "started_local", "ended_local", "turns", "attachments", "sources")},
                                         "file": jsonl.name, "markdown": f"{prefix}.md", "user_turns": n_user,
                                         "tool_calls": n_tools, **{f"{k}_count": len(v) for k, v in flags.items()}})
    summary["counts"] = {k: len(summary[k]) for k in ("tool_errors", "refusals", "cant_replies", "repeats", "corrections")}
    summary["counts"]["excluded_sessions"] = len(summary["excluded_sessions"])
    (tmp_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str, ensure_ascii=False))
    if day_dir.exists():
        shutil.rmtree(day_dir)
    tmp_dir.rename(day_dir)
    summary["path"] = str(day_dir)
    return summary


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Export Rafael's Max sessions for one ET date.")
    p.add_argument("--date", default=None, help="YYYY-MM-DD (America/New_York). Default: today.")
    p.add_argument("--yesterday", action="store_true", help="Export yesterday (for a morning cron).")
    p.add_argument("--out", default=None, help="Output root (default ~/empire-data/max-sessions)")
    p.add_argument("--include-tests", action="store_true", help="Keep sessions flagged as test traffic")
    a = p.parse_args(argv)
    today = datetime.now(sj._local_tz()).date()
    day = date.fromisoformat(a.date) if a.date else (today - timedelta(days=1) if a.yesterday else today)
    try:
        s = export_day(day, out_root=Path(a.out) if a.out else None, include_tests=a.include_tests)
    except FamilyEditionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"path": s["path"], "sessions": s["sessions"], "turns": s["turns"], "images": s["images"],
                      "counts": s["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
