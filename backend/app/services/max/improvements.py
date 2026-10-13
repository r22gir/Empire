"""
"Max improves Max" loop (approved by Rafael, Oct 4, 2026; Atlas queue Oct 13, 2026).

  1. Rafael asks Max (chat or voice) for a system improvement.
  2. Max calls the tool `request_improvement` -> a structured change request lands in
     max_improvements with status `proposed`.
  3. Rafael taps Approve -> approve_build() ONLY enqueues a SQLite job for the
     CodeForge desk (Atlas). It does not call MiniMax or GitHub itself.
  4. Atlas (MiniMax-M2, included plan path) writes a plan + proposed patch/spec,
     then opens a GitHub issue labeled max-improvement so a Cursor cloud agent
     (grok-4.6) can open a draft PR. Never merges. Never deploys.
  5. Rafael taps Approve merge after review. That only records approval.
     Rafael approves deploys after Chief e review. Max never deploys.

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
# Cloud-agent launches must include a model. Always grok-4.6 unless an
# operator explicitly sets MAX_IMPROVE_MODEL. Leave that env unset by default
# — do not write it, and do not treat getenv's default as a set env var.
_LAUNCH_MODEL = "grok-4.6"


def included_model() -> str:
    override = (os.getenv("MAX_IMPROVE_MODEL") or "").strip()
    return override or _LAUNCH_MODEL


INCLUDED_MODEL = included_model()
DEFAULT_MODEL = INCLUDED_MODEL
DEFAULT_PARAMS = [{"id": "effort", "value": os.getenv("MAX_IMPROVE_EFFORT", "medium")}]
SMALL_MODEL = INCLUDED_MODEL
SMALL_PARAMS = DEFAULT_PARAMS
PIPELINE = ("proposed", "approved", "planning", "pr_open", "deployed")
STATUSES = (
    "proposed", "approved", "planning", "awaiting_build", "building",
    "pr_open", "merge_approved", "deployed", "rejected", "build_failed", "done",
)
KINDS = ("growth", "fix", "nightly")
RETRYABLE = ("build_failed", "awaiting_build")
APPROVEABLE = ("proposed", "build_failed", "awaiting_build")


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
    for col, decl in (
        ("model", "TEXT"),
        ("run_id", "TEXT"),
        ("kind", "TEXT DEFAULT 'growth'"),
        ("issue_url", "TEXT"),
        ("job_id", "INTEGER"),
    ):
        if col not in have:
            conn.execute(f"ALTER TABLE max_improvements ADD COLUMN {col} {decl}")


def _row(r) -> dict:
    d = dict(r)
    try:
        d["affected_modules"] = json.loads(d.get("affected_modules") or "[]")
    except Exception:
        d["affected_modules"] = [d.get("affected_modules")] if d.get("affected_modules") else []
    d["approval_url"] = approval_deep_link(d.get("id"))
    d["next_step"] = {
        "proposed": "Rafael: Approve to enqueue Atlas (CodeForge), or Reject.",
        "approved": "Queued for Atlas. MiniMax-M2 will write the plan, then a GitHub issue is opened.",
        "planning": "Atlas is planning (MiniMax-M2) or a Cursor agent is opening a draft PR.",
        "awaiting_build": "Plan/spec is ready. Add a GitHub token or Cursor key and tap Retry.",
        "building": "Legacy: cloud agent is working. Refresh to check for the PR.",
        "pr_open": "Review the issue / draft PR. Tap Approve merge only after you have looked at it.",
        "merge_approved": "Merge approved. A human merges. Rafael approves deploys after Chief e review. Max does not.",
        "deployed": "Recorded as deployed by Rafael. Max never deploys.",
        "rejected": "Closed.",
        "build_failed": "See build note. Tap Retry to re-enqueue Atlas.",
        "done": "Merged (legacy). Deploy still needs Rafael after Chief e review.",
    }.get(d["status"], "")
    d["pipeline"] = list(PIPELINE)
    return d


def studio_base() -> str:
    try:
        from app.services.max.quick_replies import public_base
        return public_base()
    except Exception:
        return os.getenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store").rstrip("/")


def approval_deep_link(req_id) -> str:
    """Stable Studio deep link Max can send in chat / WhatsApp. Approval still needs the founder tap."""
    try:
        n = int(req_id)
    except (TypeError, ValueError):
        n = req_id
    return f"{studio_base()}/?screen=improvements&id={n}"


def cursor_configured() -> bool:
    return bool(os.getenv("CURSOR_API_KEY"))


def create_request(title: str, problem: str, proposed_change: str, affected_modules=None, risk: str = "medium",
                   acceptance: str = "", requested_via: str = "chat", requested_text: str = "",
                   kind: str = "growth") -> dict:
    if not (title or "").strip() or not (problem or "").strip() or not (proposed_change or "").strip():
        raise ValueError("title, problem and proposed_change are required")
    risk = (risk or "medium").lower()
    if risk not in RISKS:
        risk = "medium"
    kind = (kind or "growth").lower()
    if kind not in KINDS:
        kind = "growth"
    mods = affected_modules if isinstance(affected_modules, list) else \
        [m.strip() for m in str(affected_modules or "").split(",") if m.strip()]
    with growth._db() as conn:
        _ensure(conn)
        cur = conn.execute(
            """INSERT INTO max_improvements (title, problem, proposed_change, affected_modules, risk, acceptance,
                   requested_via, requested_text, kind) VALUES (?,?,?,?,?,?,?,?,?)""",
            (title.strip()[:200], problem.strip(), proposed_change.strip(), json.dumps(mods), risk,
             (acceptance or "").strip(), requested_via, (requested_text or "")[:2000], kind))
        return _row(conn.execute("SELECT * FROM max_improvements WHERE id=?", (cur.lastrowid,)).fetchone())


def list_requests(status: Optional[str] = None) -> dict:
    with growth._db() as conn:
        _ensure(conn)
        if status:
            rows = conn.execute("SELECT * FROM max_improvements WHERE status=? ORDER BY id DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM max_improvements ORDER BY id DESC LIMIT 200").fetchall()
    from app.services.max.improvement_planner import usage_snapshot
    from app.services.max.improvement_queue import queue_counts
    from app.services.max.improvement_github import github_configured
    return {"items": [_row(r) for r in rows], "cursor_configured": cursor_configured(),
            "github_configured": github_configured(),
            "minimax_configured": bool(os.getenv("MINIMAX_API_KEY")),
            "repo": REPO_URL, "base_ref": BASE_REF,
            "pipeline": list(PIPELINE),
            "minimax": usage_snapshot(),
            "queue": queue_counts(),
            "models": {"planner": "MiniMax-M2 (included plan path)",
                       "implementer": f"{DEFAULT_MODEL} ({DEFAULT_PARAMS[0]['value']})",
                       "default": f"{DEFAULT_MODEL} ({DEFAULT_PARAMS[0]['value']})",
                       "small_fix": f"{SMALL_MODEL} ({SMALL_PARAMS[0]['value']})"},
            "policy": "Max writes requests only. Approve enqueues Atlas (CodeForge). "
                      "MiniMax-M2 writes a plan, then a GitHub issue labeled max-improvement "
                      "is opened for a grok-4.6 draft PR. Merge/deploy needs Rafael after Chief e review. "
                      "Max never edits his own code or deploys. No auto-credits."}


def get(req_id: int) -> Optional[dict]:
    with growth._db() as conn:
        _ensure(conn)
        r = conn.execute("SELECT * FROM max_improvements WHERE id=?", (req_id,)).fetchone()
    return _row(r) if r else None


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "change"


def build_prompt(req: dict) -> str:
    if req.get("spec_override"):
        return str(req["spec_override"])
    mods = ", ".join(req.get("affected_modules") or []) or "(see proposed change)"
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
- Never print or commit secrets, .env, client_aliases.json, or business.json.
- No amp/maxine code. No live-data writes in tests. No outbound email, WhatsApp, or SMS.
- Outreach stays draft-only: nothing may send email, SMS, DMs or social posts without a founder tap.
- Keep Dark and Gold themes working; check mobile at 390px for UI changes.
- Back-end: FastAPI in backend/app; portal: Next.js in empire-command-center.
- In the PR description list: what changed, how it was tested, screenshots for UI changes, rollback steps.
"""


def write_spec(req: dict) -> str:
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    path = SPEC_DIR / f"IMP-{req['id']:04d}-{_slug(req['title'])}.md"
    body = req.get("spec_override") or build_prompt(req)
    path.write_text(
        body + f"\n\n---\nGenerated {datetime.now().isoformat(timespec='seconds')} "
        f"by Atlas after Rafael approved. Do not merge. Do not deploy.\n"
        f"GitHub issue label: max-improvement. Cursor implementer: grok-4.6 draft PR only.\n"
    )
    return str(path)


def is_small_fix(req: dict) -> bool:
    """Small fix = low risk and touches at most two modules -> the faster model."""
    return req.get("risk") == "low" and len(req.get("affected_modules") or []) <= 2


def pick_model(req: dict) -> dict:
    """Always include a model id (grok-4.6 unless MAX_IMPROVE_MODEL is set)."""
    return {"id": included_model(), "params": DEFAULT_PARAMS}


def _is_usage_limit_exceeded(status_code: int, body: str) -> bool:
    text = (body or "").lower()
    return (
        "usage_limit_exceeded" in text
        or "usage limit" in text
        or (status_code in (402, 429) and "limit" in text)
    )


def _usage_limit_message(body: str) -> str:
    return (
        "usage_limit_exceeded: Cursor usage limit reached. "
        "Max cannot raise this limit. Retry later or raise it in Cursor billing. "
        f"Detail: {(body or '')[:180]}"
    )


def _auth():
    return (os.environ["CURSOR_API_KEY"], "")


def _launch_cursor_agent(req: dict) -> dict:
    """POST /v1/agents. Only called from approve_build (Rafael's tap). Never merges; the agent opens a PR."""
    import httpx
    model = pick_model(req)
    prompt_text = req.get("_prompt_override") or build_prompt(req)
    body = {"prompt": {"text": prompt_text},
            "name": f"IMP-{req['id']:04d} {req['title']}"[:100],
            "repos": [{"url": REPO_URL, "startingRef": BASE_REF}],
            "workOnCurrentBranch": False,   # new cursor/... branch, never the base branch
            "autoCreatePR": True,
            "model": model}
    r = httpx.post(f"{API}/v1/agents", json=body, auth=_auth(), timeout=60)
    used = model["id"]
    if _is_usage_limit_exceeded(r.status_code, r.text):
        raise RuntimeError(_usage_limit_message(r.text))
    if r.status_code >= 400:
        # Do not retry without a model. Do not try to raise the limit.
        raise RuntimeError(f"Cursor API HTTP {r.status_code}: {r.text[:300]}")
    j = r.json() or {}
    a = j.get("agent") or j
    run = j.get("run") or {}
    return {"agent_id": a.get("id"), "run_id": run.get("id") or a.get("latestRunId"),
            "agent_url": a.get("url") or (f"https://cursor.com/agents/{a.get('id')}" if a.get("id") else None),
            "model": used}


def approve_build(req_id: int, *, confirm: bool, by: str = "rafael") -> dict:
    """Rafael's tap #1. Enqueues Atlas. Does not call MiniMax, GitHub, or Cursor."""
    if not confirm:
        raise PermissionError("confirm=true is required (Rafael's tap)")
    req = get(req_id)
    if not req:
        raise LookupError("not found")
    if req["status"] not in APPROVEABLE:
        raise ValueError(f"request is {req['status']}")
    from app.services.max.improvement_queue import enqueue
    # Claim atomically so a double tap cannot enqueue twice.
    with growth._db() as conn:
        _ensure(conn)
        cur = conn.execute(
            "UPDATE max_improvements SET status='approved', build_note=?, approved_at=?, decided_by=? "
            "WHERE id=? AND status IN ('proposed','awaiting_build','build_failed')",
            ("Queued for Atlas (CodeForge). MiniMax-M2 plans, then a max-improvement GitHub issue. "
             "Nothing merges or deploys.",
             datetime.now().isoformat(timespec="seconds"), by, req_id),
        )
        if cur.rowcount != 1:
            raise ValueError("request is already being built")
    job = enqueue(req_id, kind="retry" if req["status"] in RETRYABLE else "plan")
    with growth._db() as conn:
        conn.execute("UPDATE max_improvements SET job_id=? WHERE id=?", (job["id"], req_id))
    return get(req_id)


def retry_build(req_id: int, *, confirm: bool, by: str = "rafael") -> dict:
    """Re-enqueue a failed / awaiting request. Same confirm gate as approve."""
    if not confirm:
        raise PermissionError("confirm=true is required (Rafael's tap)")
    req = get(req_id)
    if not req:
        raise LookupError("not found")
    if req["status"] not in RETRYABLE:
        raise ValueError(f"retry is only for {', '.join(RETRYABLE)} (got {req['status']})")
    return approve_build(req_id, confirm=True, by=by)


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
    if req["status"] != "pr_open" or not (req.get("pr_url") or req.get("preview_url") or req.get("issue_url")):
        raise ValueError("There is no PR, preview, or GitHub issue to approve yet.")
    with growth._db() as conn:
        conn.execute("UPDATE max_improvements SET status='merge_approved', merge_approved_at=?, decided_by=? WHERE id=?",
                     (datetime.now().isoformat(timespec="seconds"), by, req_id))
    return get(req_id)


def mark_deployed(req_id: int, *, confirm: bool, by: str = "rafael", note: str = "") -> dict:
    """Record that Rafael deployed after Chief e review. Does NOT deploy anything."""
    if not confirm:
        raise PermissionError("confirm=true is required (Rafael's tap)")
    req = get(req_id)
    if not req:
        raise LookupError("not found")
    if req["status"] not in ("merge_approved", "done"):
        raise ValueError("Deploy is recorded only after merge approval (Chief e review, then Rafael).")
    extra = (note or "").strip()
    with growth._db() as conn:
        conn.execute(
            "UPDATE max_improvements SET status='deployed', decided_by=?, build_note=? WHERE id=?",
            (by, (extra or "Recorded as deployed by Rafael after Chief e review. Max did not deploy.")[:500], req_id),
        )
    return get(req_id)


def reject(req_id: int, note: str = "") -> dict:
    with growth._db() as conn:
        _ensure(conn)
        conn.execute("UPDATE max_improvements SET status='rejected', build_note=? WHERE id=?", (note[:500], req_id))
    return get(req_id)
