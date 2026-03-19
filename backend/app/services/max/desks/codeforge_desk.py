"""
CodeForgeDesk — Development operations desk.
Agent: Atlas. Handles code creation, editing, testing, and version control.
Precise, methodical — always reads before writing, always tests after changing.
"""
import logging
from .base_desk import BaseDesk, DeskTask, DeskAction

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

    async def _handle_read(self, task: DeskTask) -> DeskTask:
        """Read files — Atlas's first step before any edit."""
        task.actions.append(DeskAction(action="file_read", detail="Reading requested files"))
        try:
            result = await self.ai_execute_task(task)
            return await self.complete_task(task, result)
        except Exception as e:
            return await self.fail_task(task, str(e))

    async def _handle_scaffold(self, task: DeskTask) -> DeskTask:
        """Create new files from templates."""
        task.actions.append(DeskAction(action="scaffold", detail="Creating new project files"))
        try:
            result = await self.ai_execute_task(task)
            return await self.complete_task(task, result)
        except Exception as e:
            return await self.fail_task(task, str(e))

    async def _handle_edit(self, task: DeskTask) -> DeskTask:
        """Edit existing files — always reads first."""
        task.actions.append(DeskAction(action="file_edit", detail="Reading then editing files"))
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
        if r.success and r.result:
            passed = r.result.get("passed", 0)
            failed = r.result.get("failed", 0)
            details = r.result.get("results", [])

            lines = [f"Health Check: {passed} passed, {failed} failed"]
            for d in details:
                icon = "✅" if d.get("ok") else "❌"
                label = d.get("label", d.get("path", "?"))
                lines.append(f"  {icon} {label}")

            result = "\n".join(lines)
            return await self.complete_task(task, result)
        else:
            return await self.fail_task(task, r.error or "Test runner failed")

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
        if r.success and r.result:
            return await self.complete_task(task, r.result.get("output", "No output"))
        else:
            return await self.fail_task(task, r.error or "Git operation failed")

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
