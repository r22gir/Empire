"""H57 Phase 3 — Canonical root tests.

Per DISPATCH H57 Phase 3 (2026-08-19):
  - 3b: file/repo tools take paths RELATIVE to a canonical root
    resolved in the tool layer; refuse escapes (.., symlinks).
  - 3c: positive identification via `.empire-canonical` marker.

Tests:
  - Absolute path outside root → refused
  - Relative path with .. → refused
  - Symlink pointing outside → refused
  - Canonical read → succeeds
  - Missing marker → refused with clear reason
  - Relative path with no root → resolves to CANONICAL
  - NEGATIVE FIXTURE: literal "~/empire-repo/claude/DISPATCH_2026-08-17_drapery_r3.md"
    (the exact path MAX proposed) must be refused.
  - Write through quotes.py lands in the canonical tree.
"""
from __future__ import annotations

import os
import pytest
from pathlib import Path

from app.services.drawing.canonical_path import (
    resolve_canonical_root,
    resolve_path_under_canonical_root,
    CanonicalRootError,
)


# ── Marker presence ─────────────────────────────────────────────

class TestCanonicalMarkerPresent:
    """Per H57 Phase 3c: positive identification. The canonical repo
    MUST have the `.empire-canonical` marker file."""

    def test_marker_file_exists(self):
        canonical = resolve_canonical_root()
        assert canonical.is_dir()
        marker = canonical / ".empire-canonical"
        assert marker.is_file(), (
            f"canonical root {canonical} is missing .empire-canonical "
            f"marker — refusing to proceed without positive identification"
        )

    def test_marker_starts_with_canonical_token(self):
        canonical = resolve_canonical_root()
        content = (canonical / ".empire-canonical").read_text(
            encoding="utf-8"
        )
        assert content.startswith("EmpireBox canonical root"), (
            f"canonical marker content is wrong: {content[:80]!r}"
        )


# ── 3b — relative path resolution ─────────────────────────────────

class TestRelativePathResolvesToCanonical:
    """Per dispatch 3b: file/repo tools take paths RELATIVE to
    canonical root. A relative path with no root resolves to the
    canonical tree (not to `~/empire-repo/`)."""

    def test_relative_path_resolves_under_canonical(self):
        # No root, no `..`, no leading slash — should resolve to
        # canonical repo's path.
        resolved = resolve_path_under_canonical_root(
            "backend/app/main.py"
        )
        canonical = resolve_canonical_root()
        assert resolved.is_relative_to(canonical.resolve()), (
            f"relative path resolved to {resolved}, which is outside "
            f"canonical repo {canonical}"
        )

    def test_relative_path_with_dotdot_is_refused(self):
        # `..` escapes the canonical repo. Must refuse.
        # The realistic escape shape — user types a path that
        # traverses up out of canonical via `..` components.
        with pytest.raises(CanonicalRootError) as exc:
            resolve_path_under_canonical_root(
                "backend/data/uploads/../../../etc/passwd"
            )
        assert "escapes" in str(exc.value).lower() or ".." in str(exc.value).lower() or "canonical" in str(exc.value).lower()

    def test_negative_fixture_maxs_proposed_path_refused(self):
        """The literal path MAX proposed tonight — the exact bug
        the dispatch is fixing."""
        with pytest.raises(CanonicalRootError):
            resolve_path_under_canonical_root(
                "~/empire-repo/claude/DISPATCH_2026-08-17_drapery_r3.md"
            )


# ── 3b — absolute paths ──────────────────────────────────────────

class TestAbsolutePathPolicy:
    """Per dispatch 3b: absolute paths are checked against canonical.
    Outside canonical → refused. Inside → allowed."""

    def test_absolute_path_inside_canonical_allowed(self):
        canonical = resolve_canonical_root()
        path_inside = canonical / "backend" / "data" / "drawings"
        resolved = resolve_path_under_canonical_root(str(path_inside))
        assert resolved == path_inside.resolve()

    def test_absolute_path_outside_canonical_refused(self):
        with pytest.raises(CanonicalRootError):
            resolve_path_under_canonical_root("/etc/passwd")

    def test_stale_fork_path_refused(self):
        """The whole point of H57 Phase 3: the stale fork
        ~/empire-repo/ MUST BE UNREACHABLE."""
        stale = Path.home() / "empire-repo" / "backend" / "main.py"
        with pytest.raises(CanonicalRootError) as exc:
            resolve_path_under_canonical_root(str(stale))
        assert "stale" in str(exc.value).lower() or "canonical" in str(exc.value).lower()


# ── 3b — symlink escapes ──────────────────────────────────────────

class TestSymlinkEscapeRefused:
    """Per dispatch 3b: symlinks pointing outside canonical refused.
    The resolver uses os.path.realpath which follows symlinks —
    the escaped path lands outside the canonical repo → refuse."""

    def test_symlink_outside_canonical_refused(self, tmp_path):
        # Create a symlink in canonical repo pointing to outside canonical.
        # Use a unique target per test run — pytest's tmp_path gives
        # per-test isolation (avoids FileExistsError from previous runs
        # polluting /tmp).
        canonical = resolve_canonical_root()
        # Symlink target OUTSIDE canonical. Pick a name that's unique
        # to this test (pytest_tmp_path gives us that) AND outside the
        # canonical root. We pick a tmp_path under /tmp (not under
        # canonical). Path.resolve() follows symlinks so this symlink
        # resolves to /tmp/<unique>, which is OUTSIDE canonical.
        outside_target = tmp_path / "outside_repo"
        symlink_path = canonical / "backend" / "tests" / "evil_link"
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
        symlink_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            symlink_path.symlink_to(outside_target)
            with pytest.raises(CanonicalRootError):
                resolve_path_under_canonical_root(str(symlink_path))
        finally:
            if symlink_path.exists() or symlink_path.is_symlink():
                symlink_path.unlink()


# ── Missing marker — refuse loudly ────────────────────────────────

class TestMissingMarkerRefused:
    """Per dispatch 3c: missing `.empire-canonical` marker →
    CanonicalRootError with a clear reason."""

    def test_resolve_canonical_root_raises_when_marker_missing(
        self, tmp_path
    ):
        # tmp_path has no `.empire-canonical` marker.
        # Walking up 8 levels would land at /tmp or / which still
        # has no marker → raise.
        with pytest.raises(CanonicalRootError) as exc:
            resolve_canonical_root(tmp_path)
        assert "marker" in str(exc.value).lower()
        assert "refusing" in str(exc.value).lower() or "canonical" in str(exc.value).lower()


# ── Tool layer — file_read / file_write use canonical resolver ──

class TestFileToolUsesCanonical:
    """Per dispatch 3b: file/repo tools (file_read, file_write)
    resolve via canonical_path — NOT `~/empire-repo/`. The previous
    default was the stale-fork leak."""

    def test_file_read_resolves_relative_via_canonical(self, monkeypatch):
        from app.services.max import tool_executor as te
        from app.services.max.tool_safety import validate_path

        # Mock open to capture the path the tool tries to read.
        captured_path = []
        def fake_open(path, *args, **kwargs):
            captured_path.append(os.path.realpath(path))
            from io import StringIO
            return StringIO("test content\n")

        monkeypatch.setattr("builtins.open", fake_open)
        result = te._file_read({"path": "backend/app/main.py"})
        assert result.success, f"file_read failed: {result.error}"
        canonical = resolve_canonical_root()
        assert captured_path[0].startswith(str(canonical.resolve())), (
            f"file_read opened {captured_path[0]} which is outside "
            f"canonical {canonical}"
        )

    def test_file_write_resolves_relative_via_canonical(self, monkeypatch):
        from app.services.max import tool_executor as te

        captured_path = []
        def fake_open(path, *args, **kwargs):
            captured_path.append(os.path.realpath(path))
            from io import StringIO
            return StringIO()

        monkeypatch.setattr("builtins.open", fake_open)
        result = te._file_write(
            {"path": "backend/data/test_h57.txt", "content": "ok"}
        )
        assert result.success, f"file_write failed: {result.error}"
        canonical = resolve_canonical_root()
        assert captured_path[0].startswith(str(canonical.resolve())), (
            f"file_write wrote to {captured_path[0]} which is outside "
            f"canonical {canonical}"
        )

    def test_file_read_absolute_outside_canonical_refused(
        self, monkeypatch
    ):
        from app.services.max import tool_executor as te
        result = te._file_read({"path": "/etc/passwd"})
        assert not result.success
        assert "canonical" in result.error.lower() or "stale" in result.error.lower() or "escapes" in result.error.lower()


# ── system_prompt.py git cwd — canonical, not stale fork ──────

class TestSystemPromptGitContextIsCanonical:
    """Per dispatch: MAX's git context currently uses the stale
    fork as cwd. Post-fix, it must use the canonical repo."""

    def test_system_prompt_git_cwd_resolves_to_canonical(self):
        from app.services.max import system_prompt
        # Inspect the source — the cwd must be derived from the
        # canonical resolver, not from a hardcoded `~/empire-repo`.
        src = Path(system_prompt.__file__).read_text(encoding="utf-8")
        assert "expanduser(\"~/empire-repo\")" not in src, (
            "system_prompt.py still hardcodes the stale fork ~/empire-repo "
            "as git cwd — must resolve via canonical_path"
        )
        assert "resolve_canonical_root" in src or "canonical_path" in src


# ── quotes.py write target — canonical tree ──────────────────────

class TestQuotesWriteLandsInCanonical:
    """Per dispatch: quotes.py writes UPLOADS and GENERATED files
    into the stale fork. Live business data in the wrong tree outranks
    everything else. Post-fix, these write paths resolve via canonical."""

    def test_quotes_uploads_dir_resolves_to_canonical(self):
        from app.routers import quotes
        # Inspect the source — must resolve via canonical_path, not
        # hardcode the stale fork.
        src = Path(quotes.__file__).read_text(encoding="utf-8")
        assert 'expanduser("~/empire-repo/backend/data/uploads' not in src, (
            "quotes.py still hardcodes the stale fork for uploads"
        )
        assert "resolve_path_under_canonical_root" in src or "canonical_path" in src

    def test_quotes_generated_path_resolves_to_canonical(self):
        from app.routers import quotes
        src = Path(quotes.__file__).read_text(encoding="utf-8")
        assert "expanduser(f\"~/empire-repo/backend/data/generated" not in src, (
            "quotes.py still hardcodes the stale fork for generated paths"
        )


# ── openclaw_worker drawings dir — canonical tree ──────────────

class TestOpenclawWorkerDrawingsDirIsCanonical:
    """Per dispatch: openclaw_worker.py writes DRAWINGS to the
    stale fork. Post-fix, must land in canonical."""

    def test_openclaw_worker_drawings_dir_resolves_to_canonical(self):
        from app.services import openclaw_worker
        src = Path(openclaw_worker.__file__).read_text(encoding="utf-8")
        assert 'expanduser("~/empire-repo/uploads/openclaw_drawings")' not in src, (
            "openclaw_worker.py still hardcodes the stale fork for drawings"
        )
        assert "resolve_path_under_canonical_root" in src or "canonical_path" in src


# ── validator convergence — ONE validator, not two ─────────────

class TestSingleValidator:
    """Per dispatch 3b: ONE validator, NOT two. Two validators
    where one is right and one is wrong is doctrine-rule-12 risk."""

    def test_tool_safety_validate_path_delegates_to_canonical(self):
        """tool_safety.validate_path must delegate to canonical_path
        — it must NOT keep its own stale-fork-permissive logic."""
        from app.services.max import tool_safety
        src = Path(tool_safety.__file__).read_text(encoding="utf-8")
        # The old ALLOWED_ROOTS containing `~/empire-repo` must be gone.
        assert 'expanduser("~/empire-repo"),' not in src, (
            "tool_safety.py still has the OLD ALLOWED_ROOTS list "
            "containing the stale fork ~/empire-repo"
        )
        # It must call canonical_path.resolve_path_under_canonical_root.
        assert "resolve_path_under_canonical_root" in src, (
            "tool_safety.py does NOT delegate to canonical_path"
        )


# ── Stale fork in ALLOWED_ROOTS — explicitly REMOVED ───────────

class TestStaleForkUnreachable:
    """Per dispatch 3b: make the wrong repo UNREACHABLE."""

    def test_stale_fork_path_refused_by_resolver(self):
        stale = str(Path.home() / "empire-repo")
        # Any path under the stale fork must refuse. This is the
        # structural fix the dispatch requires.
        with pytest.raises(CanonicalRootError):
            resolve_path_under_canonical_root(f"{stale}/backend/main.py")

    def test_stale_fork_path_via_validate_path_refused(self):
        """The single validator must refuse the stale fork too."""
        from app.services.max import tool_safety
        stale = str(Path.home() / "empire-repo")
        ok, reason = tool_safety.validate_path(f"{stale}/backend/main.py")
        assert not ok
        assert "stale" in reason.lower() or "canonical" in reason.lower()


# ── Phase 3a test fixtures (existing tests) — show the diffs ────
#
# The 11 test fixtures asserting the OLD default root encode the bug.
# Below: a doc block listing the tests so the founder can decide which
# to look at. The dispatch rule: "Replacing them is correct — but show
# the diff per test, and say which ones I should look at."
#
# These tests have NOT been edited in this commit (per the user's rule:
# "Do not rewrite them inside H57 — that would hide a real staleness debt
# in an unrelated commit"). The fix lives in the runtime; the test
# fixtures assert the OLD path. They will FAIL after this commit lands.
# The dispatch acknowledges this as the correct outcome.
#
# Tests that assert `~/empire-repo/...`:
#   1. backend/tests/test_canonical_pricing_engine.py
#   2. backend/tests/test_dev_git_runtime_truth.py
#   3. backend/tests/test_drawing_flow_wiring_hotfix4_0.py
#   4. backend/tests/test_openclaw_worker.py
#   5. backend/tests/test_payments_webhook_fail_closed.py
# Plus other unit files in backend/tests/ that hardcode the path.
#
# These tests will start FAILING after this commit lands. They need
# updating to use the canonical resolver. Per dispatch: the update is
# CORRECT — but show the diff and let the founder pick which to look at.
#
# This commit does NOT touch those tests (per dispatch rule). They
# are listed here as a tracking artifact only.