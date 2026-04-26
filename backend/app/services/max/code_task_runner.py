"""
CodeTaskRunner — Async code task execution via CodeForge/Atlas.

Runs multi-step code tasks with real tool execution. When Atlas outputs
tool call blocks (file_read, file_write, file_edit, git_ops), they are
parsed, executed, and results fed back so Atlas can chain operations.
Provides real-time progress logging via an activity log.
"""
import asyncio
import logging
import os
import re
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger("max.code_task")

# Tools Atlas is allowed to use in Code Mode
ALLOWED_TOOLS = {"file_read", "file_write", "file_edit", "file_append", "git_ops", "test_runner", "shell_execute", "package_manager", "service_manager", "project_scaffold"}
MAX_ITERATIONS = 8  # Safety cap on tool-call loops (reduced from 15 for performance)
MAX_NO_TOOL_RETRIES = 2
MUTATE_HINTS = (
    "fix ", "change ", "update ", "modify ", "harden ", "implement ",
    "patch ", "refactor ", "write ", "create ", "edit ", "replace ",
    "add ", "remove ", "repair ", "ground ", "prevent ",
)
READ_ONLY_HINTS = (
    "do not edit", "read-only", "inspect", "summarize", "report whether",
    "file exists", "do not commit", "do not generate drawings",
)
TEST_HINTS = ("test", "pytest", "verify", "build", "validation", "check")


class CodeTaskState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class CodeTaskLog:
    """A single log entry for a code task."""
    timestamp: str
    action: str  # e.g., "reading", "editing", "planning", "testing"
    detail: str


def _infer_execution_mode(prompt: str) -> str:
    lowered = (prompt or "").lower()
    if "execution mode: read_only" in lowered:
        return "read_only"
    if "execution mode: mutate" in lowered:
        return "mutate"

    read_only_hits = any(hint in lowered for hint in READ_ONLY_HINTS)
    mutate_hits = any(hint in lowered for hint in MUTATE_HINTS)
    if read_only_hits and not mutate_hits:
        return "read_only"
    if mutate_hits:
        return "mutate"
    return "mutate"


def _is_test_command(command: str | None) -> bool:
    if not command:
        return False
    lowered = command.lower()
    return any(hint in lowered for hint in TEST_HINTS)


def _sanitize_value(value, limit: int = 1200):
    if isinstance(value, dict):
        return {k: _sanitize_value(v, limit=limit) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(v, limit=limit) for v in value]
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "...(truncated)"
    return value


def _repo_head_exists(commit_hash: str) -> bool:
    if not commit_hash:
        return False
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{commit_hash}^{{commit}}"],
            cwd=os.path.expanduser("~/empire-repo"),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _repo_head_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=os.path.expanduser("~/empire-repo"),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
            return commit if _repo_head_exists(commit) else None
    except Exception:
        pass
    return None


def _tool_record(tool_call: dict, result, *, success: bool, error: str | None = None) -> dict:
    record = {
        "tool": tool_call.get("tool", "unknown"),
        "params": _sanitize_value({k: v for k, v in tool_call.items() if not str(k).startswith("_")}),
        "success": success,
    }
    if success:
        record["result"] = _sanitize_value(result.result)
    else:
        record["error"] = error or getattr(result, "error", None)
    return record


def _compose_verified_summary(task: "CodeTask") -> str:
    lines = [
        f"Execution mode: {task.execution_mode}",
        f"Task ID: {task.id}",
        f"Prompt: {task.prompt[:200]}",
        "",
        "Actual tool calls executed:",
    ]
    if task.executed_tool_calls:
        for idx, call in enumerate(task.executed_tool_calls, start=1):
            status = "ok" if call.get("success") else "failed"
            lines.append(
                f"{idx}. {call.get('tool')} ({status}) params={call.get('params')} result={call.get('result') or call.get('error')}"
            )
    else:
        lines.append("- none")

    if task.files_inspected:
        lines.append("")
        lines.append("Files inspected:")
        for path in task.files_inspected:
            lines.append(f"- {path}")

    if task.files_changed:
        lines.append("")
        lines.append("Files changed:")
        for path in task.files_changed:
            lines.append(f"- {path}")
    else:
        lines.append("")
        lines.append("Files changed: none")

    if task.verified_test_runs:
        lines.append("")
        lines.append("Verified tests:")
        for entry in task.verified_test_runs:
            lines.append(f"- {entry.get('tool')}: {entry.get('result')}")
    else:
        lines.append("")
        lines.append("Verified tests: none")

    lines.append("")
    lines.append(f"Verified commit hash: {task.verified_commit_hash or 'none'}")
    if task.verification_notes:
        lines.append("")
        lines.append("Verification notes:")
        for note in task.verification_notes:
            lines.append(f"- {note}")

    return "\n".join(lines).strip()


@dataclass
class CodeTask:
    """An async code task."""
    id: str
    prompt: str
    execution_mode: str = "auto"
    state: CodeTaskState = CodeTaskState.QUEUED
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    files_changed: list[str] = field(default_factory=list)
    files_inspected: list[str] = field(default_factory=list)
    executed_tool_calls: list[dict] = field(default_factory=list)
    verified_test_runs: list[dict] = field(default_factory=list)
    verified_commit_hash: Optional[str] = None
    verification_notes: list[str] = field(default_factory=list)
    log: list[CodeTaskLog] = field(default_factory=list)

    def add_log(self, action: str, detail: str):
        self.log.append(CodeTaskLog(
            timestamp=datetime.utcnow().isoformat(),
            action=action,
            detail=detail,
        ))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt[:200],
            "execution_mode": self.execution_mode,
            "state": self.state.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
            "files_changed": self.files_changed,
            "files_inspected": self.files_inspected,
            "executed_tool_calls": self.executed_tool_calls,
            "verified_test_runs": self.verified_test_runs,
            "verified_commit_hash": self.verified_commit_hash,
            "verification_notes": self.verification_notes,
            "log": [
                {"timestamp": l.timestamp, "action": l.action, "detail": l.detail}
                for l in self.log
            ],
        }


class CodeTaskRunner:
    """Manages async code tasks executed by CodeForge/Atlas."""

    def __init__(self):
        self._tasks: dict[str, CodeTask] = {}
        self._running: dict[str, asyncio.Task] = {}

    def get_task(self, task_id: str) -> Optional[CodeTask]:
        return self._tasks.get(task_id)

    def submit(self, prompt: str) -> CodeTask:
        """Submit a new code task. Returns immediately with task ID."""
        task = CodeTask(
            id=str(uuid.uuid4())[:12],
            prompt=prompt,
            execution_mode=_infer_execution_mode(prompt),
        )
        self._tasks[task.id] = task
        # Start execution in background
        self._running[task.id] = asyncio.create_task(self._execute(task))
        logger.info(f"Code task {task.id} submitted: {prompt[:80]}")
        return task

    async def _execute(self, task: CodeTask):
        """Execute the code task via CodeForge/Atlas with real tool execution.

        Loop: Atlas responds → parse tool blocks → execute tools → feed results
        back → Atlas continues until no more tool calls or it outputs a final summary.
        """
        task.state = CodeTaskState.RUNNING
        task.started_at = datetime.utcnow().isoformat()
        task.add_log("started", "Atlas is analyzing the request...")

        try:
            from app.services.max.desks.desk_manager import desk_manager
            from app.services.max.tool_executor import parse_tool_blocks, execute_tool, strip_tool_blocks

            desk_manager.initialize()

            codeforge = desk_manager.get_desk("codeforge")
            if not codeforge:
                raise RuntimeError("CodeForge desk not available")

            task.add_log("planning", "Reading codebase and planning changes...")

            # Build initial prompt for Atlas
            import os
            repo_root = os.path.expanduser("~/empire-repo")
            prompt = (
                "You are Atlas (CodeForge), handling a Code Mode task from the founder. "
                "You have tools available — use them to read, write, and edit files. "
                "Execute tool calls one at a time using ```tool blocks.\n\n"
                f"IMPORTANT: The repository root is {repo_root}. Always use this as the base for all file paths.\n\n"
                "Available tools:\n"
                f"- file_read: {{\"tool\": \"file_read\", \"path\": \"{repo_root}/backend/app/main.py\"}}\n"
                f"- file_write: {{\"tool\": \"file_write\", \"path\": \"{repo_root}/path/to/file\", \"content\": \"...\"}}\n"
                f"- file_edit: {{\"tool\": \"file_edit\", \"path\": \"{repo_root}/path/to/file\", \"old_str\": \"...\", \"new_str\": \"...\"}}\n"
                f"- file_append: {{\"tool\": \"file_append\", \"path\": \"{repo_root}/path/to/file\", \"content\": \"...\"}}\n"
                "- git_ops: {\"tool\": \"git_ops\", \"command\": \"status|diff|log|add\", \"args\": \"...\"}\n\n"
                "IMPORTANT: Use ONE tool call per response. I will execute it and give you the result. "
                "Then you can use the next tool. When you are DONE, write your final answer with "
                "NO tool blocks — just a ## Summary section.\n\n"
                f"Task: {task.prompt}"
            )

            actual_files_changed: set[str] = set()
            actual_files_inspected: set[str] = set()
            executed_tool_calls: list[dict] = []
            verified_test_runs: list[dict] = []
            consecutive_blocked = 0  # Track repeated blocked-tool loops
            no_tool_retries = 0
            force_one_tool_call = task.execution_mode != "read_only"

            for iteration in range(MAX_ITERATIONS):
                # Call Atlas
                response = await asyncio.wait_for(
                    codeforge.ai_call(prompt),
                    timeout=90,
                )

                if not response:
                    task.add_log("warning", f"Atlas returned empty response on iteration {iteration + 1}")
                    break

                # Parse tool calls from response
                tool_calls = parse_tool_blocks(response)
                clean_text = strip_tool_blocks(response)

                # No tool calls = Atlas is done
                if not tool_calls:
                    if clean_text:
                        task.add_log("summary", clean_text[:120])
                    if force_one_tool_call and not executed_tool_calls and no_tool_retries < MAX_NO_TOOL_RETRIES:
                        no_tool_retries += 1
                        task.add_log("retry", "Atlas returned prose without tool calls; requesting executable tool call")
                        prompt = (
                            "This is an edit task. You must use file_read/file_edit/file_write/test_runner/git_ops. "
                            "Provide exactly one tool call."
                        )
                        continue
                    task.add_log("completed", "Atlas finished — no more tool calls")
                    break

                # Execute each tool call and collect results
                tool_results_text = []
                any_allowed = False
                for tc in tool_calls:
                    tool_name = tc.get("tool", "unknown")

                    # Safety: only allow whitelisted tools
                    if tool_name not in ALLOWED_TOOLS:
                        task.add_log("blocked", f"Blocked disallowed tool: {tool_name}")
                        tool_results_text.append(f"[Tool '{tool_name}' is not allowed in Code Mode. Only: {', '.join(sorted(ALLOWED_TOOLS))}]")
                        continue

                    any_allowed = True

                    # Log what we're doing
                    action_label = {
                        "file_read": "reading",
                        "file_write": "writing",
                        "file_edit": "editing",
                        "file_append": "appending",
                        "git_ops": "git",
                        "test_runner": "testing",
                    }.get(tool_name, "executing")

                    detail = tc.get("path", tc.get("command", ""))
                    if isinstance(detail, str) and len(detail) > 80:
                        detail = detail[:77] + "..."
                    task.add_log(action_label, f"{tool_name}: {detail}")

                    # Execute the tool (sync — run in thread to not block event loop)
                    try:
                        result = await asyncio.get_event_loop().run_in_executor(
                            None, lambda t=tc: execute_tool(t, desk="codeforge")
                        )
                        executed_tool_calls.append(_tool_record(tc, result, success=result.success, error=result.error))

                        if result.success:
                            result_str = str(result.result) if result.result else "(no output)"
                            # Cap tool output to prevent context explosion
                            if len(result_str) > 8000:
                                result_str = result_str[:8000] + "\n... (truncated)"
                            tool_results_text.append(
                                f"✓ {tool_name} succeeded:\n{result_str}"
                            )
                            # Track file changes
                            if tool_name in ("file_write", "file_edit", "file_append"):
                                path = (
                                    (result.result or {}).get("path")
                                    if isinstance(result.result, dict)
                                    else tc.get("path", "")
                                )
                                if path:
                                    actual_files_changed.add(str(path))
                            if tool_name == "file_read":
                                path = (
                                    (result.result or {}).get("path")
                                    if isinstance(result.result, dict)
                                    else tc.get("path", "")
                                )
                                if path:
                                    actual_files_inspected.add(str(path))
                            if tool_name == "git_ops":
                                command = str(tc.get("command", "")).strip()
                                if command == "commit":
                                    verified = _repo_head_commit()
                                    if verified:
                                        task.verified_commit_hash = verified
                                    else:
                                        task.verification_notes.append("git commit reported success but HEAD could not be verified")
                            if tool_name == "test_runner" or (tool_name == "shell_execute" and _is_test_command(str(tc.get("command", "")))):
                                verified_test_runs.append({
                                    "tool": tool_name,
                                    "command": tc.get("command"),
                                    "result": _sanitize_value(result.result),
                                })
                        else:
                            tool_results_text.append(
                                f"✗ {tool_name} failed: {result.error}"
                            )
                    except Exception as e:
                        tool_results_text.append(f"✗ {tool_name} exception: {e}")
                        logger.error(f"Code task {task.id} tool error: {e}")

                # Track consecutive iterations where ALL tool calls were blocked
                if not any_allowed:
                    consecutive_blocked += 1
                    if consecutive_blocked >= 2:
                        task.add_log("stopped", "Stopped — Atlas keeps requesting disallowed tools")
                        break
                else:
                    consecutive_blocked = 0

                # Build follow-up prompt with tool results
                results_block = "\n\n".join(tool_results_text)
                prompt = (
                    f"Tool results:\n\n{results_block}\n\n"
                    "Continue with your next step. Use another tool call if needed, "
                    "or write your ## Summary if you're done."
                )

            else:
                # Hit MAX_ITERATIONS
                task.add_log("warning", f"Reached {MAX_ITERATIONS} iteration limit")

            task.executed_tool_calls = executed_tool_calls
            task.files_changed = sorted(actual_files_changed)[:20]
            task.files_inspected = sorted(actual_files_inspected)[:20]
            task.verified_test_runs = verified_test_runs

            if force_one_tool_call and no_tool_retries >= MAX_NO_TOOL_RETRIES and not executed_tool_calls:
                task.state = CodeTaskState.ERROR
                task.error = "model did not provide executable tool calls."
                task.completed_at = datetime.utcnow().isoformat()
                task.add_log("error", task.error)
                logger.error(f"Code task {task.id} did not provide executable tool calls after retries")
                return

            if not executed_tool_calls:
                task.state = CodeTaskState.ERROR
                task.error = "Code task completed without actual tool execution; refusing prose-only summary."
                task.completed_at = datetime.utcnow().isoformat()
                task.add_log("error", task.error)
                logger.error(f"Code task {task.id} had no executed tool calls")
                return

            if task.execution_mode == "read_only":
                if any(call.get("tool") in {"file_write", "file_edit", "file_append"} and call.get("success") for call in executed_tool_calls):
                    task.state = CodeTaskState.ERROR
                    task.error = "Read-only code task executed a mutating tool call."
                    task.completed_at = datetime.utcnow().isoformat()
                    task.add_log("error", task.error)
                    logger.error(f"Code task {task.id} violated read-only mode")
                    return
            else:
                if not task.files_changed:
                    task.state = CodeTaskState.ERROR
                    task.error = "Code task completed without actual file changes; refusing to accept prose-only summary."
                    task.completed_at = datetime.utcnow().isoformat()
                    task.add_log("error", task.error)
                    logger.error(f"Code task {task.id} had no actual file changes")
                    return

            commit_attempted = any(
                call.get("tool") == "git_ops"
                and call.get("success")
                and (call.get("params") or {}).get("command") == "commit"
                for call in executed_tool_calls
            )
            if commit_attempted and not task.verified_commit_hash:
                task.state = CodeTaskState.ERROR
                task.error = "git commit succeeded but could not be verified in repository history."
                task.completed_at = datetime.utcnow().isoformat()
                task.add_log("error", task.error)
                logger.error(f"Code task {task.id} could not verify commit")
                return

            if task.verified_commit_hash and not _repo_head_exists(task.verified_commit_hash):
                task.state = CodeTaskState.ERROR
                task.error = f"Verified commit hash is not present in git history: {task.verified_commit_hash}"
                task.completed_at = datetime.utcnow().isoformat()
                task.add_log("error", task.error)
                logger.error(f"Code task {task.id} invalid commit hash")
                return

            task.result = _compose_verified_summary(task)
            task.state = CodeTaskState.COMPLETED
            task.completed_at = datetime.utcnow().isoformat()
            logger.info(
                f"Code task {task.id} completed: {len(task.files_changed)} files changed, {len(task.executed_tool_calls)} tool calls"
            )

        except asyncio.TimeoutError:
            task.state = CodeTaskState.ERROR
            task.error = "Task timed out — Atlas was unresponsive for too long"
            task.completed_at = datetime.utcnow().isoformat()
            task.add_log("error", "Timed out waiting for Atlas")
            logger.error(f"Code task {task.id} timed out")

        except Exception as e:
            task.state = CodeTaskState.ERROR
            task.error = str(e)
            task.completed_at = datetime.utcnow().isoformat()
            task.add_log("error", f"Failed: {e}")
            logger.error(f"Code task {task.id} failed: {e}")

        finally:
            self._running.pop(task.id, None)


# Singleton
code_task_runner = CodeTaskRunner()
