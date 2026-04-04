"""
MAX Self-Heal Engine — Staged, bounded, auditable.
detect → snapshot → patch → canary → commit or revert → log
"""
import subprocess, os, json, sqlite3, shutil
from datetime import datetime

DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")
REPO_PATH = os.path.expanduser("~/empire-repo")
INCIDENT_DIR = os.path.join(REPO_PATH, ".session-artifacts/self-heal/incidents")

ALLOWED_PATHS = [
    "backend/app/services/max/", "backend/app/routers/max/",
    "backend/app/services/vision/", "empire-command-center/app/",
]
BLOCKED_PATHS = [".env", "auth.py", "payments", "stripe", "main.py", "migrations/"]

AUTO_HEAL_ALLOWED = [
    "max_route_500", "renderer_failure", "tool_execution_exception",
    "capability_mismatch", "inline_drawing_regression",
]
AUTO_HEAL_BLOCKED = ["auth_failure", "payment_failure", "db_corruption", "missing_credentials"]

# Create incident table
try:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS self_heal_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trigger_type TEXT, endpoint TEXT, error_excerpt TEXT,
        files_touched TEXT, patch_summary TEXT, commit_hash TEXT,
        verification_status TEXT, revert_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()
except:
    pass

def is_path_allowed(filepath):
    rel = os.path.relpath(filepath, REPO_PATH) if os.path.isabs(filepath) else filepath
    for b in BLOCKED_PATHS:
        if b in rel: return False
    for a in ALLOWED_PATHS:
        if rel.startswith(a): return True
    return False

def _log_incident(trigger_type, endpoint, error_excerpt, files, summary, commit_hash, status, revert=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""INSERT INTO self_heal_log (trigger_type, endpoint, error_excerpt,
            files_touched, patch_summary, commit_hash, verification_status, revert_hash)
            VALUES (?,?,?,?,?,?,?,?)""",
            (trigger_type, endpoint, (error_excerpt or "")[:500], json.dumps(files),
             (summary or "")[:500], commit_hash, status, revert))
        conn.commit()
        conn.close()
    except: pass

def _run_canary_tests():
    tests = []
    try:
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8000/health"],
                          capture_output=True, text=True, timeout=10)
        tests.append({"name": "backend_health", "passed": r.stdout.strip() == "200"})
    except:
        tests.append({"name": "backend_health", "passed": False})
    return {"passed": all(t["passed"] for t in tests), "results": tests}

def get_heal_status():
    try:
        conn = sqlite3.connect(DB_PATH)
        recent = conn.execute("""SELECT trigger_type, patch_summary, commit_hash, verification_status, created_at
            FROM self_heal_log ORDER BY created_at DESC LIMIT 5""").fetchall()
        total = conn.execute("SELECT COUNT(*) FROM self_heal_log").fetchone()[0]
        passed = conn.execute("SELECT COUNT(*) FROM self_heal_log WHERE verification_status='passed'").fetchone()[0]
        conn.close()
        return {"total_incidents": total, "successful_heals": passed,
                "recent": [{"trigger": r[0], "summary": r[1], "commit": r[2], "status": r[3], "time": r[4]} for r in recent]}
    except:
        return {"total_incidents": 0, "successful_heals": 0, "recent": []}
