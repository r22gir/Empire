"""Dataset registry and output writer for Empire-native SimulaLab."""

from __future__ import annotations

import json
import shlex
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .generator import generate_samples, hermes_example_count
from .schemas import (
    DATASET_ID,
    DEFAULT_OUTPUT_ROOT,
    DOMAIN,
    GENERATOR_ID,
    INTENDED_USE,
    OUTPUT_DIRECTORIES,
    SCHEMA_VERSION,
    SimulaOutputPaths,
)
from .validator import SimulaValidationError, validate_rows


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def get_repo_commit(repo_root: Path | None = None) -> str | None:
    root = repo_root or Path(__file__).resolve().parents[4]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def build_output_paths(dataset_id: str, output_root: Path | str | None = None) -> SimulaOutputPaths:
    root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    return SimulaOutputPaths(
        root=root,
        dataset=root / "datasets" / f"{dataset_id}.jsonl",
        manifest=root / "manifests" / f"{dataset_id}.manifest.json",
        report=root / "reports" / f"{dataset_id}.report.json",
        taxonomies=root / "taxonomies",
        eval_runs=root / "eval_runs",
    )


def ensure_output_tree(output_root: Path | str | None = None) -> SimulaOutputPaths:
    paths = build_output_paths(DATASET_ID, output_root)
    paths.root.mkdir(parents=True, exist_ok=True)
    for directory in OUTPUT_DIRECTORIES:
        (paths.root / directory).mkdir(parents=True, exist_ok=True)
    return paths


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _command_string(argv: list[str] | None) -> str | None:
    if not argv:
        return None
    return " ".join(shlex.quote(part) for part in argv)


def _counter(rows: list[dict[str, Any]], field_name: str) -> dict[str, int]:
    return dict(sorted(Counter(row[field_name] for row in rows).items()))


def build_manifest(
    *,
    rows: list[dict[str, Any]],
    paths: SimulaOutputPaths,
    command: list[str] | None,
    created_at: str,
) -> dict[str, Any]:
    return {
        "dataset_id": DATASET_ID,
        "domain": DOMAIN,
        "created_at": created_at,
        "generator": GENERATOR_ID,
        "model_provider": None,
        "teacher_model": None,
        "critic_model": None,
        "sample_count": len(rows),
        "schema_version": SCHEMA_VERSION,
        "synthetic": True,
        "intended_use": INTENDED_USE,
        "repo_commit": get_repo_commit(),
        "output_path": str(paths.dataset),
        "command": _command_string(command),
    }


def build_report(
    *,
    rows: list[dict[str, Any]],
    paths: SimulaOutputPaths,
    validation_passed: bool,
    errors: list[str],
    warnings: list[str],
    created_at: str,
) -> dict[str, Any]:
    return {
        "dataset_id": DATASET_ID,
        "domain": DOMAIN,
        "created_at": created_at,
        "validation_passed": validation_passed,
        "validation": {
            "passed": validation_passed,
            "errors": errors,
            "warnings": warnings,
        },
        "sample_count": len(rows),
        "count_by_expected_mode": _counter(rows, "expected_mode"),
        "count_by_expected_route": _counter(rows, "expected_route"),
        "hermes_example_count": hermes_example_count(rows),
        "warnings": warnings,
        "output_paths": paths.as_strings(),
        "notes": [
            "Empire-native deterministic Phase 1 dataset/eval pilot.",
            "OpenSimula/AfterImage is future optional adapter work only and is not used in Phase 1.",
            "No GPU, CUDA, vLLM, cloud API, live MAX runtime, or OpenClaw runtime dependency is required.",
        ],
    }


def run_dataset(
    *,
    dataset_id: str,
    count: int,
    output_root: Path | str | None = None,
    dry_run: bool = False,
    command: list[str] | None = None,
) -> dict[str, Any]:
    if dataset_id != DATASET_ID:
        raise ValueError(f"unsupported dataset: {dataset_id}")

    rows = generate_samples(count)
    validation = validate_rows(rows)
    paths = build_output_paths(dataset_id, output_root)
    created_at = utc_now_iso()
    warnings: list[str] = []

    manifest = build_manifest(rows=rows, paths=paths, command=command, created_at=created_at)
    report = build_report(
        rows=rows,
        paths=paths,
        validation_passed=validation.passed,
        errors=validation.errors,
        warnings=warnings + validation.warnings,
        created_at=created_at,
    )

    if not validation.passed:
        if not dry_run:
            ensure_output_tree(output_root)
            _write_json(paths.report, report)
        raise SimulaValidationError("generated dataset failed validation: " + "; ".join(validation.errors))

    if not dry_run:
        ensure_output_tree(output_root)
        _write_jsonl(paths.dataset, rows)
        _write_json(paths.manifest, manifest)
        _write_json(paths.report, report)

    return {
        "dataset_id": dataset_id,
        "dry_run": dry_run,
        "rows": rows,
        "manifest": manifest,
        "report": report,
        "paths": paths.as_strings(),
    }
