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
        """Read files — use file_read tool directly."""
        task.actions.append(DeskAction(action="file_read", detail="Reading requested files"))
        from app.services.max.tool_executor import execute_tool

        # Extract file path from task description
        combined = f"{task.title} {task.description}"
        # Try to find a file path in the description
        import re
        paths = re.findall(r'(?:~/empire-repo/|backend/|frontend/|empire-command-center/)[\w/.\-]+', combined)
        if paths:
            r = execute_tool({"tool": "file_read", "path": paths[0]}, desk="codeforge")
            if r.success and r.result:
                content = r.result.get("content", str(r.result))[:3000]
                return await self.complete_task(task, content)
            else:
                return await self.fail_task(task, r.error or "File read failed")
        else:
            # Fall back to AI to determine what to read
            try:
                result = await self.ai_execute_task(task)
                return await self.complete_task(task, result)
            except Exception as e:
                return await self.fail_task(task, str(e))

    async def _handle_scaffold(self, task: DeskTask) -> DeskTask:
        """Create new files — use file_write tool directly."""
        task.actions.append(DeskAction(action="scaffold", detail="Creating new project files"))
        # Scaffold requires AI to generate the content, then we write it
        try:
            # Ask AI to generate the file content
            ai_result = await self.ai_call(
                f"Generate the code for this task. Output ONLY the file content, no explanations:\n\n"
                f"Task: {task.title}\nDetails: {task.description}\n\n"
                f"If multiple files are needed, output each as:\n"
                f"--- FILE: path/relative/to/empire-repo ---\n<content>\n--- END FILE ---"
            )
            if not ai_result:
                return await self.fail_task(task, "AI failed to generate code")

            # Parse and write files
            import re
            file_blocks = re.findall(
                r'--- FILE: (.+?) ---\n(.*?)--- END FILE ---',
                ai_result, re.DOTALL,
            )
            if file_blocks:
                written = []
                for path, content in file_blocks:
                    r = self.write_file(path.strip(), content)
                    if r["success"]:
                        written.append(path.strip())
                    else:
                        task.actions.append(DeskAction(action="file_write_failed", detail=f"{path}: {r['error']}", success=False))
                if written:
                    return await self.complete_task(task, f"Created {len(written)} file(s): {', '.join(written)}")
                else:
                    return await self.fail_task(task, "All file writes failed")
            else:
                # Single file — try to extract path from task
                paths = re.findall(r'(?:~/empire-repo/|backend/|empire-command-center/)[\w/.\-]+', f"{task.title} {task.description}")
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
        import re

        # Extract file paths
        combined = f"{task.title} {task.description}"
        paths = re.findall(r'(?:~/empire-repo/|backend/|empire-command-center/)[\w/.\-]+', combined)

        if paths:
            # Read the file first
            r = execute_tool({"tool": "file_read", "path": paths[0]}, desk="codeforge")
            if r.success and r.result:
                current_content = r.result.get("content", "")
                # Ask AI what to change
                ai_result = await self.ai_call(
                    f"Edit this file to complete the task. Output ONLY the complete new file content.\n\n"
                    f"Task: {task.title}\nDetails: {task.description}\n\n"
                    f"Current file ({paths[0]}):\n```\n{current_content[:6000]}\n```\n\n"
                    f"Output the complete updated file content, nothing else."
                )
                if ai_result:
                    w = self.write_file(paths[0], ai_result)
                    if w["success"]:
                        return await self.complete_task(task, f"Edited {paths[0]}")
                    else:
                        return await self.fail_task(task, w["error"] or "Write failed")
                else:
                    return await self.fail_task(task, "AI failed to generate edit")
            else:
                return await self.fail_task(task, r.error or "Could not read file")
        else:
            # No clear file path — let AI figure it out
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
