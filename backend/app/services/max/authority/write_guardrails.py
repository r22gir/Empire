"""
Write Guardrails for v10_test MAX.

Blocks v10_test MAX from writing to:
- ~/empire-repo (canonical stable repo)
- ~/empire-box-memory (canonical brain store)
- feature/v10.0, main, master branches

Allows v10_test MAX to write only to:
- ~/empire-repo-v10
- /tmp (sandbox)
- feature/v10.0-test-lane git branch
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from .environment_policy import get_current_policy


class WriteGuardrails:
    """Enforces write scope restrictions per environment."""

    # Paths that v10_test cannot write to (canonical stable)
    BLOCKED_PATHS = [
        Path("~/empire-repo").expanduser().resolve(),
        Path("~/empire-box-memory").expanduser().resolve(),
    ]

    # Paths that v10_test cannot write to unless in proposal-only mode
    PROPOSAL_ONLY_PATHS = [
        Path("~/empire-repo").expanduser().resolve(),
    ]

    @classmethod
    def check_path_write(cls, path: str | Path) -> Tuple[bool, str]:
        """Check if a filesystem path can be written from current environment.

        Returns (allowed, reason).
        """
        policy = get_current_policy()
        path = Path(path).resolve()

        if policy.is_v10_test:
            # v10_test can only write to v10 repo or /tmp
            v10_root = policy.V10_ROOT.resolve()
            try:
                path.relative_to(v10_root)
                return True, "v10_test write allowed within v10 repo"
            except ValueError:
                pass

            # /tmp is allowed for sandbox
            if str(path).startswith("/tmp"):
                return True, "v10_test write allowed in /tmp sandbox"

            return False, (
                f"v10_test MAX cannot write to {path} — "
                f"write scope is limited to {policy.V10_ROOT}"
            )

        # Canonical — allow writes to canonical repo and /tmp
        canonical = policy.CANONICAL_ROOT.resolve()
        try:
            path.relative_to(canonical)
            return True, "canonical write allowed within empire-repo"
        except ValueError:
            pass

        if str(path).startswith("/tmp"):
            return True, "canonical write allowed in /tmp"

        return False, f"path {path} is outside allowed write scope"

    @classmethod
    def check_git_branch(cls, branch: str) -> Tuple[bool, str]:
        """Check if a git branch can be committed to from current environment.

        Returns (allowed, reason).
        """
        policy = get_current_policy()

        if policy.is_v10_test:
            allowed = policy.allowed_git_branches  # ["feature/v10.0-test-lane"]
            if branch in allowed:
                return True, f"v10_test can commit to {branch}"
            return False, (
                f"v10_test MAX cannot commit to branch '{branch}' — "
                f"only {allowed} allowed. "
                f"Use promotion workflow to propose changes to canonical."
            )

        # Canonical — check if in allowed branches
        if branch in policy.allowed_git_branches:
            return True, f"canonical write allowed to {branch}"
        return False, f"branch '{branch}' requires explicit promotion approval"

    @classmethod
    def check_git_command(cls, subcommand: str, args: str) -> Tuple[bool, str]:
        """Check if a git subcommand is allowed from current environment.

        Returns (allowed, reason).
        read_only commands: status, diff, log, branch, show
        write commands: add, commit, push, merge, rebase
        """
        policy = get_current_policy()
        read_only_commands = {"status", "diff", "log", "branch", "show", "rev-parse"}

        if subcommand.lower() in read_only_commands:
            return True, f"{subcommand} is read-only and allowed in all environments"

        # Write commands
        write_commands = {"add", "commit", "push", "merge", "rebase", "checkout", "branch"}
        if subcommand.lower() in write_commands:
            # Check branch for commit/push
            if subcommand.lower() in ("commit", "push"):
                # Extract branch from args if possible
                branch = args.strip().split()[-1] if args.strip() else ""
                # Remove leading refs/heads/ for branch names
                if branch.startswith("refs/heads/"):
                    branch = branch[len("refs/heads/"):]
                if branch.startswith("origin/"):
                    branch = branch[len("origin/"):]
                if branch.startswith("feature/v10.0"):
                    # Check if this is the v10 test lane or canonical branch
                    if "test-lane" in branch:
                        return cls.check_git_branch(branch)
                    return False, (
                        f"v10_test cannot commit to canonical branch '{branch}'. "
                        "Promote changes through approval workflow instead."
                    )
            return cls.check_git_branch(branch or "feature/v10.0-test-lane")

        return False, f"git subcommand '{subcommand}' is not recognized"

    @staticmethod
    def get_promotion_report(
        files_changed: list[str],
        tests_passed: bool,
        risk_level: str,
        memory_implications: list[str],
        canonical_memory_needs_update: bool,
    ) -> dict:
        """Generate a promotion report for v10_test changes.

        This report must be reviewed by a founder before changes can be
        promoted to canonical.
        """
        policy = get_current_policy()

        report = {
            "promotion_id": f"promo_{policy.branch}_{files_changed[0] if files_changed else 'unknown'}",
            "environment": policy.environment_name,
            "branch": policy.branch,
            "commit": policy.current_commit,
            "files_changed": files_changed,
            "tests_passed": tests_passed,
            "risk_level": risk_level,  # low / medium / high
            "memory_implications": memory_implications,
            "canonical_memory_needs_update": canonical_memory_needs_update,
            "promotion_eligible": False,
            "approval_required_from": list(
                {"web_cc", "telegram", "email", "founder"}
                & set(FOUNDER_CHANNELS)
            ),
            "steps_to_promote": [
                "1. Founder reviews promotion report",
                "2. Founder approves via /approve-promotion command",
                "3. Changes merged to feature/v10.0",
                "4. Canonical memory updated if needed",
                "5. Stable backend restarted to pick up changes",
            ],
            "if_rejected": [
                "1. v10_test MAX receives rejection reason",
                "2. v10_test MAX logs rejection for future reference",
                "3. v10_test MAX continues working on test-lane fixes",
            ],
        }

        # Promotion is eligible if tests passed and risk is not high
        if tests_passed and risk_level != "high":
            report["promotion_eligible"] = True

        return report


def check_write_allowed(path: str | Path) -> Tuple[bool, str]:
    """Shorthand for WriteGuardrails.check_path_write(path)."""
    return WriteGuardrails.check_path_write(path)


# Import FOUNDER_CHANNELS for use in promotion report generation
from .environment_policy import FOUNDER_CHANNELS