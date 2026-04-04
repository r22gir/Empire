"""
MAX Autonomous Maintenance Manager
───────────────────────────────────
Parses the productivity roadmap, queues tasks into maintenance_log,
and executes safe fixes with canary testing + git commit/revert.

Tables (already created):
  - maintenance_log: task tracking with status lifecycle
  - maintenance_config: key/value settings store
"""

import os
import re
import json
import sqlite3
import subprocess
from datetime import datetime, date
from typing import Optional

DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")
REPO_PATH = os.path.expanduser("~/empire-repo")
ROADMAP_PATH = os.path.join(REPO_PATH, ".session-artifacts/audit/productivity_roadmap.md")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Roadmap Ingestion ────────────────────────────────────────────────

def ingest_roadmap() -> dict:
    """Parse productivity_roadmap.md and insert items into maintenance_log.

    Idempotent — skips existing task_keys.
    Returns {inserted: int, skipped: int, errors: list}.
    """
    if not os.path.exists(ROADMAP_PATH):
        return {"inserted": 0, "skipped": 0, "errors": [f"Roadmap not found: {ROADMAP_PATH}"]}

    with open(ROADMAP_PATH, "r") as f:
        content = f.read()

    items = _parse_roadmap(content)
    inserted = 0
    skipped = 0
    errors = []
    conn = _get_conn()

    for item in items:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO maintenance_log
                   (task_key, title, description, bucket, source_artifact, status,
                    approval_required, priority, productivity_area, user_visible_change)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
                (
                    item["task_key"],
                    item["title"],
                    item.get("description", ""),
                    item["bucket"],
                    "productivity_roadmap.md",
                    1 if item["bucket"] != "bucket_1" else 0,  # bucket 1 = auto-approve
                    item.get("priority", 0),
                    item.get("area", ""),
                    item.get("user_visible", 0),
                ),
            )
            if conn.total_changes:
                # Check if it was actually inserted (IGNORE means no error on dup)
                row = conn.execute(
                    "SELECT id FROM maintenance_log WHERE task_key = ?", (item["task_key"],)
                ).fetchone()
                if row:
                    inserted += 1
                else:
                    skipped += 1
            skipped += 0  # OR IGNORE silently skips duplicates
        except Exception as e:
            errors.append(f"{item['task_key']}: {e}")

    conn.commit()
    # Recount accurately
    total_in_db = conn.execute("SELECT COUNT(*) FROM maintenance_log").fetchone()[0]
    conn.close()

    return {
        "inserted": inserted,
        "skipped": len(items) - inserted,
        "total_items_parsed": len(items),
        "total_in_db": total_in_db,
        "errors": errors,
    }


def _parse_roadmap(content: str) -> list:
    """Extract structured items from the roadmap markdown."""
    items = []
    current_bucket = None
    bucket_map = {
        "bucket 1": "bucket_1",
        "fix immediately": "bucket_1",
        "bucket 2": "bucket_2",
        "high-value": "bucket_2",
        "bucket 3": "bucket_3",
        "good overlap": "bucket_3",
        "bucket 4": "bucket_4",
        "overlap to consolidate": "bucket_4",
        "bucket 5": "bucket_5",
        "dead features": "bucket_5",
        "bucket 6": "bucket_6",
        "missing features": "bucket_6",
    }

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect bucket headers
        if line.startswith("## "):
            header_lower = line.lower()
            for key, bucket in bucket_map.items():
                if key in header_lower:
                    current_bucket = bucket
                    break

        # Detect numbered items: "1. **Title** — description"
        match = re.match(r'^\d+\.\s+\*\*(.+?)\*\*\s*[—–-]\s*(.+)', line)
        if match and current_bucket:
            title = match.group(1).strip()
            description = match.group(2).strip()

            # Collect sub-lines (indented lines after this item)
            sub_lines = []
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("- "):
                sub_lines.append(lines[j].strip().lstrip("- "))
                j += 1

            full_desc = description
            if sub_lines:
                full_desc += "\n" + "\n".join(sub_lines)

            task_key = _make_task_key(current_bucket, title)
            priority = _bucket_priority(current_bucket)

            items.append({
                "task_key": task_key,
                "title": title,
                "description": full_desc,
                "bucket": current_bucket,
                "priority": priority,
                "area": _detect_area(title, description),
                "user_visible": 1 if current_bucket in ("bucket_1", "bucket_5") else 0,
            })

        # Detect table rows: "| Feature | Action | Priority |"
        if current_bucket and line.startswith("|") and not line.startswith("|--") and not line.startswith("| Feature"):
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) >= 2:
                title = cols[0]
                action = cols[1]
                task_key = _make_task_key(current_bucket, title)
                items.append({
                    "task_key": task_key,
                    "title": title,
                    "description": action,
                    "bucket": current_bucket,
                    "priority": _bucket_priority(current_bucket),
                    "area": _detect_area(title, action),
                    "user_visible": 1,
                })

        i += 1

    return items


def _make_task_key(bucket: str, title: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')[:60]
    return f"{bucket}_{slug}"


def _bucket_priority(bucket: str) -> int:
    return {"bucket_1": 10, "bucket_2": 8, "bucket_3": 5, "bucket_4": 5, "bucket_5": 3, "bucket_6": 2}.get(bucket, 1)


def _detect_area(title: str, desc: str) -> str:
    combined = (title + " " + desc).lower()
    if any(k in combined for k in ("import", "dead", "remove")):
        return "cleanup"
    if any(k in combined for k in ("calendar", "video", "screen")):
        return "ui"
    if any(k in combined for k in ("cron", "auto", "campaign")):
        return "automation"
    if any(k in combined for k in ("search", "navigation")):
        return "ux"
    return "general"


# ── Task Retrieval ───────────────────────────────────────────────────

def get_next_task() -> Optional[dict]:
    """Return the next task to execute.

    Priority: bucket_1 pending → bucket_2 approved → bucket_2 pending (needs approval).
    """
    conn = _get_conn()

    # 1. Bucket 1 pending (auto-execute, no approval needed)
    row = conn.execute(
        """SELECT * FROM maintenance_log
           WHERE bucket = 'bucket_1' AND status = 'pending'
           ORDER BY priority DESC, id ASC LIMIT 1"""
    ).fetchone()
    if row:
        conn.close()
        return {"task": dict(row), "action": "auto_execute", "reason": "Bucket 1 fix — auto-approved"}

    # 2. Bucket 2 approved
    row = conn.execute(
        """SELECT * FROM maintenance_log
           WHERE bucket = 'bucket_2' AND status = 'approved'
           ORDER BY priority DESC, id ASC LIMIT 1"""
    ).fetchone()
    if row:
        conn.close()
        return {"task": dict(row), "action": "auto_execute", "reason": "Bucket 2 task — founder-approved"}

    # 3. Bucket 2 pending (needs approval)
    row = conn.execute(
        """SELECT * FROM maintenance_log
           WHERE bucket = 'bucket_2' AND status = 'pending'
           ORDER BY priority DESC, id ASC LIMIT 1"""
    ).fetchone()
    if row:
        conn.close()
        return {"task": dict(row), "action": "request_approval", "reason": "Bucket 2 task — needs founder approval"}

    # 4. Any other pending/approved task
    row = conn.execute(
        """SELECT * FROM maintenance_log
           WHERE status IN ('pending', 'approved')
           ORDER BY priority DESC, id ASC LIMIT 1"""
    ).fetchone()
    if row:
        conn.close()
        action = "auto_execute" if row["status"] == "approved" or row["approval_required"] == 0 else "request_approval"
        return {"task": dict(row), "action": action, "reason": f"{row['bucket']} task"}

    conn.close()
    return None


def get_pending_tasks(bucket: str = None) -> list:
    """List pending/approved tasks, optionally filtered by bucket."""
    conn = _get_conn()
    if bucket:
        rows = conn.execute(
            """SELECT * FROM maintenance_log
               WHERE status IN ('pending', 'approved') AND bucket = ?
               ORDER BY priority DESC, id ASC""",
            (bucket,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM maintenance_log
               WHERE status IN ('pending', 'approved')
               ORDER BY priority DESC, id ASC"""
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_completed_today() -> list:
    """Tasks done/failed/reverted today."""
    conn = _get_conn()
    today = date.today().isoformat()
    rows = conn.execute(
        """SELECT * FROM maintenance_log
           WHERE status IN ('done', 'failed', 'reverted')
             AND DATE(updated_at) = ?
           ORDER BY updated_at DESC""",
        (today,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_maintenance_history(limit: int = 20) -> list:
    """Recent maintenance history."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT * FROM maintenance_log
           ORDER BY updated_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_maintenance_status() -> dict:
    """Summary: enabled, last_run, pending counts, done/failed/reverted counts."""
    conn = _get_conn()

    enabled_row = conn.execute(
        "SELECT value FROM maintenance_config WHERE key = 'enabled'"
    ).fetchone()
    enabled = (enabled_row["value"] if enabled_row else "true") == "true"

    last_run_row = conn.execute(
        "SELECT value FROM maintenance_config WHERE key = 'last_run'"
    ).fetchone()
    last_run = last_run_row["value"] if last_run_row else None

    counts = {}
    for status in ("pending", "approved", "running", "done", "failed", "reverted"):
        row = conn.execute(
            "SELECT COUNT(*) as c FROM maintenance_log WHERE status = ?", (status,)
        ).fetchone()
        counts[status] = row["c"]

    bucket_counts = {}
    for b in ("bucket_1", "bucket_2", "bucket_3", "bucket_4", "bucket_5", "bucket_6"):
        row = conn.execute(
            "SELECT COUNT(*) as c FROM maintenance_log WHERE bucket = ? AND status IN ('pending', 'approved')", (b,)
        ).fetchone()
        if row["c"] > 0:
            bucket_counts[b] = row["c"]

    conn.close()

    return {
        "enabled": enabled,
        "last_run": last_run,
        "counts": counts,
        "pending_by_bucket": bucket_counts,
        "total_tasks": sum(counts.values()),
    }


# ── Task Approval ────────────────────────────────────────────────────

def approve_task(task_key: str) -> dict:
    """Approve a pending task for execution."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM maintenance_log WHERE task_key = ?", (task_key,)
    ).fetchone()

    if not row:
        conn.close()
        return {"success": False, "error": f"Task not found: {task_key}"}

    if row["status"] != "pending":
        conn.close()
        return {"success": False, "error": f"Task is '{row['status']}', not pending"}

    conn.execute(
        "UPDATE maintenance_log SET status = 'approved', approved_by = 'founder', updated_at = ? WHERE task_key = ?",
        (datetime.now().isoformat(), task_key),
    )
    conn.commit()
    conn.close()
    return {"success": True, "task_key": task_key, "status": "approved"}


# ── Toggle ───────────────────────────────────────────────────────────

def toggle_maintenance(enabled: bool) -> dict:
    """Enable or disable maintenance execution."""
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO maintenance_config (key, value, updated_at) VALUES ('enabled', ?, ?)",
        ("true" if enabled else "false", datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"enabled": enabled}


# ── Execution Engine ─────────────────────────────────────────────────

def execute_maintenance_task(task_id: int = None, task_key: str = None) -> dict:
    """Execute a maintenance task with canary testing and git safety.

    If neither task_id nor task_key provided, executes the next auto-executable task.
    Lifecycle: pending/approved → running → (fix + canary) → done | failed | reverted.
    """
    # Check if enabled
    conn = _get_conn()
    enabled_row = conn.execute(
        "SELECT value FROM maintenance_config WHERE key = 'enabled'"
    ).fetchone()
    if enabled_row and enabled_row["value"] == "false":
        conn.close()
        return {"success": False, "error": "Maintenance is disabled"}

    # Find the task
    if task_key:
        row = conn.execute("SELECT * FROM maintenance_log WHERE task_key = ?", (task_key,)).fetchone()
    elif task_id:
        row = conn.execute("SELECT * FROM maintenance_log WHERE id = ?", (task_id,)).fetchone()
    else:
        # Get next auto-executable
        conn.close()
        next_info = get_next_task()
        if not next_info or next_info["action"] != "auto_execute":
            return {"success": False, "error": "No auto-executable tasks available"}
        task_key = next_info["task"]["task_key"]
        conn = _get_conn()
        row = conn.execute("SELECT * FROM maintenance_log WHERE task_key = ?", (task_key,)).fetchone()

    if not row:
        conn.close()
        return {"success": False, "error": "Task not found"}

    task = dict(row)

    if task["status"] not in ("pending", "approved"):
        conn.close()
        return {"success": False, "error": f"Task status is '{task['status']}', must be pending or approved"}

    # Bucket 2+ requires approval
    if task["approval_required"] and task["status"] != "approved":
        conn.close()
        return {"success": False, "error": "Task requires approval before execution", "task_key": task["task_key"]}

    # Mark running
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE maintenance_log SET status = 'running', started_at = ?, updated_at = ? WHERE id = ?",
        (now, now, task["id"]),
    )
    conn.commit()
    conn.close()

    # Execute the fix
    try:
        fix_result = _execute_fix(task)
    except Exception as e:
        _update_task_status(task["id"], "failed", error=str(e))
        return {"success": False, "error": str(e), "task_key": task["task_key"]}

    if not fix_result.get("executed"):
        _update_task_status(
            task["id"], "done",
            result_summary=fix_result.get("message", "Logged — needs Code Mode"),
        )
        return {"success": True, "task_key": task["task_key"], "result": fix_result}

    # Run canary tests
    canary = _run_canary_tests()

    if canary["passed"]:
        # Commit the fix
        commit_hash = _git_commit(f"[maintenance] {task['title']}", fix_result.get("files_touched", []))
        _update_task_status(
            task["id"], "done",
            commit_hash=commit_hash,
            result_summary=fix_result.get("message", "Fix applied"),
            files_touched=fix_result.get("files_touched"),
            tests_run=json.dumps(canary["results"]),
        )
        # Update last_run
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO maintenance_config (key, value, updated_at) VALUES ('last_run', ?, ?)",
            (datetime.now().isoformat(), datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "task_key": task["task_key"],
            "commit_hash": commit_hash,
            "canary": canary,
            "result": fix_result,
        }
    else:
        # Canary failed — revert
        revert_hash = _git_revert(fix_result.get("files_touched", []))
        _update_task_status(
            task["id"], "reverted",
            revert_hash=revert_hash,
            result_summary="Canary failed — reverted",
            error=json.dumps(canary["results"]),
            tests_run=json.dumps(canary["results"]),
        )
        return {
            "success": False,
            "task_key": task["task_key"],
            "revert_hash": revert_hash,
            "canary": canary,
            "error": "Canary tests failed — changes reverted",
        }


def revert_last_maintenance() -> dict:
    """Git revert the last completed maintenance task."""
    conn = _get_conn()
    row = conn.execute(
        """SELECT * FROM maintenance_log
           WHERE status = 'done' AND commit_hash IS NOT NULL
           ORDER BY completed_at DESC LIMIT 1"""
    ).fetchone()

    if not row:
        conn.close()
        return {"success": False, "error": "No completed tasks with commits to revert"}

    task = dict(row)
    commit = task["commit_hash"]

    try:
        result = subprocess.run(
            ["git", "revert", "--no-edit", commit],
            capture_output=True, text=True, cwd=REPO_PATH, timeout=30,
        )
        if result.returncode != 0:
            conn.close()
            return {"success": False, "error": f"git revert failed: {result.stderr}"}

        revert_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=REPO_PATH, timeout=10,
        ).stdout.strip()

        conn.execute(
            "UPDATE maintenance_log SET status = 'reverted', revert_hash = ?, updated_at = ? WHERE id = ?",
            (revert_hash, datetime.now().isoformat(), task["id"]),
        )
        conn.commit()
        conn.close()

        return {"success": True, "task_key": task["task_key"], "reverted_commit": commit, "revert_hash": revert_hash}

    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}


# ── Fix Handlers ─────────────────────────────────────────────────────

def _execute_fix(task: dict) -> dict:
    """Route to specific fix handlers based on task title keywords."""
    title_lower = task["title"].lower()

    if "dead import" in title_lower or "remove" in title_lower and "import" in title_lower:
        return _fix_dead_imports(task)

    if "calendar" in title_lower:
        return _log_needs_code_mode(task, "Calendar fix requires UI changes — needs Code Mode")

    if "cron" in title_lower or "campaign" in title_lower:
        return _log_needs_code_mode(task, "Cron/campaign automation — needs Code Mode")

    if "video" in title_lower:
        return _log_needs_code_mode(task, "Video call feature — needs Code Mode")

    if "search" in title_lower or "navigation" in title_lower:
        return _log_needs_code_mode(task, "Search/navigation feature — needs Code Mode")

    # Default: log as needs code mode
    return _log_needs_code_mode(task, f"Task '{task['title']}' requires manual implementation — needs Code Mode")


def _fix_dead_imports(task: dict) -> dict:
    """Remove dead LeadForgePage/RelistAppScreen imports from page.tsx files."""
    import glob

    patterns = ["LeadForgePage", "RelistAppScreen"]
    files_touched = []
    changes = []

    # Find page.tsx files in the command center
    cc_path = os.path.join(REPO_PATH, "empire-command-center")
    page_files = glob.glob(os.path.join(cc_path, "**", "page.tsx"), recursive=True)

    for filepath in page_files:
        try:
            with open(filepath, "r") as f:
                original = f.read()

            modified = original
            for pattern in patterns:
                # Remove import lines containing the pattern
                lines = modified.split("\n")
                filtered = []
                removed = False
                for line in lines:
                    if pattern in line and ("import" in line.lower() or "from" in line.lower()):
                        changes.append(f"Removed '{pattern}' import from {os.path.relpath(filepath, REPO_PATH)}")
                        removed = True
                        continue
                    filtered.append(line)
                if removed:
                    modified = "\n".join(filtered)

            if modified != original:
                with open(filepath, "w") as f:
                    f.write(modified)
                files_touched.append(os.path.relpath(filepath, REPO_PATH))

        except Exception as e:
            changes.append(f"Error processing {filepath}: {e}")

    if files_touched:
        return {
            "executed": True,
            "message": f"Removed dead imports from {len(files_touched)} file(s)",
            "files_touched": files_touched,
            "changes": changes,
        }
    else:
        return {
            "executed": False,
            "message": "No dead imports found — already clean or pattern not matched",
        }


def _log_needs_code_mode(task: dict, reason: str) -> dict:
    """Log a task as needing Code Mode (manual implementation)."""
    return {
        "executed": False,
        "message": reason,
        "needs_code_mode": True,
    }


# ── Git Helpers ──────────────────────────────────────────────────────

def _git_commit(message: str, files: list = None) -> Optional[str]:
    """Stage files and commit. Returns commit hash or None."""
    try:
        if files:
            for f in files:
                subprocess.run(["git", "add", f], cwd=REPO_PATH, capture_output=True, timeout=10)
        else:
            subprocess.run(["git", "add", "-A"], cwd=REPO_PATH, capture_output=True, timeout=10)

        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True, cwd=REPO_PATH, timeout=30,
        )
        if result.returncode != 0:
            print(f"[maintenance] git commit failed: {result.stderr}")
            return None

        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=REPO_PATH, timeout=10,
        )
        return hash_result.stdout.strip()
    except Exception as e:
        print(f"[maintenance] git commit error: {e}")
        return None


def _git_revert(files: list = None) -> Optional[str]:
    """Revert unstaged changes or last commit. Returns revert hash or None."""
    try:
        if files:
            for f in files:
                subprocess.run(["git", "checkout", "--", f], cwd=REPO_PATH, capture_output=True, timeout=10)
        else:
            # Revert last commit
            subprocess.run(
                ["git", "revert", "--no-edit", "HEAD"],
                cwd=REPO_PATH, capture_output=True, timeout=30,
            )

        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=REPO_PATH, timeout=10,
        )
        return hash_result.stdout.strip()
    except Exception as e:
        print(f"[maintenance] git revert error: {e}")
        return None


# ── Canary Tests (from self_heal pattern) ────────────────────────────

def _run_canary_tests() -> dict:
    """Run canary tests — health endpoint check."""
    tests = []
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8000/health"],
            capture_output=True, text=True, timeout=10,
        )
        tests.append({"name": "backend_health", "passed": r.stdout.strip() == "200"})
    except Exception:
        tests.append({"name": "backend_health", "passed": False})

    return {"passed": all(t["passed"] for t in tests), "results": tests}


# ── Internal Helpers ─────────────────────────────────────────────────

def _update_task_status(
    task_id: int,
    status: str,
    commit_hash: str = None,
    revert_hash: str = None,
    result_summary: str = None,
    error: str = None,
    files_touched: list = None,
    tests_run: str = None,
):
    """Update a maintenance_log row."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    completed_at = now if status in ("done", "failed", "reverted") else None

    conn.execute(
        """UPDATE maintenance_log SET
            status = ?, updated_at = ?, completed_at = COALESCE(?, completed_at),
            commit_hash = COALESCE(?, commit_hash),
            revert_hash = COALESCE(?, revert_hash),
            result_summary = COALESCE(?, result_summary),
            error = COALESCE(?, error),
            files_touched = COALESCE(?, files_touched),
            tests_run = COALESCE(?, tests_run)
           WHERE id = ?""",
        (
            status, now, completed_at,
            commit_hash, revert_hash, result_summary, error,
            json.dumps(files_touched) if files_touched else None,
            tests_run,
            task_id,
        ),
    )
    conn.commit()
    conn.close()
