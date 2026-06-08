"""Update the Hermes ↔ Harry operational truth artifact.

This is a PILOT PROGRAM — not a full memory rewrite, not a production
edit. The artifact (.empire/runtime/HERMES_HARRY_SYNC.json) gives
Hermes Desktop, Harry/OpenCode, and (eventually) MAX a shared read of
the operational state. The HTML and Markdown views are generated from
the same JSON so there is exactly one source of truth.

Run from the canonical repo root:
    cd /home/rg/empire-repo-main
    python3 backend/scripts/update_hermes_harry_sync.py

What it does:
    1. Probes opencode-remote.service, MAX backend, Hermes gateway,
       git state, opencode DB.
    2. Computes blocking / non-blocking mismatches.
    3. Writes the JSON sidecar atomically.
    4. Renders the HTML view from the same data.
    5. Renders the Markdown fallback at the repo root.

What it does NOT do:
    - Touch .opencode/config.json
    - Modify ~/.hermes/MEMORY.md or USER.md
    - Read auth.json contents or print any secret
    - Restart any service
    - Edit source code
"""
import datetime as _dt
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────

CANONICAL_REPO = "/home/rg/empire-repo-main"
OTHER_REPO = "/home/rg/empire-repo"
OPENCODE_DB = "/home/rg/.local/share/opencode/opencode.db"
RUNTIME_DIR = Path(CANONICAL_REPO) / ".empire" / "runtime"
JSON_PATH = RUNTIME_DIR / "HERMES_HARRY_SYNC.json"
HTML_PATH = RUNTIME_DIR / "HERMES_HARRY_SYNC.html"
MD_PATH = Path(CANONICAL_REPO) / "HERMES-HARRY-HANDOFF.md"
MAX_HEALTH = "http://127.0.0.1:8000/health"
MAX_STATUS = "http://127.0.0.1:8000/api/v1/max/status"
MAX_VOICE = "http://127.0.0.1:8000/api/v1/max/voice/status"
OPENCODE_LOCAL = "http://127.0.0.1:8787/"
OPENCODE_TS = "http://100.110.233.75:8787/"
HERMES_VERSION_CMD = ["hermes", "--version"]
HERMES_DOCTOR_CMD = ["hermes", "doctor"]


# ── Helpers ───────────────────────────────────────────────────────────────

def _run(cmd, **kw):
    """Run a subprocess, return (rc, stdout, stderr) — never raise."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=kw.pop("timeout", 8), **kw)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", "command not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:
        return 1, "", f"error: {e}"


def _read_file(path, default=""):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return default


def _atomic_write(path: Path, content: str) -> None:
    """Write to a tempfile in the same dir, then rename (POSIX-atomic)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise


# ── Probe functions ───────────────────────────────────────────────────────

def probe_git_state(repo_path: str) -> dict:
    """Read git state from the given worktree."""
    if not Path(repo_path, ".git").exists():
        return {"toplevel": repo_path, "branch": "(no-git)", "head": "(no-git)", "ahead_behind": "n/a", "dirty": [], "error": "not a git repo"}
    try:
        toplevel = subprocess.check_output(["git", "-C", repo_path, "rev-parse", "--show-toplevel"], text=True).strip()
        branch = subprocess.check_output(["git", "-C", repo_path, "branch", "--show-current"], text=True).strip()
        head = subprocess.check_output(["git", "-C", repo_path, "rev-parse", "--short", "HEAD"], text=True).strip()
        rc, ab, _ = _run(["git", "-C", repo_path, "rev-list", "--left-right", "--count", "origin/main...main"])
        a, b = (ab.strip().split() + ["0", "0"])[:2]
        rc, status, _ = _run(["git", "-C", repo_path, "status", "--short"])
        dirty = [line for line in status.splitlines() if line.strip()]
        return {
            "toplevel": toplevel,
            "branch": branch or "(detached)",
            "head": head,
            "origin_main": head,  # placeholder; updated below
            "ahead_behind": f"{a}	{b}",
            "dirty": dirty,
        }
    except Exception as e:
        return {"toplevel": repo_path, "error": str(e)}


def probe_opencode_process() -> dict:
    """Detect opencode-remote.service state."""
    rc, status, _ = _run(["systemctl", "--user", "is-active", "opencode-remote.service"])
    is_active = status.strip() == "active"
    rc, log, _ = _run(["journalctl", "--user", "-u", "opencode-remote.service", "-n", "1", "--no-pager"])
    return {
        "service_running": is_active,
        "service_active_word": status.strip() or "inactive",
        "last_journal_line": log.strip()[-300:] if log else "",
    }


def probe_opencode_db() -> dict:
    """Inspect the opencode project/session DB."""
    if not Path(OPENCODE_DB).exists():
        return {"exists": False, "projects": [], "newest_sessions": []}
    try:
        con = sqlite3.connect(OPENCODE_DB)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT id, worktree, vcs, time_created, time_updated, time_initialized FROM project")
        projects = []
        for r in cur.fetchall():
            projects.append({
                "project_id": r["id"],
                "worktree": r["worktree"],
                "vcs": r["vcs"],
                "first_seen": _dt.datetime.fromtimestamp(r["time_created"]/1000).isoformat() if r["time_created"] else None,
                "last_seen": _dt.datetime.fromtimestamp(r["time_updated"]/1000).isoformat() if r["time_updated"] else None,
            })
        cur.execute("""SELECT id, project_id, directory, time_updated
                       FROM session
                       WHERE time_archived IS NULL
                       ORDER BY time_updated DESC LIMIT 5""")
        sessions = []
        for r in cur.fetchall():
            sessions.append({
                "id": r["id"],
                "project_id": r["project_id"],
                "directory": r["directory"],
                "last_updated": _dt.datetime.fromtimestamp(r["time_updated"]/1000).isoformat() if r["time_updated"] else None,
            })
        return {"exists": True, "projects": projects, "newest_sessions": sessions}
    except Exception as e:
        return {"exists": True, "error": str(e)}


def probe_hermes() -> dict:
    """Hermes version + doctor summary."""
    rc, version_out, _ = _run(HERMES_VERSION_CMD, timeout=5)
    rc, doctor_out, _ = _run(HERMES_DOCTOR_CMD, timeout=15)
    # Only keep the first ~30 lines of doctor output, no secrets
    doctor_lines = doctor_out.splitlines()[:30]
    return {
        "version": version_out.strip() or "unknown",
        "doctor_lines": doctor_lines,
        "doctor_clean": rc == 0 and "⚠" not in doctor_out and "✗" not in doctor_out and "issues" not in doctor_out.lower(),
    }


def probe_max_backend() -> dict:
    """Probe the MAX backend's health, status, and voice endpoints via HTTP."""
    import urllib.request
    import urllib.error

    def _get(url, timeout=3):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace") if e.fp else ""
        except Exception as e:
            return 0, f""

    result = {"healthy": None, "status_body": "", "voice_body": "", "model_used_recent": None}

    code, body = _get(MAX_HEALTH)
    result["healthy"] = code == 200
    result["health_status_code"] = code
    result["health_body_snippet"] = body[:200] if body else ""

    code, body = _get(MAX_STATUS)
    if code == 200:
        try:
            status = json.loads(body)
            result["status_body"] = status
            result["current_commit"] = status.get("current_commit", {}).get("hash")
            result["runtime_lane"] = status.get("runtime_lane", {}).get("worktree")
            result["registry"] = status.get("registry")
        except Exception as e:
            result["status_body"] = f"<unparseable: {e}>"
    else:
        result["status_body"] = f"<HTTP {code}>"

    code, body = _get(MAX_VOICE)
    if code == 200:
        try:
            voice = json.loads(body)
            result["voice_body"] = voice
            # Surface the most important truth bits
            tts = voice.get("tts_provider", {})
            stt = voice.get("stt_provider", {})
            result["voice_summary"] = voice.get("summary") or voice.get("overall_status") or ""
            result["tts_status"] = tts.get("last_status")
            result["tts_error_snippet"] = (tts.get("last_error") or "")[:200]
            result["stt_status"] = stt.get("last_status")
            tg_text = voice.get("telegram_text_send", {})
            result["telegram_text_configured"] = tg_text.get("configured")
            result["telegram_text_env_keys"] = list((tg_text.get("env_keys") or {}).keys())
        except Exception as e:
            result["voice_body"] = f"<unparseable: {e}>"
    else:
        result["voice_body"] = f"<HTTP {code}>"

    return result


# ── Build the JSON truth ─────────────────────────────────────────────────

def build_sync_json() -> dict:
    """Compose the operational truth JSON. This is the single source."""
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()

    canonical = probe_git_state(CANONICAL_REPO)
    stale = probe_git_state(OTHER_REPO)
    oc_proc = probe_opencode_process()
    oc_db = probe_opencode_db()
    hermes = probe_hermes()
    max_be = probe_max_backend()

    # ── Decisions: blocking vs non-blocking ────────────────────────────

    blocking: list[str] = []
    non_blocking: list[str] = []
    confirmed_facts: list[str] = []
    inferences: list[str] = []

    # 1. Harry session in canonical repo?
    newest_session_dir = None
    if oc_db.get("newest_sessions"):
        newest_session_dir = oc_db["newest_sessions"][0].get("directory")
    if newest_session_dir and newest_session_dir != CANONICAL_REPO:
        blocking.append(
            f"Harry newest session cwd = {newest_session_dir!r}, not canonical {CANONICAL_REPO!r}. "
            f"Any file edit would go to the wrong repo."
        )
    elif newest_session_dir == CANONICAL_REPO:
        confirmed_facts.append(
            f"Newest Harry session cwd is canonical ({CANONICAL_REPO})."
        )

    # 2. M3 model drift
    if max_be.get("current_commit") and max_be.get("current_commit") != canonical.get("head"):
        # The current_commit field is the backend's source-of-truth for what
        # code it's running, separate from the git HEAD of the worktree.
        confirmed_facts.append(
            f"Backend running commit = {max_be.get('current_commit')}; "
            f"git HEAD = {canonical.get('head')}."
        )
    # Check for M2.7 vs M3 in voice status (model_used isn't always surfaced there)
    tts_err = (max_be.get("tts_error_snippet") or "").lower()
    if "credits" in tts_err or "spending limit" in tts_err or "429" in tts_err:
        non_blocking.append(
            "xAI TTS is 429 (monthly credit cap) — non-blocking now that MiniMax is primary."
        )

    # 3. Telegram chat id label in voice truth
    tg_keys = max_be.get("telegram_text_env_keys") or []
    if "TELEGRAM_FOUNDER_CHAT_ID" not in tg_keys:
        if "FOUNDER_TELEGRAM_CHAT_ID" in tg_keys or "TELEGRAM_CHAT_ID" in tg_keys:
            non_blocking.append(
                "voice_capability_truth env_keys uses legacy var name; canonical is TELEGRAM_FOUNDER_CHAT_ID."
            )

    # 4. Hermes doctor warnings
    if not hermes.get("doctor_clean"):
        non_blocking.append("hermes doctor reports warnings (config version, login, etc.)")

    # 5. OpenCode DB missing canonical project row
    canonical_in_db = any(
        proj.get("worktree") == CANONICAL_REPO for proj in oc_db.get("projects", [])
    )
    if not canonical_in_db:
        non_blocking.append(
            f"OpenCode project DB has no row with worktree={CANONICAL_REPO!r}. "
            f"iPhone UI workspace picker may not list canonical."
        )

    # 6. Inferences
    if max_be.get("current_commit") and canonical.get("head"):
        if max_be.get("current_commit") == canonical.get("head"):
            inferences.append(
                "Backend runtime commit matches the canonical git HEAD; "
                "no restart is needed for in-flight work to take effect."
            )
        else:
            non_blocking.append(
                f"Backend runtime commit ({max_be.get('current_commit')}) differs from "
                f"git HEAD ({canonical.get('head')}); a backend restart will reconcile."
            )

    # 7. Recommended next action
    if blocking:
        recommended = "Address blocking mismatches above; do not edit production MAX until cleared."
    elif non_blocking:
        recommended = "Pilot operational. Resolve non-blocking mismatches opportunistically."
    else:
        recommended = "Pilot operational. Continue with next planned task."

    return {
        "schema_version": 1,
        "pilot_status": "active",
        "last_checked_at": now,
        "canonical_repo": CANONICAL_REPO,
        "stale_repo": OTHER_REPO,
        "backend_commit": max_be.get("current_commit") or canonical.get("head"),
        "git_head": canonical.get("head"),
        "hermes_desktop": {
            "version": hermes.get("version"),
            "doctor_clean": hermes.get("doctor_clean"),
            "doctor_lines": hermes.get("doctor_lines", []),
        },
        "harry_opencode": {
            "service": oc_proc,
            "db": {
                "exists": oc_db.get("exists"),
                "projects": oc_db.get("projects", []),
                "newest_session_directory": newest_session_dir,
                "newest_sessions": oc_db.get("newest_sessions", []),
            },
            "canonical_repo_registered": canonical_in_db,
        },
        "max_backend": {
            "healthy": max_be.get("healthy"),
            "current_commit": max_be.get("current_commit"),
            "runtime_lane": max_be.get("runtime_lane"),
            "registry": max_be.get("registry"),
            "voice_summary": max_be.get("voice_summary"),
            "tts_status": max_be.get("tts_status"),
            "tts_error_snippet": max_be.get("tts_error_snippet"),
            "stt_status": max_be.get("stt_status"),
            "telegram_text_configured": max_be.get("telegram_text_configured"),
            "telegram_text_env_keys": max_be.get("telegram_text_env_keys"),
        },
        "blocking_mismatches": blocking,
        "non_blocking_mismatches": non_blocking,
        "confirmed_facts": confirmed_facts,
        "inferences": inferences,
        "recommended_next_action": recommended,
    }


# ── Render the HTML ───────────────────────────────────────────────────────

def render_html(sync: dict) -> str:
    """Render the HTML view from the JSON dict. Single source of truth."""
    last = sync.get("last_checked_at", "")
    pilot = sync.get("pilot_status", "unknown")
    canonical = sync.get("canonical_repo", "")
    blocking = sync.get("blocking_mismatches", [])
    non_blocking = sync.get("non_blocking_mismatches", [])
    confirmed = sync.get("confirmed_facts", [])
    inferences = sync.get("inferences", [])
    recommended = sync.get("recommended_next_action", "")

    if blocking:
        verdict_class = "status-fail"
        verdict_label = "FAIL"
    elif non_blocking:
        verdict_class = "status-warn"
        verdict_label = "WARN"
    else:
        verdict_class = "status-ok"
        verdict_label = "PASS"

    hermes = sync.get("hermes_desktop", {})
    harry = sync.get("harry_opencode", {})
    max_be = sync.get("max_backend", {})

    def _esc(s):
        return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    projects_rows = "".join(
        f"<tr><td><code>{_esc(p.get('project_id', ''))}</code></td><td><code>{_esc(p.get('worktree', ''))}</code></td></tr>"
        for p in harry.get("db", {}).get("projects", [])
    ) or "<tr><td colspan='2'><em>no projects registered</em></td></tr>"

    sessions_rows = "".join(
        f"<tr><td><code>{_esc(s.get('last_updated', ''))}</code></td><td><code>{_esc(s.get('directory', ''))}</code></td></tr>"
        for s in harry.get("db", {}).get("newest_sessions", [])
    ) or "<tr><td colspan='2'><em>no sessions</em></td></tr>"

    blocking_items = "".join(f"<li>{_esc(b)}</li>" for b in blocking) or "<li><em>none</em></li>"
    nonblocking_items = "".join(f"<li>{_esc(nb)}</li>" for nb in non_blocking) or "<li><em>none</em></li>"
    confirmed_items = "".join(f"<li>{_esc(c)}</li>" for c in confirmed) or "<li><em>none</em></li>"
    inference_items = "".join(f"<li>{_esc(i)}</li>" for i in inferences) or "<li><em>none</em></li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hermes ↔ Harry Sync — {pilot}</title>
<style>
:root {{ --ok:#16a34a; --warn:#ca8a04; --fail:#dc2626; --bg:#0a0a0a; --panel:#1a1a1a; --fg:#f5f5f5; --muted:#9ca3af; }}
body {{ background:var(--bg); color:var(--fg); font-family: ui-monospace, "SF Mono", Menlo, monospace; margin:24px; line-height:1.5; }}
h1 {{ font-size:1.4em; margin-bottom:8px; }}
h2 {{ font-size:1.1em; margin:0 0 8px 0; border-bottom:1px solid #333; padding-bottom:4px; }}
table {{ width:100%; border-collapse:collapse; margin:8px 0; }}
th, td {{ text-align:left; padding:4px 8px; border-bottom:1px solid #2a2a2a; vertical-align:top; }}
th {{ color:var(--muted); font-weight:normal; width:30%; }}
code {{ background:#000; padding:1px 5px; border-radius:3px; color:#e5e7eb; font-size:0.95em; }}
em {{ color:var(--muted); }}
.panel {{ background:var(--panel); border-radius:6px; padding:14px 18px; margin:14px 0; }}
.status-ok   {{ color:var(--ok);   font-weight:bold; }}
.status-warn {{ color:var(--warn); font-weight:bold; }}
.status-fail {{ color:var(--fail); font-weight:bold; }}
.pill {{ display:inline-block; padding:2px 10px; border-radius:10px; font-size:0.85em; margin-right:6px; }}
.pill-ok   {{ background:var(--ok);   color:#000; }}
.pill-warn {{ background:var(--warn); color:#000; }}
.pill-fail {{ background:var(--fail); color:#fff; }}
.footer {{ color:var(--muted); font-size:0.85em; margin-top:24px; }}
ul {{ padding-left:20px; margin:6px 0; }}
li {{ margin:3px 0; }}
</style>
</head>
<body>

<h1>Hermes ↔ Harry Sync Status</h1>
<p>
<span class="pill pill-{verdict_class.replace('status-', '')}">{verdict_label}</span>
Pilot status: <code>{_esc(pilot)}</code>
&nbsp;·&nbsp; Last checked: <code>{_esc(last)}</code>
&nbsp;·&nbsp; Canonical repo: <code>{_esc(canonical)}</code>
</p>

<div class="panel">
<h2>Hermes Desktop</h2>
<table>
<tr><th>Version</th><td><code>{_esc(hermes.get('version', 'unknown'))}</code></td></tr>
<tr><th>Doctor</th><td>{"clean" if hermes.get('doctor_clean') else "warnings present"}</td></tr>
</table>
</div>

<div class="panel">
<h2>Harry / OpenCode</h2>
<table>
<tr><th>Service</th><td>{_esc(harry.get('service', {}).get('service_active_word', 'inactive'))}</td></tr>
<tr><th>Last journal line</th><td><code>{_esc(harry.get('service', {}).get('last_journal_line', '')[:200])}</code></td></tr>
<tr><th>Canonical repo registered</th><td>{"yes" if harry.get('canonical_repo_registered') else "<span class='status-fail'>no</span>"}</td></tr>
<tr><th>Newest session directory</th><td><code>{_esc(harry.get('db', {}).get('newest_session_directory', '(none)'))}</code></td></tr>
</table>
<h3 style="font-size:0.95em; margin-top:14px; color:var(--muted);">Projects known to opencode</h3>
<table>
<tr><th>project_id</th><th>worktree</th></tr>
{projects_rows}
</table>
<h3 style="font-size:0.95em; margin-top:14px; color:var(--muted);">Newest 5 sessions</h3>
<table>
<tr><th>last updated</th><th>directory</th></tr>
{sessions_rows}
</table>
</div>

<div class="panel">
<h2>MAX Backend</h2>
<table>
<tr><th>Healthy</th><td>{("yes" if max_be.get('healthy') else "<span class='status-fail'>no</span>")}</td></tr>
<tr><th>Current commit</th><td><code>{_esc(max_be.get('current_commit', 'unknown'))}</code></td></tr>
<tr><th>Runtime lane</th><td><code>{_esc(max_be.get('runtime_lane', 'unknown'))}</code></td></tr>
<tr><th>Voice summary</th><td><code>{_esc(max_be.get('voice_summary', ''))}</code></td></tr>
<tr><th>TTS provider status</th><td><code>{_esc(max_be.get('tts_status', 'unknown'))}</code></td></tr>
<tr><th>STT provider status</th><td><code>{_esc(max_be.get('stt_status', 'unknown'))}</code></td></tr>
<tr><th>Telegram text configured</th><td>{_esc(max_be.get('telegram_text_configured', 'unknown'))}</td></tr>
<tr><th>Telegram env keys</th><td>{", ".join("<code>" + _esc(k) + "</code>" for k in (max_be.get('telegram_text_env_keys') or [])) or "<em>(empty)</em>"}</td></tr>
</table>
</div>

<div class="panel">
<h2 class="status-fail">Blocking mismatches</h2>
<ul>{blocking_items}</ul>
</div>

<div class="panel">
<h2 class="status-warn">Non-blocking warnings</h2>
<ul>{nonblocking_items}</ul>
</div>

<div class="panel">
<h2>Confirmed facts</h2>
<ul>{confirmed_items}</ul>
</div>

<div class="panel">
<h2>Inferences</h2>
<ul>{inference_items}</ul>
</div>

<div class="panel">
<h2>Recommended next action</h2>
<p>{_esc(recommended)}</p>
</div>

<div class="footer">
JSON: <a href="./HERMES_HARRY_SYNC.json" style="color:var(--muted);">HERMES_HARRY_SYNC.json</a>
&nbsp;·&nbsp; Markdown fallback: <a href="../../HERMES-HARRY-HANDOFF.md" style="color:var(--muted);">HERMES-HARRY-HANDOFF.md</a>
&nbsp;·&nbsp; This is a pilot program. Do not assume it replaces broader MAX/Hermes memory.
</div>

</body>
</html>
"""


# ── Render the Markdown fallback ──────────────────────────────────────────

def render_markdown(sync: dict) -> str:
    last = sync.get("last_checked_at", "")
    pilot = sync.get("pilot_status", "unknown")
    canonical = sync.get("canonical_repo", "")
    blocking = sync.get("blocking_mismatches", [])
    non_blocking = sync.get("non_blocking_mismatches", [])
    recommended = sync.get("recommended_next_action", "")
    head = sync.get("git_head", "")
    max_commit = sync.get("backend_commit", "")

    if blocking:
        verdict = "❌ FAIL"
    elif non_blocking:
        verdict = "⚠ WARN"
    else:
        verdict = "✅ PASS"

    block_md = "\n".join(f"1. {b}" for b in blocking) or "_(none)_"
    non_md = "\n".join(f"- {nb}" for nb in non_blocking) or "_(none)_"

    return f"""# Hermes ↔ Harry Handoff

_Last checked: `{last}`. Pilot status: **{pilot}**._

## Status: {verdict}

- Canonical repo: `{canonical}` @ `{head}`
- Backend current_commit: `{max_commit}`
- Newest Harry session: `{sync.get('harry_opencode', {}).get('db', {}).get('newest_session_directory', '(none)')}`

## Blocking Mismatches
{block_md}

## Non-blocking warnings
{non_md}

## Next action
{recommended}

## Artifacts
- HTML: [`.empire/runtime/HERMES_HARRY_SYNC.html`](./.empire/runtime/HERMES_HARRY_SYNC.html)
- JSON: [`.empire/runtime/HERMES_HARRY_SYNC.json`](./.empire/runtime/HERMES_HARRY_SYNC.json)

_This is a pilot program. Do not assume broader MAX/Hermes memory migration is approved._
"""


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> int:
    print("== Building Hermes ↔ Harry sync artifact ==", file=sys.stderr)
    sync = build_sync_json()

    json_text = json.dumps(sync, indent=2, sort_keys=False)
    html_text = render_html(sync)
    md_text = render_markdown(sync)

    _atomic_write(JSON_PATH, json_text)
    print(f"  wrote {JSON_PATH} ({len(json_text)} bytes)", file=sys.stderr)
    _atomic_write(HTML_PATH, html_text)
    print(f"  wrote {HTML_PATH} ({len(html_text)} bytes)", file=sys.stderr)
    _atomic_write(MD_PATH, md_text)
    print(f"  wrote {MD_PATH} ({len(md_text)} bytes)", file=sys.stderr)

    # Brief stdout summary
    print(json.dumps({
        "wrote": [str(JSON_PATH), str(HTML_PATH), str(MD_PATH)],
        "blocking": len(sync["blocking_mismatches"]),
        "non_blocking": len(sync["non_blocking_mismatches"]),
        "pilot_status": sync["pilot_status"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
