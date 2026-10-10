"""
"Max improves Max" loop (approved by Rafael, Oct 4, 2026).

  1. Rafael asks Max (chat or voice) for a system improvement.
  2. Max calls the tool `request_improvement` -> a structured change request lands in
     max_improvements with status `proposed` (problem, proposed change, affected modules, risk).
  3. Rafael taps Approve on the Improvements page -> approve_build():
       * CURSOR_API_KEY set  -> a Cursor cloud agent starts on github.com/r22gir/Empire and opens a PR
                                on its own branch (status `building`, then `pr_open`).
       * no key              -> a ready-to-run spec file is written and status is `awaiting_build`.
  4. Max shows the preview / PR link. Merge or deploy needs a SECOND tap (approve_merge), which only
     records Rafael's approval; the merge itself is done by a human in GitHub. Nothing here merges,
     deploys, restarts a service, or edits files in the running checkout.

Max can only create and read requests. Max has no tool that approves, builds, merges or deploys.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.services.leadforge import growth

REPO_URL = os.getenv("MAX_IMPROVE_REPO", "https://github.com/r22gir/Empire")
BASE_REF = os.getenv("MAX_IMPROVE_BASE_REF", "main")
SPEC_DIR = Path(os.getenv("MAX_IMPROVE_SPEC_DIR", str(Path.home() / "empire-data" / "improvements")))
RISKS = ("low", "medium", "high")
API = "https://api.cursor.com"
# Rafael's defaults (Oct 4, 2026): Muse Spark 1.3 at medium effort; Gemini 3.8 Flash for small fixes.
# If the API refuses a model, the launch retries with the account default (no "model" field).
DEFAULT_MODEL = os.getenv("MAX_IMPROVE_MODEL", "muse-spark-1.3")
DEFAULT_PARAMS = [{"id": "effort", "value": os.getenv("MAX_IMPROVE_EFFORT", "medium")}]
SMALL_MODEL = os.getenv("MAX_IMPROVE_SMALL_MODEL", "gemini-3.8-flash")
SMALL_PARAMS = [{"id": "reasoning_effort", "value": os.getenv("MAX_IMPROVE_SMALL_EFFORT", "medium")}]
STATUSES = ("proposed", "awaiting_build", "building", "pr_open", "merge_approved", "rejected", "build_failed", "done")


def _ensure(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS max_improvements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, problem TEXT NOT NULL, proposed_change TEXT NOT NULL,
        affected_modules TEXT, risk TEXT DEFAULT 'medium', acceptance TEXT,
        requested_via TEXT DEFAULT 'chat', requested_text TEXT,
        status TEXT NOT NULL DEFAULT 'proposed',
        spec_path TEXT, agent_id TEXT, agent_url TEXT, branch TEXT, pr_url TEXT, preview_url TEXT,
        build_note TEXT, created_at TEXT DEFAULT (datetime('now','localtime')),
        approved_at TEXT, merge_approved_at TEXT, decided_by TEXT)""")
    have = {r[1] for r in conn.execute("PRAGMA table_info(max_improvements)")}
    for col in ("model", "run_id"):
        if col not in have:
            conn.execute(f"ALTER TABLE max_improvements ADD COLUMN {col} TEXT")


def _row(r) -> dict:
    d = dict(r)
    try:
        d["affected_modules"] = json.loads(d.get("affected_modules") or "[]")
    except Exception:
        d["affected_modules"] = [d.get("affected_modules")] if d.get("affected_modules") else []
    d["next_step"] = {
        "proposed": "Rafael: Approve to start the build, or Reject.",
        "awaiting_build": "Spec is ready. Start it in Cursor (or add CURSOR_API_KEY and tap Build again).",
        "building": "Cloud agent is working. Refresh to check for the PR.",
        "pr_open": "Review the PR / preview. Tap Approve merge only after you have looked at it.",
        "merge_approved": "Approved. A human merges and deploys; Max does not.",
        "rejected": "Closed.", "build_failed": "See build note. Edit and approve again.", "done": "Merged.",
    }.get(d["status"], "")
    return d


def cursor_configured() -> bool:
    return bool(os.getenv("CURSOR_API_KEY"))


def create_request(title: str, problem: str, proposed_change: str, affected_modules=None, risk: str = "medium",
                   acceptance: str = "", requested_via: str = "chat", requested_text: str = "") -> dict:
    if not (title or "").strip() or not (problem or "").strip() or not (proposed_change or "").strip():
        raise ValueError("title, problem and proposed_change are required")
    risk = (risk or "medium").lower()
    if risk not in RISKS:
        risk = "medium"
    mods = affected_modules if isinstance(affected_modules, list) else \
        [m.strip() for m in str(affected_modules or "").split(",") if m.strip()]
    with growth._db() as conn:
        _ensure(conn)
        cur = conn.execute(
            """INSERT INTO max_improvements (title, problem, proposed_change, affected_modules, risk, acceptance,
                   requested_via, requested_text) VALUES (?,?,?,?,?,?,?,?)""",
            (title.strip()[:200], problem.strip(), proposed_change.strip(), json.dumps(mods), risk,
             (acceptance or "").strip(), requested_via, (requested_text or "")[:2000]))
        return _row(conn.execute("SELECT * FROM max_improvements WHERE id=?", (cur.lastrowid,)).fetchone())


def list_requests(status: Optional[str] = None) -> dict:
    with growth._db() as conn:
        _ensure(conn)
        if status:
            rows = conn.execute("SELECT * FROM max_improvements WHERE status=? ORDER BY id DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM max_improvements ORDER BY id DESC LIMIT 200").fetchall()
    return {"items": [_row(r) for r in rows], "cursor_configured": cursor_configured(),
            "repo": REPO_URL, "base_ref": BASE_REF,
            "models": {"default": f"{DEFAULT_MODEL} ({DEFAULT_PARAMS[0]['value']})",
                       "small_fix": f"{SMALL_MODEL} ({SMALL_PARAMS[0]['value']})"},
            "policy": "Max writes requests only. Build starts on Rafael's tap. Merge/deploy needs a second tap "
                      "and is done by a human. Max never edits his own code or deploys."}


def get(req_id: int) -> Optional[dict]:
    with growth._db() as conn:
        _ensure(conn)
        r = conn.execute("SELECT * FROM max_improvements WHERE id=?", (req_id,)).fetchone()
    return _row(r) if r else None


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "change"


def build_prompt(req: dict) -> str:
    mods = ", ".join(req["affected_modules"]) or "(see proposed change)"
    acceptance = req.get("acceptance") or ("- Behaviour described above works.\n"
                                           "- Existing tests pass; add a test for the new behaviour.")
    return f"""# Empire improvement IMP-{req['id']}: {req['title']}

Repository: {REPO_URL} (base: {BASE_REF}). Work on a NEW branch (never {BASE_REF}) and open a pull request
titled "IMP-{req['id']:04d}: {req['title']}". Do not merge. Do not deploy. Do not push to {BASE_REF}.

## Problem
{req['problem']}

## Proposed change
{req['proposed_change']}

## Affected modules
{mods}

## Risk
{req['risk']}

## Acceptance
{acceptance}

## House rules (must follow)
- Never edit max/memory.md. Never touch OpenClaw, test-studio or willard data.
- Never print or commit secrets or .env files.
- Outreach stays draft-only: nothing may send email, SMS, DMs or social posts without a founder tap.
- Keep Dark and Gold themes working; check mobile at 390px for UI changes.
- Back-end: FastAPI in backend/app; portal: Next.js in empire-command-center.
- In the PR description list: what changed, how it was tested, screenshots for UI changes, rollback steps.
"""


def write_spec(req: dict) -> str:
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    path = SPEC_DIR / f"IMP-{req['id']:04d}-{_slug(req['title'])}.md"
    path.write_text(build_prompt(req) + f"\n\n---\nGenerated {datetime.now().isoformat(timespec='seconds')} "
                    f"after Rafael approved. Status: awaiting build.\n"
                    f"Run it: paste this file into a Cursor cloud agent on {REPO_URL}, or set CURSOR_API_KEY on the Dell "
                    f"and tap Build on the Improvements page.\n")
    return str(path)


def is_small_fix(req: dict) -> bool:
    """Small fix = low risk and touches at most two modules -> the faster model."""
    return req.get("risk") == "low" and len(req.get("affected_modules") or []) <= 2


def pick_model(req: dict) -> dict:
    if is_small_fix(req):
        return {"id": SMALL_MODEL, "params": SMALL_PARAMS}
    return {"id": DEFAULT_MODEL, "params": DEFAULT_PARAMS}


def _auth():
    return (os.environ["CURSOR_API_KEY"], "")


def _launch_cursor_agent(req: dict) -> dict:
    """POST /v1/agents. Only called from approve_build (Rafael's tap). Never merges; the agent opens a PR."""
    import httpx
    model = pick_model(req)
    body = {"prompt": {"text": build_prompt(req)},
            "name": f"IMP-{req['id']:04d} {req['title']}"[:100],
            "repos": [{"url": REPO_URL, "startingRef": BASE_REF}],
            "workOnCurrentBranch": False,   # new cursor/... branch, never the base branch
            "autoCreatePR": True,
            "model": model}
    r = httpx.post(f"{API}/v1/agents", json=body, auth=_auth(), timeout=60)
    used = model["id"]
    if r.status_code in (400, 404, 422) and "model" in r.text.lower():
        body.pop("model")  # account default
        r = httpx.post(f"{API}/v1/agents", json=body, auth=_auth(), timeout=60)
        used = "account default"
    if r.status_code >= 400:
        raise RuntimeError(f"Cursor API HTTP {r.status_code}: {r.text[:300]}")
    j = r.json() or {}
    a = j.get("agent") or j
    run = j.get("run") or {}
    return {"agent_id": a.get("id"), "run_id": run.get("id") or a.get("latestRunId"),
            "agent_url": a.get("url") or (f"https://cursor.com/agents/{a.get('id')}" if a.get("id") else None),
            "model": used}


def approve_build(req_id: int, *, confirm: bool, by: str = "rafael") -> dict:
    """Rafael's tap #1. Starts the build (cloud agent) or writes the spec."""
    if not confirm:
        raise PermissionError("confirm=true is required (Rafael's tap)")
    req = get(req_id)
    if not req:
        raise LookupError("not found")
    if req["status"] not in ("proposed", "awaiting_build", "build_failed"):
        raise ValueError(f"request is {req['status']}")
    # Claim the request atomically so a double tap can never launch two agents.
    with growth._db() as conn:
        _ensure(conn)
        cur = conn.execute("UPDATE max_improvements SET status='building', build_note='starting' WHERE id=? "
                           "AND status IN ('proposed','awaiting_build','build_failed')", (req_id,))
        if cur.rowcount != 1:
            raise ValueError("request is already being built")
    try:
        spec = write_spec(req)
    except Exception as e:
        with growth._db() as conn:
            conn.execute("UPDATE max_improvements SET status='build_failed', build_note=? WHERE id=?",
                         (f"Could not write spec: {e}"[:500], req_id))
        raise
    upd = {"spec_path": spec, "approved_at": datetime.now().isoformat(timespec="seconds"), "decided_by": by}
    if cursor_configured():
        try:
            upd.update(_launch_cursor_agent(req))
            upd["status"] = "building"
            upd["build_note"] = (f"Cursor cloud agent started on {REPO_URL} (model: {upd.get('model')}). "
                                 "It opens a PR on its own branch; nothing merges without your second tap.")
        except Exception as e:
            upd["status"] = "build_failed"
            upd["build_note"] = str(e)[:500]
    else:
        upd["status"] = "awaiting_build"
        upd["build_note"] = "No CURSOR_API_KEY on the Dell. Spec file written; ready to run."
    with growth._db() as conn:
        _ensure(conn)
        conn.execute(f"UPDATE max_improvements SET {', '.join(k + '=?' for k in upd)} WHERE id=?",
                     (*upd.values(), req_id))
    return get(req_id)


def refresh_build(req_id: int) -> dict:
    """Poll the cloud agent for its PR link (read-only)."""
    req = get(req_id)
    if not req or not req.get("agent_id") or not cursor_configured():
        return req or {}
    import httpx
    try:
        r = httpx.get(f"{API}/v1/agents/{req['agent_id']}", auth=_auth(), timeout=20)
        r.raise_for_status()
        a = r.json() or {}
        run_id = a.get("latestRunId") or req.get("run_id")
        run = {}
        if run_id:
            rr = httpx.get(f"{API}/v1/agents/{req['agent_id']}/runs/{run_id}", auth=_auth(), timeout=20)
            if rr.status_code == 200:
                run = rr.json() or {}
        branches = ((run.get("git") or {}).get("branches")) or []
        pr = next((b.get("prUrl") for b in branches if b.get("prUrl")), None)
        branch = next((b.get("branch") for b in branches if b.get("branch")), None)
        rs = str(run.get("status") or a.get("status") or "").upper()
        upd = {"build_note": f"agent {a.get('status')}, run {run.get('status') or '?'}", "run_id": run_id}
        if branch:
            upd["branch"] = branch
        if pr:
            upd.update({"pr_url": pr, "status": "pr_open",
                        "build_note": "PR is open. Review it (and the preview), then tap Approve merge. Max does not merge."})
        elif rs in ("ERROR", "FAILED", "CANCELLED", "EXPIRED"):
            upd["status"] = "build_failed"
            upd["build_note"] = f"Cloud agent run {rs.lower()}: {(run.get('result') or '')[:300]}"
        elif rs == "FINISHED":
            upd["build_note"] = "Agent finished without a PR link yet. Open the agent to check, or Build again."
        with growth._db() as conn:
            conn.execute(f"UPDATE max_improvements SET {', '.join(k + '=?' for k in upd)} WHERE id=?", (*upd.values(), req_id))
    except Exception as e:
        return {**req, "refresh_error": str(e)[:200]}
    return get(req_id)


def set_links(req_id: int, pr_url: str = "", preview_url: str = "") -> dict:
    """Record a PR / preview link by hand (e.g. after running the spec in Cursor yourself)."""
    upd = {}
    if pr_url:
        upd["pr_url"] = pr_url
        upd["status"] = "pr_open"
    if preview_url:
        upd["preview_url"] = preview_url
    if upd:
        with growth._db() as conn:
            _ensure(conn)
            conn.execute(f"UPDATE max_improvements SET {', '.join(k + '=?' for k in upd)} WHERE id=?", (*upd.values(), req_id))
    return get(req_id)


def approve_merge(req_id: int, *, confirm: bool, by: str = "rafael") -> dict:
    """Rafael's tap #2, only after he has seen the PR/preview. Records approval; does NOT merge or deploy."""
    if not confirm:
        raise PermissionError("confirm=true is required (Rafael's tap)")
    req = get(req_id)
    if not req:
        raise LookupError("not found")
    if req["status"] != "pr_open" or not (req.get("pr_url") or req.get("preview_url")):
        raise ValueError("There is no PR or preview to approve yet.")
    with growth._db() as conn:
        conn.execute("UPDATE max_improvements SET status='merge_approved', merge_approved_at=?, decided_by=? WHERE id=?",
                     (datetime.now().isoformat(timespec="seconds"), by, req_id))
    return get(req_id)


def reject(req_id: int, note: str = "") -> dict:
    with growth._db() as conn:
        _ensure(conn)
        conn.execute("UPDATE max_improvements SET status='rejected', build_note=? WHERE id=?", (note[:500], req_id))
    return get(req_id)
