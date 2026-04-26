"""
CodeTaskRunner — Async code task execution via CodeForge/Atlas.

Runs multi-step code tasks with real tool execution. When Atlas outputs
tool call blocks (file_read, file_write, file_edit, git_ops), they are
parsed, executed, and results fed back so Atlas can chain operations.
Provides real-time progress logging via an activity log.
"""
import asyncio
import json
import logging
import os
import re
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from app.services.max.ai_router import AIMessage, AIModel, AIResponse, ai_router

logger = logging.getLogger("max.code_task")

# Tools Atlas is allowed to use in Code Mode
ALLOWED_TOOLS = {"file_read", "file_write", "file_edit", "file_append", "git_ops", "test_runner", "shell_execute", "package_manager", "service_manager", "project_scaffold"}
MAX_ITERATIONS = 8  # Safety cap on tool-call loops (reduced from 15 for performance)
MAX_NO_TOOL_RETRIES = 2
CODE_TASK_MODEL_OVERRIDE_ENV = ("OPENCLAW_CODE_MODEL", "CODE_TASK_MODEL")
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
CODE_TOOL_SCHEMAS = [
    {
        "type": "function",
        "name": "file_read",
        "description": "Read a file from the repo.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "type": "function",
        "name": "file_write",
        "description": "Write a new file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "type": "function",
        "name": "file_edit",
        "description": "Edit an existing file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "type": "function",
        "name": "file_append",
        "description": "Append to a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "type": "function",
        "name": "test_runner",
        "description": "Run tests and checks.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "type": "function",
        "name": "git_ops",
        "description": "Run git status, diff, log, add, or commit.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "args": {"type": "string"},
            },
            "required": ["command"],
        },
    },
    {
        "type": "function",
        "name": "shell_execute",
        "description": "Run a shell command when necessary.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
]


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


def _infer_provider_from_model(model_used: str | None) -> str:
    model = (model_used or "").lower()
    if model.startswith("claude") or model.startswith("anthropic"):
        return "anthropic"
    if model.startswith("gpt-") or "openai" in model:
        return "openai"
    if model.startswith("grok") or model.startswith("xai"):
        return "xai"
    if model.startswith("groq"):
        return "groq"
    if model.startswith("ollama"):
        return "ollama"
    if model.startswith("openclaw"):
        return "openclaw"
    return "unknown"


def _code_model_override() -> str | None:
    for env_name in CODE_TASK_MODEL_OVERRIDE_ENV:
        value = os.getenv(env_name)
        if value:
            return value.strip()
    return None


def _select_code_model() -> tuple[AIModel | None, str, bool]:
    override = _code_model_override()
    if override:
        normalized = override.lower()
        if normalized in {"grok", "xai"}:
            return AIModel.GROK, "xai", True
        for model in AIModel:
            if model.value == normalized:
                return model, _infer_provider_from_model(model.value), False
        return None, "unknown", False

    if ai_router.xai_key:
        return AIModel.GROK, "xai", True
    if ai_router.anthropic_key:
        return AIModel.CLAUDE_OPUS, "anthropic", False
    if ai_router.openai_key:
        return AIModel.OPENAI_4O, "openai", False
    if ai_router.groq_key:
        return AIModel.GROQ, "groq", False
    return AIModel.CLAUDE_OPUS, "unknown", False


def _code_protocol_intro(task: "CodeTask", execution_mode: str) -> str:
    return f"""DB-backed OpenClaw CodeForge execution task.

Title: {task.prompt.splitlines()[0][:200]}
Execution mode: {execution_mode}

You must respond with executable tool actions only.

Protocol:
- Return exactly one tool action per response.
- Valid formats are:
  1. Native function/tool call if supported.
  2. Raw JSON object with a top-level "tool" field.
  3. A fenced JSON block with one JSON object.
- Do not include prose outside the JSON/tool action.
- If you need to edit code, you must first inspect the file.
- If you need tests, use test_runner or shell_execute with the test command.
- If you need git, use git_ops.

Valid examples:
{{
  "tool": "file_read",
  "args": {{
    "path": "backend/app/services/max/drawing_intent.py"
  }}
}}

{{
  "tool": "file_edit",
  "args": {{
    "path": "backend/app/services/max/drawing_intent.py",
    "old": "before",
    "new": "after"
  }}
}}

{{
  "tool": "test_runner",
  "args": {{
    "command": "pytest backend/tests/test_openclaw_worker.py -q"
  }}
}}

{{
  "tool": "git_ops",
  "args": {{
    "command": "status"
  }}
}}

Task:
{task.prompt}
"""


def _code_protocol_retry_message() -> str:
    return """This is an edit task. You must use file_read/file_edit/file_write/test_runner/git_ops.
Provide exactly one executable tool action.

Valid JSON examples:
{"tool":"file_read","args":{"path":"backend/app/services/max/drawing_intent.py"}}
{"tool":"file_edit","args":{"path":"backend/app/services/max/drawing_intent.py","old":"before","new":"after"}}
{"tool":"file_write","args":{"path":"/tmp/codetaskrunner_tool_test.txt","content":"before"}}
{"tool":"test_runner","args":{"command":"pytest backend/tests/test_openclaw_worker.py -q"}}
{"tool":"git_ops","args":{"command":"status"}}
"""


def _extract_first_path(text: str) -> str | None:
    candidates = re.findall(
        r"((?:/tmp|/home/rg/empire-repo|~)/[^\s`\"'<>]+|(?:backend|frontend|empire-command-center)/[\w/.\-]+)",
        text or "",
    )
    if not candidates:
        return None
    path = candidates[0].rstrip(".,);")
    if path.startswith("~"):
        path = os.path.expanduser(path)
    elif not path.startswith("/"):
        path = os.path.join(os.path.expanduser("~/empire-repo"), path)
    return path


def _extract_literal_after(text: str, marker: str, *, fallback: str | None = None) -> str | None:
    pattern = re.compile(rf"{re.escape(marker)}\s+(.+?)(?:,\s*then\b|;\s*then\b|\.\s*then\b|\s+then\b|$)", re.IGNORECASE | re.DOTALL)
    match = pattern.search(text or "")
    if not match:
        return fallback
    value = match.group(1).strip().strip("`\"'")
    return value or fallback


def _synthesize_tool_actions_from_prompt(prompt: str, execution_mode: str) -> list[dict]:
    text = (prompt or "").strip()
    lower = text.lower()
    path = _extract_first_path(text)
    actions: list[dict] = []

    if not path:
        return actions

    if any(term in lower for term in ("write ", "create ", "save ")) and any(term in lower for term in ("then edit", "edit it", "update it", "change it")):
        initial = _extract_literal_after(text, "with content", fallback=_extract_literal_after(text, "content"))
        updated = _extract_literal_after(text, "edit it to", fallback=_extract_literal_after(text, "change it to", fallback=_extract_literal_after(text, "update it to")))
        if initial and updated:
            actions.append({"tool": "file_write", "path": path, "content": initial})
            actions.append({"tool": "file_edit", "path": path, "old_str": initial, "new_str": updated})
            return actions

    if any(term in lower for term in ("edit ", "fix ", "update ", "modify ", "change ", "patch ")):
        if any(term in lower for term in ("read ", "inspect ", "open ", "look at")) or execution_mode == "mutate":
            actions.append({"tool": "file_read", "path": path})
        return actions

    if any(term in lower for term in ("read ", "inspect ", "open ", "look at", "report", "summarize")):
        actions.append({"tool": "file_read", "path": path})
        return actions

    return actions


def _normalize_native_tool_call(tool_call: dict) -> dict | None:
    if not isinstance(tool_call, dict):
        return None

    normalized = dict(tool_call)
    tool_name = normalized.pop("tool", None) or normalized.pop("name", None)
    if not tool_name:
        return None

    merged: dict[str, Any] = {}
    for key in ("params", "args", "arguments"):
        value = normalized.pop(key, None)
        if isinstance(value, dict):
            merged.update(value)
        elif isinstance(value, str):
            try:
                decoded = json.loads(value)
            except Exception:
                continue
            if isinstance(decoded, dict):
                merged.update(decoded)

    merged.update({k: v for k, v in normalized.items() if not str(k).startswith("_")})

    if "old" in merged and "old_str" not in merged:
        merged["old_str"] = merged.pop("old")
    if "new" in merged and "new_str" not in merged:
        merged["new_str"] = merged.pop("new")
    if "text" in merged and "content" not in merged:
        merged["content"] = merged["text"]

    return {"tool": tool_name, **merged}


async def _request_code_response(
    prompt: str,
    *,
    execution_mode: str,
    task: "CodeTask",
    selected_model: AIModel | None = None,
    provider_hint: str | None = None,
    supports_native_tools: bool | None = None,
) -> AIResponse:
    model = selected_model
    if model is None or provider_hint is None or supports_native_tools is None:
        model, provider_hint, supports_native_tools = _select_code_model()
    tools = CODE_TOOL_SCHEMAS if supports_native_tools else None
    response = await ai_router.chat(
        messages=[AIMessage(role="user", content=prompt)],
        model=model,
        desk="codeforge",
        system_prompt=_code_protocol_intro(task, execution_mode),
        tools=tools,
    )
    task.provider_used = _infer_provider_from_model(response.model_used) or provider_hint
    task.model_used = response.model_used
    task.supports_tool_calls = bool(response.function_calls) if response.function_calls is not None else supports_native_tools
    return response


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
        f"Provider used: {task.provider_used or 'unknown'}",
        f"Model used: {task.model_used or 'unknown'}",
        f"Supports tool calls: {task.supports_tool_calls if task.supports_tool_calls is not None else 'unknown'}",
        f"Prompt attempts: {task.prompt_attempts}",
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
    lines.append(f"Failure reason: {task.failure_reason or 'none'}")
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
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    supports_tool_calls: Optional[bool] = None
    prompt_attempts: int = 0
    failure_reason: Optional[str] = None
    execution_protocol: str = "json-tool-action"
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
            "provider_used": self.provider_used,
            "model_used": self.model_used,
            "supports_tool_calls": self.supports_tool_calls,
            "prompt_attempts": self.prompt_attempts,
            "failure_reason": self.failure_reason,
            "execution_protocol": self.execution_protocol,
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
            from app.services.max.tool_executor import parse_tool_blocks, execute_tool

            desk_manager.initialize()

            codeforge = desk_manager.get_desk("codeforge")
            if not codeforge:
                raise RuntimeError("CodeForge desk not available")

            task.add_log("planning", "Reading codebase and planning changes...")
            prompt = task.prompt

            actual_files_changed: set[str] = set()
            actual_files_inspected: set[str] = set()
            executed_tool_calls: list[dict] = []
            verified_test_runs: list[dict] = []
            consecutive_blocked = 0  # Track repeated blocked-tool loops
            no_tool_retries = 0
            force_one_tool_call = task.execution_mode != "read_only"

            for iteration in range(MAX_ITERATIONS):
                # Call Atlas
                task.prompt_attempts += 1
                selected_model, provider_hint, supports_native_tools = _select_code_model()
                task.provider_used = provider_hint
                task.model_used = selected_model.value if selected_model else None
                task.supports_tool_calls = supports_native_tools
                response = await asyncio.wait_for(
                    _request_code_response(
                        prompt,
                        execution_mode=task.execution_mode,
                        task=task,
                        selected_model=selected_model,
                        provider_hint=provider_hint,
                        supports_native_tools=supports_native_tools,
                    ),
                    timeout=90,
                )
                task.add_log(
                    "model",
                    f"attempt={task.prompt_attempts} provider={task.provider_used or 'unknown'} model={task.model_used or 'unknown'} supports_tool_calls={task.supports_tool_calls if task.supports_tool_calls is not None else 'unknown'}",
                )

                if not response:
                    task.add_log("warning", f"Model returned empty response on iteration {iteration + 1}")
                    break

                response_text = response.content or ""
                tool_calls = [
                    normalized
                    for normalized in (
                        _normalize_native_tool_call(call)
                        for call in (response.function_calls or [])
                    )
                    if normalized
                ]
                if not tool_calls:
                    tool_calls = parse_tool_blocks(response_text)
                clean_text = response_text.strip()

                # No tool calls = Atlas is done
                if not tool_calls:
                    if force_one_tool_call and not executed_tool_calls and no_tool_retries < MAX_NO_TOOL_RETRIES:
                        no_tool_retries += 1
                        task.add_log("retry", "Model returned prose without tool calls; requesting executable tool call")
                        prompt = _code_protocol_retry_message()
                        continue
                    fallback_actions = _synthesize_tool_actions_from_prompt(task.prompt, task.execution_mode)
                    if fallback_actions and not executed_tool_calls:
                        task.add_log(
                            "planner",
                            f"Synthesized {len(fallback_actions)} executable tool action(s) from prompt: "
                            + ", ".join(
                                f"{action.get('tool')}:{action.get('path', action.get('command', ''))}"
                                for action in fallback_actions
                            ),
                        )
                        task.verification_notes.append("Local fallback planner synthesized executable tool actions from prompt")
                        tool_calls = fallback_actions
                    else:
                        if clean_text:
                            task.add_log("summary", clean_text[:120])
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
                task.failure_reason = (
                    f"selected code model did not emit executable tool calls "
                    f"(provider={task.provider_used or 'unknown'}, model={task.model_used or 'unknown'}, attempts={task.prompt_attempts}). "
                    "No deterministic fallback plan could be inferred from the prompt."
                )
                task.error = task.failure_reason
                task.completed_at = datetime.utcnow().isoformat()
                task.add_log("error", task.error)
                logger.error(f"Code task {task.id} did not provide executable tool calls after retries")
                return

            if not executed_tool_calls:
                task.state = CodeTaskState.ERROR
                task.failure_reason = (
                    f"Code task completed without actual tool execution "
                    f"(provider={task.provider_used or 'unknown'}, model={task.model_used or 'unknown'}, attempts={task.prompt_attempts})"
                )
                task.error = task.failure_reason
                task.completed_at = datetime.utcnow().isoformat()
                task.add_log("error", task.error)
                logger.error(f"Code task {task.id} had no executed tool calls")
                return

            if task.execution_mode == "read_only":
                if any(call.get("tool") in {"file_write", "file_edit", "file_append"} and call.get("success") for call in executed_tool_calls):
                    task.state = CodeTaskState.ERROR
                    task.failure_reason = "Read-only code task executed a mutating tool call."
                    task.error = task.failure_reason
                    task.completed_at = datetime.utcnow().isoformat()
                    task.add_log("error", task.error)
                    logger.error(f"Code task {task.id} violated read-only mode")
                    return
            else:
                if not task.files_changed:
                    task.state = CodeTaskState.ERROR
                    task.failure_reason = (
                        f"Code task completed without actual file changes "
                        f"(provider={task.provider_used or 'unknown'}, model={task.model_used or 'unknown'}, attempts={task.prompt_attempts})"
                    )
                    task.error = task.failure_reason
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
                task.failure_reason = "git commit succeeded but could not be verified in repository history."
                task.error = task.failure_reason
                task.completed_at = datetime.utcnow().isoformat()
                task.add_log("error", task.error)
                logger.error(f"Code task {task.id} could not verify commit")
                return

            if task.verified_commit_hash and not _repo_head_exists(task.verified_commit_hash):
                task.state = CodeTaskState.ERROR
                task.failure_reason = f"Verified commit hash is not present in git history: {task.verified_commit_hash}"
                task.error = task.failure_reason
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
