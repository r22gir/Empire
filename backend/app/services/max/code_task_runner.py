"""
CodeTaskRunner — Async code task execution via CodeForge/Atlas.

Runs multi-step code tasks with real tool execution. When Atlas outputs
tool call blocks (file_read, file_write, file_edit, git_ops), they are
parsed, executed, and results fed back so Atlas can chain operations.
Provides real-time progress logging via an activity log.
"""
import asyncio
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger("max.code_task")

# Tools Atlas is allowed to use in Code Mode
ALLOWED_TOOLS = {"file_read", "file_write", "file_edit", "file_append", "git_ops", "test_runner"}
MAX_ITERATIONS = 15  # Safety cap on tool-call loops


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


@dataclass
class CodeTask:
    """An async code task."""
    id: str
    prompt: str
    state: CodeTaskState = CodeTaskState.QUEUED
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    files_changed: list[str] = field(default_factory=list)
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
            "state": self.state.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
            "files_changed": self.files_changed,
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

            all_files_changed: set[str] = set()
            final_text_parts: list[str] = []
            consecutive_blocked = 0  # Track repeated blocked-tool loops

            for iteration in range(MAX_ITERATIONS):
                # Call Atlas
                response = await asyncio.wait_for(
                    codeforge.ai_call(prompt),
                    timeout=120,
                )

                if not response:
                    task.add_log("warning", f"Atlas returned empty response on iteration {iteration + 1}")
                    break

                # Parse tool calls from response
                tool_calls = parse_tool_blocks(response)
                clean_text = strip_tool_blocks(response)

                if clean_text:
                    final_text_parts.append(clean_text)

                # No tool calls = Atlas is done
                if not tool_calls:
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
                                path = tc.get("path", "")
                                if path:
                                    all_files_changed.add(path)
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

            # Assemble final result
            full_result = "\n\n".join(final_text_parts)
            if not full_result.strip():
                full_result = "(Atlas completed the task but produced no text output)"

            # Also extract file refs from text
            file_refs = re.findall(
                r'(?:~/[\w/.\-]+|/home/\w+/[\w/.\-]+|(?:backend|frontend|empire-command-center)/[\w/.\-]+)',
                full_result,
            )
            all_files_changed.update(file_refs)

            task.files_changed = sorted(all_files_changed)[:20]
            task.result = full_result
            task.state = CodeTaskState.COMPLETED
            task.completed_at = datetime.utcnow().isoformat()
            logger.info(f"Code task {task.id} completed: {len(task.files_changed)} files changed/referenced")

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
