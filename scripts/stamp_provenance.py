#!/usr/bin/env python3
"""
stamp_provenance.py — Doctrine §IX provenance stamper for Empire knowledge exports.

Purpose
    For each input file, copy it to <out>/<basename> with a provenance line
    prepended as the FIRST line of the copy. Source files are NEVER modified
    in place; the repo copy stays clean and only the exported copy carries
    the header.

Usage
    stamp_provenance.py <file>... --out <dir>

Header format (exact, single line):
    SOURCE: <branch> @ <commit>[+dirty] · exported <YYYY-MM-DD>

Rules — each is the point of the tool, not decoration
    1. The repo copy of every source file is untouched. The header lives
       only on the exported copy. Stamping tracked files in place would
       produce churn on every commit.
    2. Branch and commit come from git, never from caller arguments. The
       header is therefore reproducible from the working tree alone.
    3. Honesty on uncertainty — a provenance line that overstates its own
       certainty is worse than none, because it is trusted:
         - tracked file with uncommitted modifications -> the commit field
           carries a dirty marker, e.g. `@ 6870255+dirty`
         - file not tracked by git                     -> the header says
           so explicitly (`@ untracked`) and names no commit
         - invocation outside a git work tree         -> refuse, exit
           non-zero. The tool never emits a clean-looking anchor for
           content that does not match it.
    4. Idempotent on the destination: re-stamping a destination that
       already carries a SOURCE: header replaces that header rather than
       stacking a second one. Two passes produce one header.
    5. Exit non-zero on any failure. Silence is not success.

Stdlib + git only. No new packages.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# A SOURCE: header line at the start of the destination file. MULTILINE
# so $ matches the end-of-line, not end-of-string, and count=1 in
# re.sub still replaces only the first occurrence.
_HEADER_PATTERN = re.compile(r"^SOURCE: .*$", re.MULTILINE)


def _die(msg: str, code: int = 1) -> None:
    sys.stderr.write(f"stamp_provenance: {msg}\n")
    sys.exit(code)


def _git(*args: str, cwd: Path) -> str:
    """Run a git command, return trimmed stdout. Exit non-zero on failure."""
    result = subprocess.run(
        ("git",) + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _die(
            f"git {' '.join(args)} failed: "
            f"{result.stderr.strip() or 'no stderr'}"
        )
    return result.stdout.strip()


def _assert_inside_work_tree(cwd: Path) -> None:
    try:
        inside = _git("rev-parse", "--is-inside-work-tree", cwd=cwd)
    except SystemExit:
        raise
    if inside != "true":
        _die(f"not inside a git work tree (cwd={cwd})")


def _branch_and_commit(cwd: Path) -> tuple[str, str]:
    branch = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
    commit = _git("rev-parse", "--short", "HEAD", cwd=cwd)
    if branch == "HEAD":
        # detached HEAD — name the worktree-side fact rather than a
        # branch that does not exist
        branch = f"detached@{commit}"
    return branch, commit


def _is_tracked(path: Path, cwd: Path) -> bool:
    r = subprocess.run(
        ("git", "ls-files", "--error-unmatch", "--", str(path)),
        cwd=str(cwd), capture_output=True, text=True,
    )
    return r.returncode == 0


def _is_path_dirty(path: Path, cwd: Path) -> bool:
    # `git status --porcelain` reports both staged and unstaged
    # modifications as non-empty lines. Empty stdout = clean.
    out = _git("status", "--porcelain", "--", str(path), cwd=cwd)
    return bool(out)


def _build_header(branch: str, commit_field: str, today: str) -> str:
    return f"SOURCE: {branch} @ {commit_field} · exported {today}"


def _replace_or_prepend_header(content: str, header: str) -> str:
    """If `content` starts with a SOURCE: line, replace just that line.
    Otherwise prepend `header` as the first line.
    """
    if _HEADER_PATTERN.match(content):
        return _HEADER_PATTERN.sub(header, content, count=1)
    return header + "\n" + content


def _stamp_one(
    source: Path, out_dir: Path, cwd: Path,
    branch: str, commit: str, today: str,
) -> Path:
    abs_source = source.resolve()
    tracked = _is_tracked(abs_source, cwd)

    if tracked:
        commit_field = f"{commit}+dirty" if _is_path_dirty(abs_source, cwd) else commit
    else:
        commit_field = "untracked"

    header = _build_header(branch, commit_field, today)

    out_path = out_dir / abs_source.name
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Read source bytes — do NOT modify source.
    source_bytes = abs_source.read_bytes()
    try:
        source_text = source_bytes.decode("utf-8")
    except UnicodeDecodeError:
        _die(f"{source} is not valid UTF-8; refusing to stamp binary content")

    if out_path.exists():
        existing = out_path.read_text(encoding="utf-8")
        new_content = _replace_or_prepend_header(existing, header)
    else:
        new_content = header + "\n" + source_text

    out_path.write_text(new_content, encoding="utf-8")
    return out_path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Stamp Doctrine §IX provenance onto exported copies.",
    )
    parser.add_argument("files", nargs="+", help="source files to stamp")
    parser.add_argument(
        "--out", required=True,
        help="export directory (created if absent)",
    )
    args = parser.parse_args(argv)

    cwd = Path.cwd().resolve()
    _assert_inside_work_tree(cwd)
    branch, commit = _branch_and_commit(cwd)
    today = date.today().isoformat()

    out_dir = Path(args.out).resolve()
    if out_dir == cwd:
        _die(f"--out must not equal the work tree root ({cwd})")
    if out_dir.exists() and not out_dir.is_dir():
        _die(f"--out exists and is not a directory: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    for f in args.files:
        source = Path(f).resolve()
        if not source.exists():
            _die(f"source does not exist: {f}")
        if not source.is_file():
            _die(f"source is not a regular file: {f}")
        stamped = _stamp_one(source, out_dir, cwd, branch, commit, today)
        print(stamped)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
