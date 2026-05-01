"""
CodeForgeDesk — Development operations desk.
Agent: Atlas. Handles code creation, editing, testing, and version control.
Precise, methodical — always reads before writing, always tests after changing.
"""
import logging
import os
import re
from .base_desk import BaseDesk, DeskTask, DeskAction


def _result_ok(r):
    """Return (success: bool, result: dict or None, error: str or None) from ToolResult or dict."""
    if r is None:
        return False, None, "No result"
    if isinstance(r, dict):
        return bool(r.get("success")), r.get("result"), r.get("error")
    # ToolResult dataclass
    return bool(getattr(r, "success", False)), getattr(r, "result", None), getattr(r, "error", None)

logger = logging.getLogger("max.desks.codeforge")


class CodeForgeDesk(BaseDesk):
    desk_id = "codeforge"
    desk_name = "CodeForge"
    agent_name = "Atlas"
    desk_description = (
        "Development operations — code creation, editing, testing, version control, "
        "and project scaffolding. Atlas reads before writing, tests after changing, "
        "and never modifies files outside ~/empire-repo/."
    )
    capabilities = [
        "file_read", "file_write", "file_edit", "file_append",
        "git_ops", "test_runner", "project_scaffold",
        "code_review", "bug_fixing", "feature_development",
    ]
    preferred_model = "claude-opus-4-6"  # Atlas gets Opus for coding tasks

    def __init__(self):
        super().__init__()
        self.files_changed: list[str] = []
        self.commits: list[str] = []

    async def _handle_task(self, task: DeskTask) -> DeskTask:
        await self.accept_task(task)
        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["read", "show", "view", "cat", "look at", "what's in"]):
                return await self._handle_read(task)
            elif any(w in combined for w in ["create", "scaffold", "new file", "new router", "new component", "new desk"]):
                return await self._handle_scaffold(task)
            elif any(w in combined for w in ["edit", "fix", "change", "update", "replace", "modify"]):
                return await self._handle_edit(task)
            elif any(w in combined for w in ["test", "check", "health", "verify", "build"]):
                return await self._handle_test(task)
            elif any(w in combined for w in ["commit", "git", "push", "status", "diff"]):
                return await self._handle_git(task)
            else:
                return await self._handle_general_dev(task)
        except Exception as e:
            logger.error(f"CodeForgeDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    @staticmethod
    def _expand_path(path: str) -> str:
        """Expand ~ and ~/ to full home directory path."""
        return os.path.expanduser(path)

    @staticmethod
    def _extract_paths(text: str) -> list[str]:
        """Extract file paths from text, expanding ~ to home dir."""
        # Match ~/..., /home/..., or relative backend/empire-command-center paths
        raw = re.findall(
            r'(?:~/[\w/.\-]+|/home/\w+/[\w/.\-]+|(?:backend|frontend|empire-command-center)/[\w/.\-]+)',
            text,
        )
        expanded = []
        for p in raw:
            p = os.path.expanduser(p)
            # Relative paths: prepend repo root
            if not os.path.isabs(p):
                p = os.path.join(os.path.expanduser("~/empire-repo"), p)
            expanded.append(p)
        return expanded

    @staticmethod
    def _format_file_content(content: str, path: str) -> str:
        """Format file content with smart truncation.

        - Files ≤ 500 lines: return in full.
        - Files > 500 lines: first 200 + last 50, with skip note.
        """
        lines = content.split('\n')
        total = len(lines)

        if total <= 500:
            return f"**{path}** ({total} lines)\n```\n{content}\n```"

        head = '\n'.join(lines[:200])
        tail = '\n'.join(lines[-50:])
        skipped = total - 250
        return (
            f"**{path}** ({total} lines — showing first 200 + last 50, {skipped} lines skipped)\n"
            f"```\n{head}\n```\n\n"
            f"... ({skipped} lines skipped) ...\n\n"
            f"```\n{tail}\n```"
        )

    async def _handle_read(self, task: DeskTask) -> DeskTask:
        """Read files — direct path priority, ~ expansion, full content."""
        task.actions.append(DeskAction(action="file_read", detail="Reading requested files"))
        from app.services.max.tool_executor import execute_tool

        combined = f"{task.title} {task.description}"
        paths = self._extract_paths(combined)
        logger.info(f"[CodeForge] _handle_read paths={paths} from: {combined!r}")

        if paths:
            target = paths[0]
            if os.path.isfile(target):
                task.actions.append(DeskAction(action="file_read", detail=f"Direct read: {target}"))
                r = execute_tool({"tool": "file_read", "path": target}, desk="codeforge")
                ok, res, err = _result_ok(r)
                if ok and res:
                    raw = res.get("content", str(res)) if isinstance(res, dict) else str(res)
                    return await self.complete_task(task, self._format_file_content(raw, target))
                else:
                    return await self.fail_task(task, err or "File read failed")
            else:
                return await self.fail_task(
                    task, f"File not found: {target}"
                )
        else:
            try:
                result = await self.ai_execute_task(task)
                return await self.complete_task(task, result)
            except Exception as e:
                return await self.fail_task(task, str(e))

    async def _handle_scaffold(self, task: DeskTask) -> DeskTask:
        """Create new files — use file_write tool directly."""
        task.actions.append(DeskAction(action="scaffold", detail="Creating new project files"))
        try:
            ai_result = await self.ai_call(
                f"Generate the code for this task. Output ONLY the file content, no explanations:\n\n"
                f"Task: {task.title}\nDetails: {task.description}\n\n"
                f"If multiple files are needed, output each as:\n"
                f"--- FILE: path/relative/to/empire-repo ---\n<content>\n--- END FILE ---"
            )
            if not ai_result:
                return await self.fail_task(task, "AI failed to generate code")

            file_blocks = re.findall(
                r'--- FILE: (.+?) ---\n(.*?)--- END FILE ---',
                ai_result, re.DOTALL,
            )
            if file_blocks:
                written = []
                for path, content in file_blocks:
                    r = self.write_file(self._expand_path(path.strip()), content)
                    if r["success"]:
                        written.append(path.strip())
                    else:
                        task.actions.append(DeskAction(action="file_write_failed", detail=f"{path}: {r['error']}", success=False))
                if written:
                    return await self.complete_task(task, f"Created {len(written)} file(s): {', '.join(written)}")
                else:
                    return await self.fail_task(task, "All file writes failed")
            else:
                paths = self._extract_paths(f"{task.title} {task.description}")
                if paths:
                    r = self.write_file(paths[0], ai_result)
                    if r["success"]:
                        return await self.complete_task(task, f"Created {paths[0]}")
                    else:
                        return await self.fail_task(task, r["error"] or "Write failed")
                else:
                    return await self.complete_task(task, f"Generated code:\n{ai_result[:2000]}")
        except Exception as e:
            return await self.fail_task(task, str(e))

    async def _handle_edit(self, task: DeskTask) -> DeskTask:
        """Edit existing files — read first, then use AI to generate edit, then write."""
        task.actions.append(DeskAction(action="file_edit", detail="Reading then editing files"))
        from app.services.max.tool_executor import execute_tool

        combined = f"{task.title} {task.description}"
        paths = self._extract_paths(combined)

        if paths:
            target = paths[0]
            r = execute_tool({"tool": "file_read", "path": target}, desk="codeforge")
            ok, res, err = _result_ok(r)
            if ok and res:
                current_content = res.get("content", "") if isinstance(res, dict) else ""
                ai_result = await self.ai_call(
                    f"Edit this file to complete the task. Output ONLY the complete new file content.\n\n"
                    f"Task: {task.title}\nDetails: {task.description}\n\n"
                    f"Current file ({target}):\n```\n{current_content[:6000]}\n```\n\n"
                    f"Output the complete updated file content, nothing else."
                )
                if ai_result:
                    w = self.write_file(target, ai_result)
                    if w["success"]:
                        return await self.complete_task(task, f"Edited {target}")
                    else:
                        return await self.fail_task(task, w["error"] or "Write failed")
                else:
                    return await self.fail_task(task, "AI failed to generate edit")
            else:
                return await self.fail_task(task, err or "Could not read file")
        else:
            try:
                result = await self.ai_execute_task(task)
                return await self.complete_task(task, result)
            except Exception as e:
                return await self.fail_task(task, str(e))

    async def _handle_test(self, task: DeskTask) -> DeskTask:
        """Run tests and health checks."""
        task.actions.append(DeskAction(action="test", detail="Running tests and checks"))
        from app.services.max.tool_executor import execute_tool

        # Run a health check
        r = execute_tool({"tool": "test_runner", "command": "health"}, desk="codeforge")
        ok, res, err = _result_ok(r)
        if ok and res:
            passed = res.get("passed", 0)
            failed = res.get("failed", 0)
            details = res.get("results", [])

            lines = [f"Health Check: {passed} passed, {failed} failed"]
            for d in details:
                icon = "✅" if d.get("ok") else "❌"
                label = d.get("label", d.get("path", "?"))
                lines.append(f"  {icon} {label}")

            result = "\n".join(lines)
            return await self.complete_task(task, result)
        else:
            return await self.fail_task(task, err or "Test runner failed")

    async def _handle_git(self, task: DeskTask) -> DeskTask:
        """Git operations."""
        task.actions.append(DeskAction(action="git_ops", detail="Running git operation"))
        from app.services.max.tool_executor import execute_tool

        combined = f"{task.title} {task.description}".lower()
        if "status" in combined:
            cmd = "status"
        elif "diff" in combined:
            cmd = "diff"
        elif "log" in combined:
            cmd = "log"
        else:
            cmd = "status"

        r = execute_tool({"tool": "git_ops", "command": cmd}, desk="codeforge")
        ok, res, err = _result_ok(r)
        if ok and res:
            return await self.complete_task(task, res.get("output", "No output") if isinstance(res, dict) else "Done")
        else:
            return await self.fail_task(task, err or "Git operation failed")

    async def _handle_general_dev(self, task: DeskTask) -> DeskTask:
        """General development task — use AI to determine approach."""
        task.actions.append(DeskAction(action="dev_task", detail="Processing development request"))
        try:
            result = await self.ai_execute_task(task)
            return await self.complete_task(task, result)
        except Exception as e:
            return await self.fail_task(task, str(e))

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["files_changed"] = len(self.files_changed)
        base["commits"] = len(self.commits)
        return base
