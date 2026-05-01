"""
MAX Environment Authority Policy — defines environment identity, write scope,
and memory access rules for canonical MAX vs v10_test MAX.

Environment hierarchy:
  CANONICAL    — stable production MAX, ~/empire-repo, feature/v10.0
  V10_TEST     — test-lane MAX, ~/empire-repo-v10, feature/v10.0-test-lane

Canonical MAX:
  - Repo: ~/empire-repo
  - Branch: feature/v10.0
  - Memory: canonical read/write
  - Code writes: allowed only with explicit founder approval
  - Memory writes: allowed via verified founder channel (CC, Telegram, Email)

v10_test MAX:
  - Repo: ~/empire-repo-v10
  - Branch: feature/v10.0-test-lane
  - Memory: canonical read-only (no direct writes)
  - Code writes: allowed only inside ~/empire-repo-v10
  - Memory writes: MUST create proposal, never apply directly
  - Canonical memory: read-only, proposals only
"""
from __future__ import annotations

import os
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional


class EnvironmentType(Enum):
    CANONICAL = "canonical"
    V10_TEST = "v10_test"


# Approved founder channels for canonical memory writes and promotion approvals
FOUNDER_CHANNELS = {"web_cc", "telegram", "email", "founder"}


class EnvironmentPolicy:
    """Defines the authority rules for the current MAX environment."""

    # Canonical repo paths
    CANONICAL_ROOT = Path(os.path.expanduser("~/empire-repo"))
    V10_ROOT = Path(os.path.expanduser("~/empire-repo-v10"))

    # Canonical memory path (empire-box-memory is the canonical brain store)
    CANONICAL_MEMORY_ROOT = Path(os.path.expanduser("~/empire-box-memory"))

    def __init__(
        self,
        environment: Optional[EnvironmentType] = None,
        repo_root: Optional[Path] = None,
        branch: Optional[str] = None,
    ):
        # Auto-detect if not provided
        if environment is None:
            environment = self._detect_environment()
        self.environment = environment

        if repo_root is None:
            repo_root = self._detect_repo_root()
        self.repo_root = Path(repo_root)

        if branch is None:
            branch = self._detect_branch()
        self.branch = branch

        self._commit = self._detect_commit()
        self._memory_mode = self._derive_memory_mode()
        self._write_scope = self._derive_write_scope()
        self._canonical_memory_write_allowed = self._derive_memory_write_allowed()
        self._founder_approval_required = self._derive_founder_approval_required()

    def _detect_environment(self) -> EnvironmentType:
        """Auto-detect environment from path and git remote."""
        cwd = Path.cwd()
        v10_root = self.V10_ROOT.resolve()
        canonical_root = self.CANONICAL_ROOT.resolve()

        # Check if running from v10 repo
        try:
            v10_resolved = canonical_root.resolve()
        except Exception:
            v10_resolved = None

        # Check v10-specific paths
        if str(cwd).startswith("/home/rg/empire-repo-v10"):
            return EnvironmentType.V10_TEST

        # Check git remote for v10 test lane indicator
        try:
            result = subprocess.run(
                ["git", "-C", str(canonical_root), "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5,
            )
            remote = result.stdout.strip()
            if "empire-repo-v10" in remote:
                return EnvironmentType.V10_TEST
        except Exception:
            pass

        # Default to canonical
        return EnvironmentType.CANONICAL

    def _detect_repo_root(self) -> Path:
        """Detect which repo we're running in."""
        cwd = Path.cwd()
        if str(cwd).startswith("/home/rg/empire-repo-v10"):
            return self.V10_ROOT
        return self.CANONICAL_ROOT

    def _detect_branch(self) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5,
                cwd=str(self.repo_root),
            )
            branch = result.stdout.strip()
            if branch:
                return branch
        except Exception:
            pass

        # Fallback to rev-parse
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5,
                cwd=str(self.repo_root),
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _detect_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5,
                cwd=str(self.repo_root),
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _derive_memory_mode(self) -> str:
        if self.environment == EnvironmentType.V10_TEST:
            return "read_only"
        return "read_write"

    def _derive_write_scope(self) -> str:
        if self.environment == EnvironmentType.V10_TEST:
            return "v10_repo_only"
        return "canonical"

    def _derive_memory_write_allowed(self) -> bool:
        """Whether direct canonical memory writes are allowed."""
        if self.environment == EnvironmentType.CANONICAL:
            return True
        return False  # v10_test cannot write canonical memory

    def _derive_founder_approval_required(self) -> bool:
        """Whether founder approval is required for code/memory writes."""
        if self.environment == EnvironmentType.CANONICAL:
            return True  # canonical always needs approval for writes
        return True  # v10_test always needs approval for promotion

    @property
    def environment_name(self) -> str:
        return self.environment.value

    @property
    def is_canonical(self) -> bool:
        return self.environment == EnvironmentType.CANONICAL

    @property
    def is_v10_test(self) -> bool:
        return self.environment == EnvironmentType.V10_TEST

    @property
    def memory_mode(self) -> str:
        return self._memory_mode

    @property
    def write_scope(self) -> str:
        return self._write_scope

    @property
    def canonical_memory_write_allowed(self) -> bool:
        return self._canonical_memory_write_allowed

    @property
    def founder_approval_required(self) -> bool:
        return self._founder_approval_required

    @property
    def current_commit(self) -> str:
        return self._commit

    @property
    def allowed_git_branches(self) -> list[str]:
        """Which git branches this environment can commit to."""
        if self.environment == EnvironmentType.CANONICAL:
            return ["feature/v10.0", "main", "master"]
        # v10_test can only commit to test lane
        return ["feature/v10.0-test-lane"]

    @property
    def blocked_git_branches(self) -> list[str]:
        """Branches that cannot be written to from this environment."""
        if self.environment == EnvironmentType.CANONICAL:
            return []
        return ["feature/v10.0", "main", "master", "feature/v10.0-test-lane"]

    def can_write_path(self, path: str | Path) -> bool:
        """Check if a filesystem path can be written from this environment."""
        path = Path(path).resolve()
        if self.environment == EnvironmentType.V10_TEST:
            # v10_test can only write inside v10 repo
            v10 = self.V10_ROOT.resolve()
            try:
                path.relative_to(v10)
                return True
            except ValueError:
                return False
        # Canonical can write to canonical repo
        canonical = self.CANONICAL_ROOT.resolve()
        try:
            path.relative_to(canonical)
            return True
        except ValueError:
            pass
        # Also allow /tmp
        if str(path).startswith("/tmp"):
            return True
        return False

    def can_write_memory(self, channel: Optional[str] = None) -> tuple[bool, str]:
        """Check if memory can be written.

        Returns (allowed, reason).
        For v10_test, always returns (False, "proposal_only").
        For canonical, requires founder channel for direct writes.
        """
        if self.environment == EnvironmentType.V10_TEST:
            return False, "v10_test writes canonical memory are forbidden — create a proposal instead"

        # Canonical needs founder channel
        if channel and channel.lower() in FOUNDER_CHANNELS:
            return True, "founder channel confirmed"
        return False, f"canonical memory write requires founder channel ({', '.join(FOUNDER_CHANNELS)})"

    def can_commit_branch(self, branch: str) -> tuple[bool, str]:
        """Check if a git branch can be committed to from this environment."""
        if self.environment == EnvironmentType.V10_TEST:
            if branch == "feature/v10.0-test-lane":
                return True, "v10_test test lane branch"
            return False, f"v10_test cannot commit to {branch} — only feature/v10.0-test-lane allowed"
        # Canonical can write to feature/v10.0, main
        allowed = self.allowed_git_branches
        if branch in allowed:
            return True, f"{branch} is an allowed branch for canonical"
        return False, f"{branch} is not in allowed branches {allowed}"

    def get_status(self) -> dict:
        """Return full environment status as a dict."""
        return {
            "environment_name": self.environment_name,
            "is_canonical": self.is_canonical,
            "is_v10_test": self.is_v10_test,
            "repo_root": str(self.repo_root.resolve()),
            "branch": self.branch,
            "current_commit": self.current_commit,
            "memory_mode": self.memory_mode,
            "write_scope": self.write_scope,
            "canonical_memory_write_allowed": self.canonical_memory_write_allowed,
            "founder_approval_required": self.founder_approval_required,
            "allowed_git_branches": self.allowed_git_branches,
            "blocked_git_branches": self.blocked_git_branches,
            "memory_source": "canonical" if self.is_canonical else "canonical_read_only",
            "can_promote": self.is_canonical,
        }


def get_current_policy() -> EnvironmentPolicy:
    """Get the current environment policy (singleton per process)."""
    if not hasattr(get_current_policy, "_policy"):
        get_current_policy._policy = EnvironmentPolicy()
    return get_current_policy._policy


def format_environment_status(policy: Optional[EnvironmentPolicy] = None) -> str:
    """Format environment status as human-readable text."""
    if policy is None:
        policy = get_current_policy()

    p = policy.get_status()
    lines = [
        f"Environment: {p['environment_name']}",
        f"Repo: {p['repo_root']}",
        f"Branch: {p['branch']}",
        f"Commit: {p['current_commit']}",
        f"Memory: {p['memory_mode']} — source: {p['memory_source']}",
        f"Write scope: {p['write_scope']}",
        f"Canonical memory write allowed: {p['canonical_memory_write_allowed']}",
        f"Founder approval required: {p['founder_approval_required']}",
        f"Can promote to canonical: {p['can_promote']}",
        f"Allowed git branches: {', '.join(p['allowed_git_branches'])}",
    ]
    return "\n".join(lines)