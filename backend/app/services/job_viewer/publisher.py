"""Push a viewer HTML file to a GitHub Pages repo. Never runs unless asked.

Tests inject a MemoryPagesPublisher — no git, no network, no live writes.
Production uses a subprocess git runner against JOB_VIEWER_GITHUB_REPO.
Later host: workroom.empirebox.store (JOB_VIEWER_PAGES_BASE_URL).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional


class PublishNotConfigured(RuntimeError):
    pass


class MemoryPagesPublisher:
    """In-memory GitHub Pages stand-in for tests."""

    def __init__(self, base_url: str = "https://viewer.test"):
        self.files: dict[str, str] = {}
        self.log: list[tuple[str, str]] = []
        self.base_url = base_url.rstrip("/")

    def publish(self, slug: str, html: str, message: str = "") -> str:
        self.files[f"{slug}/index.html"] = html
        self.log.append(("publish", slug))
        return f"{self.base_url}/{slug}/"

    def unpublish(self, slug: str) -> None:
        self.files.pop(f"{slug}/index.html", None)
        self.log.append(("unpublish", slug))


Runner = Callable[..., subprocess.CompletedProcess]


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def pages_base_url() -> str:
    return _env("JOB_VIEWER_PAGES_BASE_URL", "https://workroom.empirebox.store").rstrip("/")


def repo_configured() -> bool:
    return bool(_env("JOB_VIEWER_GITHUB_REPO") and _env("JOB_VIEWER_GITHUB_TOKEN"))


class GitPagesPublisher:
    """Clone / commit / push `{slug}/index.html` to the configured Pages repo."""

    def __init__(
        self,
        *,
        repo: Optional[str] = None,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        workdir: Optional[Path] = None,
        runner: Optional[Runner] = None,
        branch: Optional[str] = None,
    ):
        self.repo = repo or _env("JOB_VIEWER_GITHUB_REPO")
        self.token = token or _env("JOB_VIEWER_GITHUB_TOKEN")
        self.base_url = (base_url or pages_base_url()).rstrip("/")
        self.workdir = Path(workdir) if workdir else Path(
            _env("JOB_VIEWER_GIT_WORKDIR") or "/tmp/empire-job-viewer-pages"
        )
        self.branch = branch or _env("JOB_VIEWER_GITHUB_BRANCH", "gh-pages")
        self.runner = runner or subprocess.run

    def _run(self, args: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        return self.runner(args, cwd=str(cwd) if cwd else None, env=env,
                           check=True, capture_output=True, text=True)

    def _clone_url(self) -> str:
        repo = self.repo
        if repo.startswith("https://"):
            rest = repo.split("https://", 1)[1]
            return f"https://x-access-token:{self.token}@{rest}"
        return f"https://x-access-token:{self.token}@github.com/{repo}.git"

    def _repo_dir(self) -> Path:
        if not self.repo or not self.token:
            raise PublishNotConfigured(
                "JOB_VIEWER_GITHUB_REPO and JOB_VIEWER_GITHUB_TOKEN must be set to publish"
            )
        dest = self.workdir / "repo"
        if dest.exists() and (dest / ".git").exists():
            self._run(["git", "fetch", "origin"], cwd=dest)
            self._run(["git", "checkout", self.branch], cwd=dest)
            self._run(["git", "-c", "pull.rebase=false", "pull", "--ff-only", "origin", self.branch], cwd=dest)
            return dest
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        self._run(["git", "clone", "--branch", self.branch, "--single-branch", self._clone_url(), str(dest)])
        return dest

    def publish(self, slug: str, html: str, message: str = "") -> str:
        if _env("JOB_VIEWER_DISABLE_PUBLISH") in {"1", "true", "yes"}:
            raise PublishNotConfigured("publishing is disabled (JOB_VIEWER_DISABLE_PUBLISH)")
        repo_dir = self._repo_dir()
        target = repo_dir / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        self._run(["git", "add", f"{slug}/index.html"], cwd=repo_dir)
        msg = message or f"Update 3D viewer {slug}"
        # Allow empty commit skip: if nothing changed, still return the URL.
        status = self.runner(
            ["git", "status", "--porcelain"], cwd=str(repo_dir),
            capture_output=True, text=True, check=True,
        )
        if status.stdout.strip():
            self._run(["git", "commit", "-m", msg], cwd=repo_dir)
            self._run(["git", "push", "origin", self.branch], cwd=repo_dir)
        return f"{self.base_url}/{slug}/"

    def unpublish(self, slug: str) -> None:
        if _env("JOB_VIEWER_DISABLE_PUBLISH") in {"1", "true", "yes"}:
            raise PublishNotConfigured("publishing is disabled (JOB_VIEWER_DISABLE_PUBLISH)")
        repo_dir = self._repo_dir()
        target = repo_dir / slug
        if not target.exists():
            return
        self._run(["git", "rm", "-r", "-f", slug], cwd=repo_dir)
        self._run(["git", "commit", "-m", f"Unpublish 3D viewer {slug}"], cwd=repo_dir)
        self._run(["git", "push", "origin", self.branch], cwd=repo_dir)


_PUBLISHER = None


def get_publisher():
    global _PUBLISHER
    if _PUBLISHER is not None:
        return _PUBLISHER
    return GitPagesPublisher()


def set_publisher(publisher) -> None:
    """Tests inject MemoryPagesPublisher here. Production leaves this None."""
    global _PUBLISHER
    _PUBLISHER = publisher
