"""
Tests for scripts/stamp_provenance.py — Doctrine §IX provenance stamper.

The stampers GUARDS are what make it trustworthy. A guard that has never
been shown to fire is not evidence; this file proves each one fires.

Required cases (per dispatch):
    - clean tracked file     -> header names branch and commit, no dirty mark
    - MODIFIED tracked file  -> header carries the dirty marker (+dirty)
    - untracked file         -> header says @ untracked, names no commit
    - re-stamp               -> exactly one header line, not two
    - source file unchanged  -> assert the original bytes are byte-identical
                                after the run

Each test builds its own git work tree under tmp_path so the real repo
is never dirtied.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


# Resolve the script via the test file's own path so the test does not
# depend on the caller's CWD.
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "stamp_provenance.py"


# A SOURCE: header on a single line. Anchored with ^…$ over MULTILINE so
# we can count header occurrences across the whole file.
_HEADER_LINE = re.compile(r"^SOURCE: .*$", re.MULTILINE)


def _run_git(args: list[str], cwd: Path) -> str:
    r = subprocess.run(
        ["git", *args], cwd=str(cwd),
        capture_output=True, text=True, check=True,
    )
    return r.stdout.strip()


def _make_repo(tmp_path: Path) -> Path:
    """Initialise a fresh git repo under tmp_path with one tracked commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(["init", "-q", "-b", "main"], repo)
    _run_git(["config", "user.email", "test@example.invalid"], repo)
    _run_git(["config", "user.name", "Test"], repo)
    _run_git(["config", "commit.gpgsign", "false"], repo)
    # Seed an initial commit so HEAD exists for rev-parse.
    seed = repo / "README.md"
    seed.write_text("seed\n", encoding="utf-8")
    _run_git(["add", "README.md"], repo)
    _run_git(["commit", "-q", "-m", "init"], repo)
    return repo


def _write_and_commit(path: Path, content: str, message: str) -> str:
    """Write `content` to `path` (mkdir parents), `git add` it, commit it.
    Returns the short commit SHA after the commit.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    repo = _repo_root(path)
    _run_git(["add", str(path.relative_to(repo))], repo)
    _run_git(["commit", "-q", "-m", message], repo)
    return _run_git(["rev-parse", "--short", "HEAD"], repo)


def _repo_root(path: Path) -> Path:
    """Walk up from `path` to find the enclosing git repo root.

    Falls back to the path itself if no parent contains .git/.
    """
    cur = path if path.is_dir() else path.parent
    for cand in (cur, *cur.parents):
        if (cand / ".git").exists():
            return cand
    raise RuntimeError(f"no .git found above {path}")


def _run_stamp(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke the script as a real subprocess from `cwd`."""
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        cwd=str(cwd), capture_output=True, text=True,
    )


def _today_iso() -> str:
    import datetime as _dt
    return _dt.date.today().isoformat()


# ──────────────────────────────────────────────────────────────────────
# Cases
# ──────────────────────────────────────────────────────────────────────


def test_clean_tracked_file_emits_branch_and_commit_without_dirty(tmp_path):
    """Happy path. Header names branch and commit, no `+dirty`."""
    repo = _make_repo(tmp_path)
    doc = repo / "doc.md"
    short_sha = _write_and_commit(
        doc, "hello world\n", "initial commit",
    )
    out = tmp_path / "out"
    before = doc.read_bytes()

    result = _run_stamp(repo, "doc.md", "--out", str(out))

    exported = out / "doc.md"
    assert result.returncode == 0, result.stderr
    assert exported.exists()
    body = exported.read_text(encoding="utf-8")
    first_line = body.splitlines()[0]

    today = _today_iso()
    expected_prefix = f"SOURCE: main @ {short_sha} · exported {today}"
    assert first_line == expected_prefix, (
        f"first line was {first_line!r}, "
        f"expected {expected_prefix!r}"
    )
    assert "+dirty" not in first_line
    assert "@ untracked" not in body
    # Source untouched.
    assert doc.read_bytes() == before


def test_modified_tracked_file_carries_dirty_marker(tmp_path):
    """The guard fires: tracked + modifications -> +dirty.

    Constructs the dirty state INSIDE tmp_path. Does not touch the real repo.
    """
    repo = _make_repo(tmp_path)
    doc = repo / "doc.md"
    short_sha = _write_and_commit(
        doc, "first version\n", "initial commit",
    )
    # Modify AFTER commit — git status --porcelain must report it.
    doc.write_text("first version\nsecond version\n", encoding="utf-8")
    # Sanity: confirm git sees the modification.
    status = _run_git(["status", "--porcelain", "--", "doc.md"], repo)
    assert "M" in status, f"setup failed; porcelain was: {status!r}"

    out = tmp_path / "out"
    result = _run_stamp(repo, "doc.md", "--out", str(out))

    assert result.returncode == 0, result.stderr
    first_line = (out / "doc.md").read_text(encoding="utf-8").splitlines()[0]
    assert "+dirty" in first_line, f"expected +dirty marker in: {first_line!r}"
    assert short_sha in first_line, (
        f"expected commit anchor {short_sha} in: {first_line!r}"
    )


def test_untracked_file_says_untracked_and_names_no_commit(tmp_path):
    """Untracked: header says @ untracked; no commit SHA is named."""
    repo = _make_repo(tmp_path)
    # Create the file but do NOT `git add` / commit it.
    doc = repo / "scratch.md"
    doc.write_text("scratch\n", encoding="utf-8")

    # Sanity: file is genuinely untracked.
    status = _run_git(["status", "--porcelain", "--", "scratch.md"], repo)
    assert "??" in status, f"setup failed; porcelain was: {status!r}"

    out = tmp_path / "out"
    result = _run_stamp(repo, "scratch.md", "--out", str(out))

    assert result.returncode == 0, result.stderr
    first_line = (out / "scratch.md").read_text(
        encoding="utf-8",
    ).splitlines()[0]

    assert "@ untracked" in first_line, (
        f"expected `@ untracked` in header: {first_line!r}"
    )
    # No hex-looking commit substring follows the @. We assert no
    # 7+ hex-char SHA appears immediately after @.
    m = re.search(r"@ (\S+)", first_line)
    assert m is not None
    tail = m.group(1)
    assert not re.search(r"[0-9a-f]{7,}", tail), (
        f"untracked header named a commit-looking token: {tail!r}"
    )


def test_restamp_replaces_header_instead_of_stacking(tmp_path):
    """Idempotency: re-stamp produces exactly one SOURCE: line."""
    repo = _make_repo(tmp_path)
    doc = repo / "doc.md"
    _write_and_commit(doc, "v1\n", "first")

    out = tmp_path / "out"
    r1 = _run_stamp(repo, "doc.md", "--out", str(out))
    assert r1.returncode == 0, r1.stderr

    exported = out / "doc.md"
    after_first = exported.read_text(encoding="utf-8")
    assert len(_HEADER_LINE.findall(after_first)) == 1

    # Modify the source between stamps so the dirty state changes —
    # this also exercises that re-stamping reflects new state.
    doc.write_text("v2\n", encoding="utf-8")
    r2 = _run_stamp(repo, "doc.md", "--out", str(out))
    assert r2.returncode == 0, r2.stderr

    after_second = exported.read_text(encoding="utf-8")
    matches = _HEADER_LINE.findall(after_second)
    assert len(matches) == 1, (
        f"expected exactly one SOURCE: line, got {len(matches)}: "
        f"{after_second!r}"
    )
    # The single header must reflect current (dirty) state.
    assert "+dirty" in matches[0]


def test_source_file_bytes_unchanged_after_run(tmp_path):
    """Guard against silent in-place mutation. Original bytes preserved.

    Also: pre-existing export survives unchanged except for the header line.
    """
    repo = _make_repo(tmp_path)
    doc = repo / "doc.md"
    payload = "BYTE-IDENTITY-CANARY: do not touch me\n"
    _write_and_commit(doc, payload, "init")
    # also dirty the file
    doc.write_text(payload + "extra line that the stamper must not see in the source\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    out_path = out / "doc.md"
    out_path.write_bytes(b"PRE-EXISTING EXPORT\n")
    before_bytes = doc.read_bytes()
    pre_export_bytes = out_path.read_bytes()

    result = _run_stamp(repo, "doc.md", "--out", str(out))
    assert result.returncode == 0, result.stderr

    # Source file untouched.
    after_bytes = doc.read_bytes()
    assert after_bytes == before_bytes, "source file was mutated"

    # Destination carries exactly one SOURCE: line.
    exported = out_path.read_text(encoding="utf-8")
    assert len(_HEADER_LINE.findall(exported)) == 1
    # Pre-existing export body preserved beneath the header.
    assert "PRE-EXISTING EXPORT" in exported
    # Only the first line of the export changed — the header.
    lines = exported.splitlines(keepends=False)
    # First line is the new SOURCE: header.
    assert lines[0].startswith("SOURCE: ")
    # All subsequent lines match what was there before.
    body_lines = lines[1:]
    pre_body_lines = pre_export_bytes.decode("utf-8").splitlines()
    assert body_lines == pre_body_lines


def test_outside_work_tree_refuses_nonzero(tmp_path):
    """Run the script from a non-repo CWD — must exit non-zero, no write."""
    non_repo = tmp_path / "nowhere"
    non_repo.mkdir()
    doc = non_repo / "doc.md"
    doc.write_text("x\n", encoding="utf-8")
    out = tmp_path / "out"

    result = _run_stamp(non_repo, "doc.md", "--out", str(out))

    assert result.returncode != 0, (
        f"expected non-zero exit outside work tree, got rc={result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert not (out / "doc.md").exists(), (
        "no export should be written when refusing"
    )
