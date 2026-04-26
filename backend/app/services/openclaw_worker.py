"""OpenClaw Worker Loop — polls task queue, dispatches to OpenClaw, stores results.

Runs as an asyncio background task inside the FastAPI app.
One task at a time (protect EmpireDell resources).
"""

import asyncio
import json
import logging
import os
import re
import socket
import subprocess
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from app.services.max.openclaw_gate import check_openclaw_gate, write_openclaw_worker_heartbeat

log = logging.getLogger("openclaw_worker")

DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")
OPENCLAW_URL = "http://localhost:7878"
OPENCLAW_TIMEOUT = 300  # 5 min per task
CODE_TASK_TIMEOUT = int(os.getenv("OPENCLAW_CODE_TASK_TIMEOUT", str(OPENCLAW_TIMEOUT)))
POLL_INTERVAL = 30  # seconds between queue checks
ZOMBIE_TIMEOUT_MINUTES = 10  # mark running tasks as failed after this
ORPHAN_RUNNING_TIMEOUT_MINUTES = int(os.getenv("OPENCLAW_ORPHAN_TIMEOUT_MINUTES", "2"))
GENERIC_HEALTH_PORTS = (8000, 3005, 7878, 11434, 3077)


@dataclass
class ExecutionResult:
    success: bool
    executor: str
    result: str = ""
    error: str | None = None
    files_modified: list[str] = field(default_factory=list)
    commit_hash: str | None = None
    commands: list[str] = field(default_factory=list)
    tools_run: list[str] = field(default_factory=list)
    files_inspected: list[str] = field(default_factory=list)
    output_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Desk context for prompting ──────────────────────────────────────

DESK_CONTEXTS = {
    "CodeForge": "You are Atlas, the code desk. You write, test, and commit code in ~/empire-repo/. Use empire-backend and empire-frontend skills.",
    "MarketingDesk": "You are Nova, the marketing desk. You create social media content, blog posts, and marketing copy. Use empire-social skill.",
    "SupportDesk": "You are Luna, the support desk. You handle customer inquiries and update the knowledge base.",
    "ForgeDesk": "You are Kai, the workroom desk. You manage quotes, inventory, and scheduling.",
    "FinanceDesk": "You are Sage, the finance desk. You handle invoicing, payments, and financial reporting.",
    "ITDesk": "You are Orion, the IT desk. You monitor system health, manage services, and handle infrastructure.",
    "WebsiteDesk": "You are Zara, the website desk. You manage the website, SEO, and portfolio content.",
    "AnalyticsDesk": "You are Raven, the analytics desk. You produce business intelligence and revenue forecasting.",
    "QualityDesk": "You are Phoenix, the quality desk. You audit AI responses and maintain accuracy standards.",
    "SalesDesk": "You are Aria, the sales desk. You handle lead qualification and sales pipeline.",
    "ClientsDesk": "You are Elena, the clients desk. You manage customer relationships and preferences.",
    "ContractorsDesk": "You are Marcus, the contractors desk. You schedule and manage installer assignments.",
    "LegalDesk": "You are Raven, the legal desk. You handle contracts, compliance, and insurance.",
    "InnovationDesk": "You are Spark, the innovation desk. You scan markets, track competitors, and identify opportunities.",
    "LabDesk": "You are Phoenix, the lab desk. You prototype and test new features in a sandbox.",
    "IntakeDesk": "You are Zara, the intake desk. You process LuxeForge submissions and route projects.",
    "CostTracker": "You are CostTracker. You monitor AI token budgets and spending alerts.",
}


def _get_db():
    """Get a fresh database connection (thread-safe)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _get_next_task() -> dict | None:
    """Get the next queued task (highest priority, oldest first)."""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM openclaw_tasks WHERE status = 'queued' ORDER BY priority ASC, created_at ASC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _update_task(task_id: int, **kwargs):
    """Update task fields in the database."""
    if not kwargs:
        return
    conn = _get_db()
    try:
        sets = []
        params = []
        for k, v in kwargs.items():
            sets.append(f"{k} = ?")
            params.append(v)
        params.append(task_id)
        conn.execute(f"UPDATE openclaw_tasks SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
    finally:
        conn.close()


def _normalize_desk(desk: str | None) -> str:
    return str(desk or "general").strip().lower().replace(" ", "").replace("_", "")


def _task_text(task: dict) -> str:
    return " ".join(
        str(task.get(key) or "")
        for key in ("title", "description", "desk", "source")
    ).lower()


def _is_explicit_health_task(task: dict) -> bool:
    """Health summaries are allowed only when health/status/ports are the task."""
    text = _task_text(task)
    health_terms = (
        "health check",
        "status check",
        "service health",
        "services health",
        "check services",
        "check ports",
        "port status",
        "ports",
        "which services are running",
        "openclaw health",
        "backend health",
        "frontend health",
    )
    action_terms = (
        "write ",
        "create ",
        "edit ",
        "fix ",
        "change ",
        "update ",
        "modify ",
        "inspect ",
        "read ",
        "repo",
        "file",
        "code",
        "commit",
        "diagnostic",
        "handoff",
        "router",
        "worker",
    )
    return any(term in text for term in health_terms) and not any(term in text for term in action_terms)


def _is_code_task(task: dict) -> bool:
    desk = _normalize_desk(task.get("desk"))
    if desk in {"codeforge", "code", "dev", "development", "atlas"}:
        return True
    source = str(task.get("source") or "").strip().lower()
    if source in {"manual-code-task", "code-task", "code"}:
        return True
    text = _task_text(task)
    code_terms = (
        "backend/",
        "frontend/",
        ".py",
        ".ts",
        ".tsx",
        "git ",
        "pytest",
        "code task",
        "fix ",
        "fixing ",
        "implement ",
        "refactor ",
        "harden ",
        "audit ",
        "test ",
        "worker",
        "router",
        "repo",
        "drawing intent",
        "drawing_intent",
        "source grounding",
        "current-source",
    )
    return "codeforge" in text or any(term in text for term in code_terms)


def _code_execution_mode(task: dict) -> str:
    text = _task_text(task)
    read_only_hints = (
        "do not edit",
        "read-only",
        "inspect ",
        "inspect backend",
        "report whether",
        "file exists",
        "do not commit",
        "do not generate drawings",
        "do not edit files",
        "do not change files",
    )
    mutate_hints = (
        "fix ",
        "change ",
        "update ",
        "modify ",
        "harden ",
        "implement ",
        "patch ",
        "refactor ",
        "write ",
        "create ",
        "edit ",
        "ground ",
        "prevent ",
    )
    if any(hint in text for hint in read_only_hints) and not any(hint in text for hint in mutate_hints):
        return "read_only"
    return "mutate"


def _is_explicit_drawing_task(task: dict) -> bool:
    """Return True only for actual drawing generation requests."""
    if _is_code_task(task):
        return False

    desk = _normalize_desk(task.get("desk"))
    text = _task_text(task)
    drawing_verbs = (
        "generate ",
        "create ",
        "render ",
        "produce ",
        "make ",
        "draw ",
        "sketch ",
        "draft ",
        "build ",
    )
    drawing_nouns = (
        "drawing",
        "bench",
        "shop drawing",
        "technical drawing",
        "cad",
        "rendering",
        "sketch",
        "pdf drawing",
    )
    code_blocks = (
        "fix ",
        "audit ",
        "harden ",
        "test ",
        "inspect ",
        "review ",
        "debug ",
        "source grounding",
        "drawing intent",
        "drawing_intent",
    )
    if any(term in text for term in code_blocks):
        return False
    if not any(term in text for term in drawing_verbs):
        return False
    if not any(noun in text for noun in drawing_nouns):
        return False
    return True


def _is_generic_port_health_result(text: str, skill_used: str | None = None) -> bool:
    """Detect the OpenClaw services_health fallback result."""
    if skill_used == "services_health":
        return True
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return False
    port_line = re.compile(r"^\d{2,5}:\s+(ONLINE|OFFLINE)$", re.IGNORECASE)
    return all(port_line.match(line) for line in lines)


def _is_drawing_generation_result(execution: ExecutionResult) -> bool:
    text = (execution.result or "").lower()
    if execution.executor == "openclaw_worker.local_drawing_generator":
        return True
    if "openclaw_drawings" in text or "drawing generated:" in text or text.endswith(".svg"):
        return True
    return False


def _git_head() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _git_commit_exists(commit_hash: str | None) -> bool:
    if not commit_hash:
        return False
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{commit_hash}^{{commit}}"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _git_changed_files() -> set[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return set()
    if result.returncode != 0:
        return set()

    changed: set[str] = set()
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            changed.add(path)
    return changed


def _git_files_changed_between(before: str, after: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{before}..{after}"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _compose_task_result(task: dict, execution: ExecutionResult) -> str:
    lines = [
        f"Executor path used: {execution.executor}",
        "Task attempted: yes",
        f"Task ID: {task.get('id')}",
        f"Desk: {task.get('desk')}",
        f"Priority: {task.get('priority')}",
    ]
    if execution.commands:
        lines.append("Commands run: " + "; ".join(execution.commands))
    if execution.tools_run:
        lines.append("Tools/actions run: " + "; ".join(execution.tools_run[:12]))
    if execution.files_inspected:
        lines.append("Files inspected: " + ", ".join(execution.files_inspected[:12]))
    if execution.files_modified:
        lines.append("Repo files modified: " + ", ".join(execution.files_modified))
    if execution.output_path:
        lines.append(f"Output path: {execution.output_path}")
    if execution.commit_hash:
        lines.append(f"Commit hash: {execution.commit_hash}")
    else:
        lines.append("Commit hash: none")
    tool_calls = execution.metadata.get("tool_calls") if isinstance(execution.metadata, dict) else None
    if tool_calls:
        lines.append("Actual tool calls executed:")
        for call in tool_calls[:12]:
            params = call.get("params", {})
            lines.append(
                f"- {call.get('tool')} success={call.get('success')} params={params} result={call.get('result') or call.get('error')}"
            )
    verified_tests = execution.metadata.get("verified_test_runs") if isinstance(execution.metadata, dict) else None
    if verified_tests:
        lines.append("Verified tests:")
        for entry in verified_tests[:12]:
            lines.append(f"- {entry.get('tool')}: {entry.get('command')} -> {entry.get('result')}")
    notes = execution.metadata.get("verification_notes") if isinstance(execution.metadata, dict) else None
    if notes:
        lines.append("Verification notes:")
        for note in notes[:12]:
            lines.append(f"- {note}")
    lines.append("")
    lines.append((execution.result or "").strip())
    return "\n".join(lines).strip()


def _fail_running_task(task_id: int, error: str):
    _update_task(
        task_id,
        status="failed",
        error=error[:2000],
        completed_at=datetime.now().isoformat(),
    )


def _recover_orphaned_running_tasks(active_task_id: int | None = None) -> int:
    """Fail stale running rows when this worker is not actively processing them."""
    conn = _get_db()
    try:
        cutoff = (datetime.now() - timedelta(minutes=ORPHAN_RUNNING_TIMEOUT_MINUTES)).isoformat()
        params: list[Any] = [cutoff]
        active_filter = ""
        if active_task_id is not None:
            active_filter = " AND id != ?"
            params.append(active_task_id)
        result = conn.execute(
            f"""UPDATE openclaw_tasks
                SET status = 'failed',
                    error = 'Recovered orphaned running task after worker restart.',
                    completed_at = ?
                WHERE status = 'running'
                  AND (started_at IS NULL OR started_at < ?){active_filter}""",
            [datetime.now().isoformat(), *params],
        )
        if result.rowcount > 0:
            log.warning("Recovered %s orphaned running OpenClaw task(s)", result.rowcount)
        conn.commit()
        return int(result.rowcount or 0)
    finally:
        conn.close()


def _cleanup_zombies():
    """Mark tasks that have been 'running' for too long as failed."""
    conn = _get_db()
    try:
        cutoff = (datetime.now() - timedelta(minutes=ZOMBIE_TIMEOUT_MINUTES)).isoformat()
        result = conn.execute(
            """UPDATE openclaw_tasks SET status = 'failed',
               error = 'Zombie protection: running task exceeded worker timeout without completion',
               completed_at = datetime('now')
               WHERE status = 'running' AND started_at < ?""",
            (cutoff,),
        )
        if result.rowcount > 0:
            log.warning(f"Cleaned up {result.rowcount} zombie tasks")
        conn.commit()
    finally:
        conn.close()


def _build_task_prompt(task: dict) -> str:
    """Build a context-rich prompt for OpenClaw based on task + desk."""
    desk = task.get("desk", "general")
    desk_context = DESK_CONTEXTS.get(desk) or DESK_CONTEXTS.get(str(desk).strip()) or "You are a general Empire AI agent."

    return f"""{desk_context}

TASK: {task['title']}
DESCRIPTION: {task['description']}
DESK: {task.get('desk', 'general')}
PRIORITY: {task['priority']}
SOURCE: {task.get('source', 'unknown')}

RULES:
- Execute the task. Do not just describe what you would do.
- Do not substitute a generic health/status/ports summary unless this task explicitly asks for health/status/ports.
- If you need to modify files, use the filesystem MCP.
- Report execution evidence: commands/tools run, files inspected, files changed, tests/builds run, output paths, and commit hash if any.
- Do not push unless the task explicitly asks for push.
- If you're unsure about something, say "NEEDS_APPROVAL: [question]" and stop.
"""


def _build_code_task_prompt(task: dict) -> str:
    """Build the prompt sent to the local CodeTaskRunner executor."""
    execution_mode = _code_execution_mode(task)
    return f"""DB-backed OpenClaw CodeForge execution task.

Title: {task.get('title')}
Description:
{task.get('description') or ''}
Desk: {task.get('desk', 'general')}
Priority: {task.get('priority')}
Source: {task.get('source', 'unknown')}
Execution Mode: {execution_mode}

Safety rules:
- Actually execute the requested task description through available CodeTaskRunner tools.
- Use tool calls to inspect or change state; do not answer from memory.
- Do not call or delegate to OpenClaw from this task.
- Do not replace the requested work with a generic health/status/ports summary.
- Do not edit repo files when the task says not to edit repo files.
- Do not commit unless the task explicitly asks for a commit.
- Do not push.
- In the final answer include evidence: tools run, files inspected, files changed, tests/builds run, output paths, and commit hash or no commit.
"""


async def _dispatch_to_openclaw(prompt: str) -> dict:
    """Send a prompt to OpenClaw and get the response."""
    async with httpx.AsyncClient(timeout=OPENCLAW_TIMEOUT) as client:
        resp = await client.post(
            f"{OPENCLAW_URL}/chat",
            json={
                "message": prompt,
                "history": [],
                "system_prompt": "You are MAX's execution agent. Execute the task precisely. Report what you did, what changed, and what needs review.",
            },
        )

    if resp.status_code == 200:
        data = resp.json()
        return {
            "success": True,
            "response": data.get("response", ""),
            "skill_used": data.get("skill_used"),
            "source": data.get("source", "openclaw"),
        }
    else:
        return {
            "success": False,
            "error": f"OpenClaw returned {resp.status_code}: {resp.text[:300]}",
        }


def _port_online(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except Exception:
        return False


async def _http_status(url: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url)
        return {
            "url": url,
            "online": 200 <= resp.status_code < 500,
            "status_code": resp.status_code,
        }
    except Exception as exc:
        return {"url": url, "online": False, "error": str(exc)}


async def _execute_health_check(task: dict) -> ExecutionResult:
    statuses = {port: "ONLINE" if _port_online(port) else "OFFLINE" for port in GENERIC_HEALTH_PORTS}
    result = "\n".join(
        [
            "OpenClaw DB task explicit health check.",
            "This generic port summary is allowed because the task explicitly asked for health/status/ports.",
            "",
            *[f"{port}: {state}" for port, state in statuses.items()],
        ]
    )
    return ExecutionResult(
        success=True,
        executor="openclaw_worker.local_health_check",
        result=result,
        commands=[f"socket.create_connection(127.0.0.1:{port})" for port in GENERIC_HEALTH_PORTS],
        metadata={"port_status": statuses},
    )


def _extract_self_heal_json_path(task: dict) -> Path | None:
    text = f"{task.get('title') or ''}\n{task.get('description') or ''}"
    if "write" not in text.lower() or ".json" not in text.lower():
        return None
    match = re.search(r"(/data/empire/self_heal_tests/[A-Za-z0-9_.-]+\.json)", text)
    if not match:
        return None
    path = Path(match.group(1)).resolve()
    allowed_root = Path("/data/empire/self_heal_tests").resolve()
    try:
        path.relative_to(allowed_root)
    except ValueError:
        return None
    return path


async def _execute_local_diagnostic_writer(task: dict) -> ExecutionResult | None:
    output_path = _extract_self_heal_json_path(task)
    if not output_path:
        return None

    health = {
        "backend": await _http_status("http://localhost:8000/health"),
        "frontend": await _http_status("http://localhost:3005"),
        "openclaw": await _http_status("http://localhost:7878/health"),
    }
    payload = {
        "created_at": datetime.now().isoformat(),
        "git_commit": _git_head(),
        "health": health,
        "executor": "openclaw_worker.local_diagnostic_writer",
        "task_id": task.get("id"),
        "title": task.get("title"),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        parsed = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return ExecutionResult(
            success=False,
            executor="openclaw_worker.local_diagnostic_writer",
            error=f"Diagnostic writer failed for {output_path}: {exc}",
            output_path=str(output_path),
        )

    if parsed.get("git_commit") != payload["git_commit"]:
        return ExecutionResult(
            success=False,
            executor="openclaw_worker.local_diagnostic_writer",
            error=f"Diagnostic writer validation failed for {output_path}",
            output_path=str(output_path),
        )

    evidence_lines = [
        f"Wrote diagnostic JSON: {output_path}",
        f"Validated JSON parse: yes",
        f"Current git commit: {payload['git_commit']}",
    ]
    for name, status in health.items():
        if "status_code" in status:
            evidence_lines.append(f"{name} health status: {status['status_code']} ({'online' if status['online'] else 'offline'})")
        else:
            evidence_lines.append(f"{name} health status: offline ({status.get('error')})")

    return ExecutionResult(
        success=True,
        executor="openclaw_worker.local_diagnostic_writer",
        result="\n".join(evidence_lines),
        commands=[
            "git rev-parse HEAD",
            "GET http://localhost:8000/health",
            "GET http://localhost:3005",
            "GET http://localhost:7878/health",
        ],
        output_path=str(output_path),
        metadata={"external_data_file": str(output_path), "health": health},
    )


def _extract_readonly_inspection_path(task: dict) -> Path | None:
    text = f"{task.get('title') or ''}\n{task.get('description') or ''}"
    lower = text.lower()
    if not any(term in lower for term in ("inspect", "read", "summarize")):
        return None
    if not any(term in lower for term in ("do not edit", "read-only", "do not commit")):
        return None

    candidates = re.findall(
        r"((?:backend|frontend|empire-command-center)/[\w/.\-]+\.py)",
        text,
    )
    repo_root = Path(REPO_DIR).resolve()
    for candidate in candidates:
        path = (repo_root / candidate).resolve()
        try:
            path.relative_to(repo_root)
        except ValueError:
            continue
        if path.exists():
            return path

    if "drawing" in lower and ("intent" in lower or "router" in lower):
        fallback_candidates = [
            repo_root / "backend/app/services/max/drawing_intent.py",
            repo_root / "backend/app/routers/drawings.py",
            repo_root / "backend/app/services/drawing/parametric_renderer.py",
        ]
        for path in fallback_candidates:
            if path.exists():
                return path.resolve()
    return None


def _summarize_python_functions(path: Path) -> list[str]:
    try:
        import ast

        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"Could not parse Python functions: {exc}"]

    items: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            doc = ast.get_docstring(node)
            summary = f"{kind} {node.name} (line {getattr(node, 'lineno', '?')})"
            if doc:
                summary += f": {doc.splitlines()[0][:120]}"
            items.append((getattr(node, "lineno", 0), summary))
    return [summary for _, summary in sorted(items)[:30]]


async def _execute_local_readonly_inspector(task: dict) -> ExecutionResult | None:
    path = _extract_readonly_inspection_path(task)
    if not path:
        return None

    repo_root = Path(REPO_DIR).resolve()
    rel_path = str(path.relative_to(repo_root))
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return ExecutionResult(
            success=False,
            executor="openclaw_worker.local_readonly_inspector",
            error=f"Could not inspect {rel_path}: {exc}",
            files_inspected=[rel_path],
        )

    functions = _summarize_python_functions(path)
    result_lines = [
        f"Inspected file path: {rel_path}",
        f"File exists: yes",
        f"Line count: {len(content.splitlines())}",
        "Relevant functions/classes:",
        *[f"- {item}" for item in functions],
        "No files edited. No commit created.",
    ]
    return ExecutionResult(
        success=True,
        executor="openclaw_worker.local_readonly_inspector",
        result="\n".join(result_lines),
        tools_run=["read_text", "ast.parse"],
        files_inspected=[rel_path],
    )


async def _try_safe_local_execution(task: dict) -> ExecutionResult | None:
    for executor in (_execute_local_diagnostic_writer, _execute_local_readonly_inspector):
        result = await executor(task)
        if result is not None:
            return result
    return None


async def _execute_code_task(task: dict) -> ExecutionResult:
    try:
        from app.services.max.code_task_runner import CodeTaskState, code_task_runner
    except Exception as exc:
        return ExecutionResult(
            success=False,
            executor="code_task_runner",
            error=f"CodeTaskRunner unavailable: {exc}",
        )

    prompt = _build_code_task_prompt(task)
    try:
        code_task = code_task_runner.submit(prompt)
    except Exception as exc:
        return ExecutionResult(
            success=False,
            executor="code_task_runner",
            error=f"CodeTaskRunner submit failed: {exc}",
        )

    def _state_value(value: Any) -> str:
        return getattr(value, "value", str(value))

    started = time.monotonic()
    while _state_value(code_task.state) in {CodeTaskState.QUEUED.value, CodeTaskState.RUNNING.value}:
        if time.monotonic() - started > CODE_TASK_TIMEOUT:
            return ExecutionResult(
                success=False,
                executor="code_task_runner",
                error=f"CodeTaskRunner timed out after {CODE_TASK_TIMEOUT}s",
                metadata={"code_task_id": code_task.id},
            )
        write_openclaw_worker_heartbeat(status="processing", current_task_id=task["id"])
        await asyncio.sleep(1)

    execution_mode = str(getattr(code_task, "execution_mode", "mutate") or "mutate")
    executed_tool_calls = list(getattr(code_task, "executed_tool_calls", []) or [])
    files_changed = list(getattr(code_task, "files_changed", []) or [])
    files_inspected = list(getattr(code_task, "files_inspected", []) or [])
    verified_test_runs = list(getattr(code_task, "verified_test_runs", []) or [])
    verification_notes = list(getattr(code_task, "verification_notes", []) or [])
    verified_commit_hash = getattr(code_task, "verified_commit_hash", None)
    result_text = code_task.result or ""
    mutating_tools = {"file_write", "file_edit", "file_append"}
    commands = []
    tools_run = []
    for call in executed_tool_calls:
        tool_name = call.get("tool", "unknown")
        status = "ok" if call.get("success") else "failed"
        params = call.get("params", {})
        tools_run.append(f"{tool_name} ({status}): {params}")
        if tool_name in {"git_ops", "test_runner", "shell_execute"}:
            command = params.get("command") if isinstance(params, dict) else None
            if command:
                commands.append(f"{tool_name}: {command}")

    has_tool_evidence = bool(executed_tool_calls or files_changed or files_inspected or verified_test_runs or verified_commit_hash)
    has_mutating_evidence = any(call.get("tool") in mutating_tools and call.get("success") for call in executed_tool_calls)

    if _state_value(code_task.state) == CodeTaskState.ERROR.value:
        return ExecutionResult(
            success=False,
            executor="code_task_runner",
            error=code_task.error or "CodeTaskRunner failed",
            tools_run=tools_run,
            metadata={"code_task_id": code_task.id},
        )

    if not executed_tool_calls:
        return ExecutionResult(
            success=False,
            executor="code_task_runner",
            error="CodeTaskRunner completed without actual tool execution; refusing to mark DB task done.",
            result=result_text,
            tools_run=tools_run,
            metadata={"code_task_id": code_task.id},
        )

    if execution_mode == "read_only" and has_mutating_evidence:
        return ExecutionResult(
            success=False,
            executor="code_task_runner",
            error="Read-only code task executed a mutating tool call.",
            result=result_text,
            tools_run=tools_run,
            metadata={"code_task_id": code_task.id},
        )

    if execution_mode != "read_only" and not files_changed:
        return ExecutionResult(
            success=False,
            executor="code_task_runner",
            error="Code task completed without actual file changes; refusing to accept prose-only summary.",
            result=result_text,
            tools_run=tools_run,
            metadata={"code_task_id": code_task.id},
        )

    commit_attempted = any(
        call.get("tool") == "git_ops"
        and call.get("success")
        and (call.get("params") or {}).get("command") == "commit"
        for call in executed_tool_calls
    )
    if commit_attempted and not verified_commit_hash:
        return ExecutionResult(
            success=False,
            executor="code_task_runner",
            error="git commit succeeded but could not be verified in repository history.",
            result=result_text,
            tools_run=tools_run,
            metadata={"code_task_id": code_task.id},
        )

    if verified_commit_hash and not _git_commit_exists(verified_commit_hash):
        return ExecutionResult(
            success=False,
            executor="code_task_runner",
            error=f"Verified commit hash is not present in git history: {verified_commit_hash}",
            result=result_text,
            tools_run=tools_run,
            metadata={"code_task_id": code_task.id},
        )

    if not has_tool_evidence:
        return ExecutionResult(
            success=False,
            executor="code_task_runner",
            error="CodeTaskRunner completed without verifiable evidence; refusing to mark DB task done.",
            result=result_text,
            tools_run=tools_run,
            metadata={"code_task_id": code_task.id},
        )

    return ExecutionResult(
        success=True,
        executor="code_task_runner",
        result=result_text,
        tools_run=tools_run,
        files_modified=files_changed,
        files_inspected=files_inspected,
        commands=commands,
        commit_hash=verified_commit_hash,
        metadata={
            "code_task_id": code_task.id,
            "execution_mode": execution_mode,
            "tool_calls": executed_tool_calls,
            "verified_test_runs": verified_test_runs,
            "verification_notes": verification_notes,
        },
    )


async def _execute_openclaw_chat_task(task: dict) -> ExecutionResult:
    gate = check_openclaw_gate()
    if not gate.allowed:
        return ExecutionResult(
            success=False,
            executor="openclaw_chat",
            error=gate.founder_message,
            metadata={"openclaw_gate": gate.to_dict()},
        )

    result = await _dispatch_to_openclaw(_build_task_prompt(task))
    if not result.get("success"):
        return ExecutionResult(
            success=False,
            executor="openclaw_chat",
            error=result.get("error", "OpenClaw dispatch failed"),
        )

    response_text = result.get("response", "") or ""
    skill_used = result.get("skill_used")
    if not _is_explicit_health_task(task) and _is_generic_port_health_result(response_text, skill_used):
        return ExecutionResult(
            success=False,
            executor="openclaw_chat",
            error="OpenClaw returned generic service health for a non-health task; refusing to mark done.",
            result=response_text,
            metadata={"skill_used": skill_used, "source": result.get("source")},
        )

    return ExecutionResult(
        success=True,
        executor="openclaw_chat",
        result=response_text,
        metadata={"skill_used": skill_used, "source": result.get("source")},
    )


async def _execute_task(task: dict) -> ExecutionResult:
    if _is_explicit_health_task(task):
        return await _execute_health_check(task)

    if _is_code_task(task):
        return await _execute_code_task(task)

    if _is_explicit_drawing_task(task):
        try:
            drawing_result = await _handle_drawing_task(task)
            return ExecutionResult(
                success=True,
                executor="openclaw_worker.local_drawing_generator",
                result=drawing_result,
                tools_run=["drawing_api", "svg_write"],
                output_path=f"~/empire-repo/uploads/openclaw_drawings/task_{task['id']}.svg",
            )
        except Exception as exc:
            return ExecutionResult(
                success=False,
                executor="openclaw_worker.local_drawing_generator",
                error=f"Drawing generation failed: {exc}",
            )

    local_result = await _try_safe_local_execution(task)
    if local_result is not None:
        return local_result

    return await _execute_openclaw_chat_task(task)


async def _notify_telegram(message: str):
    """Send a notification via the MAX chat/Telegram pipeline."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                "http://localhost:8000/api/v1/max/chat",
                json={"message": message, "channel": "telegram"},
            )
    except Exception as e:
        log.warning(f"Telegram notification failed: {e}")


async def _process_task(task: dict):
    """Process a single task through the appropriate truthful executor."""
    task_id = task["id"]
    log.info(f"Processing task #{task_id}: {task['title']} [desk={task['desk']}, priority={task['priority']}]")
    write_openclaw_worker_heartbeat(status="processing", current_task_id=task_id)

    # Mark as running
    _update_task(task_id, status="running", started_at=datetime.now().isoformat())

    try:
        before_files = _git_changed_files()
        before_head = _git_head()
        execution = await _execute_task(task)
        after_files = _git_changed_files()
        after_head = _git_head()
        commit_hash = after_head if before_head and after_head and after_head != before_head else execution.commit_hash
        files_modified = (
            _git_files_changed_between(before_head, after_head)
            if before_head and after_head and after_head != before_head
            else sorted(after_files - before_files)
        )

        if execution.success:
            if not _is_explicit_health_task(task) and _is_generic_port_health_result(execution.result):
                _fail_running_task(
                    task_id,
                    "Executor returned generic service health for a non-health task; refusing to mark done.",
                )
                log.error("Task #%s refused generic health completion", task_id)
                return

            if not _is_explicit_drawing_task(task) and _is_drawing_generation_result(execution):
                _fail_running_task(
                    task_id,
                    "Executor returned drawing generation output for a non-drawing task; refusing to mark done.",
                )
                log.error("Task #%s refused drawing generation completion", task_id)
                return

            if execution.executor == "code_task_runner":
                has_verified_evidence = any(
                    [
                        bool(execution.tools_run),
                        bool(execution.files_modified),
                        bool(execution.files_inspected),
                        bool(execution.commands),
                        bool(execution.commit_hash),
                    ]
                )
                if not has_verified_evidence:
                    _fail_running_task(
                        task_id,
                        "CodeTaskRunner returned success without verifiable evidence; refusing to mark done.",
                    )
                    log.error("Task #%s refused code task fake success", task_id)
                    return
                if execution.commit_hash and not _git_commit_exists(execution.commit_hash):
                    _fail_running_task(
                        task_id,
                        f"CodeTaskRunner reported an unverified commit hash: {execution.commit_hash}",
                    )
                    log.error("Task #%s refused unverified commit hash", task_id)
                    return

            response_text = _compose_task_result(
                task,
                ExecutionResult(
                    **{
                        **execution.__dict__,
                        "files_modified": files_modified,
                        "commit_hash": commit_hash,
                    }
                ),
            )

            if not _is_explicit_health_task(task) and _is_generic_port_health_result(response_text):
                _fail_running_task(
                    task_id,
                    "Executor result collapsed to generic service health for a non-health task; refusing to mark done.",
                )
                log.error("Task #%s refused generic health completion", task_id)
                return

            # Check for NEEDS_APPROVAL
            if "NEEDS_APPROVAL" in response_text:
                question = response_text.split("NEEDS_APPROVAL:")[-1].strip()[:500]
                _update_task(task_id, status="paused", result=response_text[:5000], error=f"NEEDS_APPROVAL: {question}")
                log.info(f"Task #{task_id} paused — needs approval: {question[:100]}")
                await _notify_telegram(
                    f"🤔 OpenClaw needs your input on Task #{task_id}: {task['title']}\n\n"
                    f"Question: {question}\n\n"
                    f"Approve at studio.empirebox.store/openclaw"
                )
                return

            # Success
            _update_task(
                task_id,
                status="done",
                result=response_text[:5000],
                files_modified=json.dumps(files_modified) if files_modified else None,
                commit_hash=commit_hash,
                completed_at=datetime.now().isoformat(),
            )
            log.info(f"Task #{task_id} completed: {task['title']}")

            # Notify for high-priority or tasks with changes
            if task["priority"] <= 3:
                await _notify_telegram(
                    f"✅ OpenClaw Task #{task_id}: {task['title']}\n"
                    f"Desk: {task['desk']}\n"
                    f"Result: {response_text[:300]}"
                )

        else:
            error = execution.error or "Executor failed without an error message"
            _update_task(
                task_id,
                status="failed",
                result=(execution.result or "")[:5000] or None,
                error=error[:2000],
                completed_at=datetime.now().isoformat(),
            )
            log.error("Task #%s failed truthfully via %s: %s", task_id, execution.executor, error[:200])
            await _notify_telegram(
                f"❌ OpenClaw Task #{task_id} FAILED: {task['title']}\n"
                f"Desk: {task['desk']}\n"
                f"Error: {error[:300]}"
            )

    except httpx.ConnectError:
        _update_task(task_id, status="failed", error="OpenClaw not reachable on port 7878",
                     completed_at=datetime.now().isoformat())
        log.error(f"Task #{task_id} failed: OpenClaw unreachable")
    except httpx.ReadTimeout:
        _update_task(task_id, status="failed", error=f"OpenClaw timed out after {OPENCLAW_TIMEOUT}s",
                     completed_at=datetime.now().isoformat())
        log.error(f"Task #{task_id} timed out")
    except Exception as e:
        _update_task(task_id, status="failed", error=str(e)[:2000],
                     completed_at=datetime.now().isoformat())
        log.error(f"Task #{task_id} unexpected error: {e}")
    finally:
        write_openclaw_worker_heartbeat(status="polling", current_task_id=None)


# ── AUTONOMOUS DEV CAPABILITIES ──────────────────────────────────────

REPO_DIR = os.path.expanduser("~/empire-repo")

# Files that must NEVER be modified by automated processes
PROTECTED_PATTERNS = [".env", ".git/", "node_modules/", "backend/data/empire.db",
                      "backend/data/", "main.py", "start-empire.sh", "__pycache__/"]


def _is_protected(filepath: str) -> bool:
    """Check if a file is protected from automated modification."""
    for pattern in PROTECTED_PATTERNS:
        if pattern in filepath:
            return True
    return False


def _validate_python(filepath: str) -> tuple[bool, str]:
    """Validate Python file syntax."""
    try:
        result = subprocess.run(
            ["python3", "-c", f"import ast; ast.parse(open('{filepath}').read())"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0, result.stderr[:300] if result.returncode != 0 else ""
    except Exception as e:
        return False, str(e)


async def verify_services() -> dict:
    """Quick health check on all services."""
    checks = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for name, url in [("backend", "http://localhost:8000/health"),
                          ("frontend", "http://localhost:3005"),
                          ("openclaw", "http://localhost:7878/health")]:
            try:
                resp = await client.get(url)
                checks[name] = resp.status_code == 200
            except Exception:
                checks[name] = False

    return checks


async def safe_git_commit(task: dict, files: list[str], message: str) -> dict:
    """Commit changes with safety checks. Returns commit info or error."""
    # 1. Check what changed
    result = subprocess.run(
        ["git", "diff", "--stat"], capture_output=True, text=True, cwd=REPO_DIR,
    )
    changed = [l.strip().split("|")[0].strip() for l in result.stdout.strip().split("\n") if "|" in l]

    # 2. Refuse if too many files
    if len(changed) > 20:
        return {"error": f"Too many files changed ({len(changed)}). Needs manual review."}

    # 3. Check for protected files
    for f in changed:
        if _is_protected(f):
            return {"error": f"Protected file modified: {f}. Needs manual approval."}

    # 4. Validate Python files
    for f in files:
        if f.endswith(".py"):
            full_path = os.path.join(REPO_DIR, f)
            if os.path.exists(full_path):
                valid, err = _validate_python(full_path)
                if not valid:
                    return {"error": f"Syntax error in {f}: {err}"}

    # 5. Stage and commit
    subprocess.run(["git", "add"] + files, cwd=REPO_DIR, capture_output=True)
    desk = task.get("desk", "general")
    commit_result = subprocess.run(
        ["git", "commit", "-m", f"openclaw/{desk}: {message}"],
        cwd=REPO_DIR, capture_output=True, text=True,
    )
    if commit_result.returncode != 0:
        return {"error": f"Git commit failed: {commit_result.stderr[:300]}"}

    # 6. Get hash
    hash_result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_DIR,
    )
    commit_hash = hash_result.stdout.strip()

    # 7. Push
    push_result = subprocess.run(
        ["git", "push", "origin", "main"], cwd=REPO_DIR, capture_output=True, text=True,
    )
    if push_result.returncode != 0:
        log.warning(f"Git push failed: {push_result.stderr[:200]}")

    # 8. Verify services still healthy
    checks = await verify_services()
    if not all(checks.values()):
        failed = [k for k, v in checks.items() if not v]
        # Auto-revert
        subprocess.run(["git", "revert", "HEAD", "--no-edit"], cwd=REPO_DIR, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_DIR, capture_output=True)
        return {"error": f"Services failed after commit ({failed}). Auto-reverted {commit_hash}."}

    return {"commit": commit_hash, "files": files, "pushed": push_result.returncode == 0}


# Drawing task detection
DRAWING_KEYWORDS = ["bench drawing", "generate drawing", "shop drawing", "render bench",
                    "parametric drawing", "cushion drawing", "window drawing"]


def _is_drawing_task(task: dict) -> bool:
    """Check if a task is a drawing generation request."""
    text = f"{task['title']} {task['description']}".lower()
    return any(kw in text for kw in DRAWING_KEYWORDS)


async def _handle_drawing_task(task: dict) -> str:
    """Handle drawing tasks by calling the renderer directly."""
    desc = task["description"].lower()

    # Parse dimensions from description
    width_match = re.search(r"(\d+)\s*(?:inch|in|\")", desc)
    width = int(width_match.group(1)) if width_match else 120

    # Determine bench type
    if "u-shape" in desc or "u shape" in desc or "booth" in desc:
        bench_type = "u_shape"
    elif "l-shape" in desc or "l shape" in desc:
        bench_type = "l_shape"
    else:
        bench_type = "straight"

    # Name from title
    name = task["title"].replace("drawing", "").replace("Drawing", "").strip() or "Bench"

    # Call the renderer via API
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "http://localhost:8000/api/v1/drawings/bench",
            json={
                "bench_type": bench_type,
                "name": name,
                "lf": width / 12,
                "seat_depth": 20,
                "seat_height": 18,
                "back_height": 34,
                "panel_style": "vertical_channels",
            },
        )

    if resp.status_code == 200:
        data = resp.json()
        # Save SVG to file
        out_dir = os.path.expanduser("~/empire-repo/uploads/openclaw_drawings")
        os.makedirs(out_dir, exist_ok=True)
        svg_path = os.path.join(out_dir, f"task_{task['id']}_{bench_type}.svg")
        with open(svg_path, "w") as f:
            f.write(data.get("svg", ""))
        return f"Drawing generated: {svg_path} ({bench_type}, {width}\")"
    else:
        return f"Drawing API error: {resp.status_code}"


_tasks_completed_since_summary = 0
_last_summary_time = None


async def _send_batch_summary():
    """Send a batch summary of recent completions. Called every 30 min if tasks were done."""
    global _tasks_completed_since_summary, _last_summary_time

    if _tasks_completed_since_summary < 1:
        return

    conn = _get_db()
    try:
        since = _last_summary_time or (datetime.now() - timedelta(minutes=30)).isoformat()
        done = conn.execute(
            "SELECT id, title, desk, status FROM openclaw_tasks WHERE completed_at > ? AND status = 'done' ORDER BY completed_at DESC LIMIT 10",
            (since,),
        ).fetchall()
        failed = conn.execute(
            "SELECT id, title, desk, error FROM openclaw_tasks WHERE completed_at > ? AND status = 'failed' ORDER BY completed_at DESC LIMIT 5",
            (since,),
        ).fetchall()
    finally:
        conn.close()

    if not done and not failed:
        _tasks_completed_since_summary = 0
        return

    msg = f"📊 OpenClaw Progress — {len(done)} done, {len(failed)} failed\n\n"
    for r in done:
        msg += f"✅ #{r[0]} {r[1]} ({r[2]})\n"
    for r in failed:
        msg += f"❌ #{r[0]} {r[1]}: {(r[3] or '')[:80]}\n"

    await _notify_telegram(msg)
    _tasks_completed_since_summary = 0
    _last_summary_time = datetime.now().isoformat()


async def openclaw_worker_loop():
    """Main worker loop — polls queue every 30 seconds, processes one task at a time."""
    global _tasks_completed_since_summary
    log.info("OpenClaw worker loop started — polling every %ds", POLL_INTERVAL)
    write_openclaw_worker_heartbeat(status="starting")
    _recover_orphaned_running_tasks()

    # Brief startup delay
    await asyncio.sleep(10)

    summary_interval = 0  # counter for batch summary timing

    while True:
        try:
            write_openclaw_worker_heartbeat(status="polling")
            _recover_orphaned_running_tasks()
            # Clean up zombies
            _cleanup_zombies()

            # Check for next task
            task = _get_next_task()
            if task:
                await _process_task(task)
                _tasks_completed_since_summary += 1
                # Brief pause between tasks
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(POLL_INTERVAL)

            # Batch summary every ~30 minutes (60 poll cycles * 30s)
            summary_interval += 1
            if summary_interval >= 60:
                await _send_batch_summary()
                summary_interval = 0

        except Exception as e:
            log.error(f"Worker loop error: {e}")
            await asyncio.sleep(POLL_INTERVAL)
