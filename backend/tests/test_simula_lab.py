import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.simula_lab.generator import generate_samples, hermes_example_count
from app.services.simula_lab.registry import run_dataset
from app.services.simula_lab.schemas import DATASET_ID, EXPECTED_MODES, EXPECTED_ROUTES
from app.services.simula_lab.validator import SimulaValidationError, validate_jsonl, validate_row, validate_rows


def test_valid_sample_accepted():
    row = generate_samples(1)[0]
    validate_row(row)


def test_invalid_expected_mode_rejected():
    row = generate_samples(1)[0]
    row["expected_mode"] = "telepathy"
    assert row["expected_mode"] not in EXPECTED_MODES
    with pytest.raises(SimulaValidationError):
        validate_row(row)


def test_invalid_expected_route_rejected():
    row = generate_samples(1)[0]
    row["expected_route"] = "afterimage_required"
    assert row["expected_route"] not in EXPECTED_ROUTES
    with pytest.raises(SimulaValidationError):
        validate_row(row)


def test_generator_creates_requested_count():
    rows = generate_samples(25)
    assert len(rows) == 25
    assert rows[0]["id"] == f"{DATASET_ID}-001"
    assert rows[-1]["id"] == f"{DATASET_ID}-025"


def test_generated_rows_validate():
    rows = generate_samples(25)
    result = validate_rows(rows)
    assert result.passed is True
    assert result.sample_count == 25
    assert result.errors == []


def test_smoke_script_works_with_temp_output_root(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{BACKEND_ROOT}:{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "simula_lab_smoke.py"),
            "--dataset",
            DATASET_ID,
            "--count",
            "25",
            "--output-root",
            str(tmp_path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    dataset_path = tmp_path / "datasets" / f"{DATASET_ID}.jsonl"
    manifest_path = tmp_path / "manifests" / f"{DATASET_ID}.manifest.json"
    report_path = tmp_path / "reports" / f"{DATASET_ID}.report.json"
    assert dataset_path.exists()
    assert manifest_path.exists()
    assert report_path.exists()
    assert validate_jsonl(dataset_path).passed is True

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["validation_passed"] is True
    assert report["sample_count"] == 25
    assert report["hermes_example_count"] >= 5


def test_hermes_examples_exist():
    rows = generate_samples(25)
    hermes_rows = [row for row in rows if "hermes" in json.dumps(row).lower()]
    assert hermes_example_count(rows) == len(hermes_rows)
    assert len(hermes_rows) >= 5
    assert any(row["requires_approval"] for row in hermes_rows)


def test_no_live_max_or_openclaw_runtime_files_are_modified(tmp_path):
    watched_paths = [
        ROOT / "backend" / "app" / "services" / "max" / "tool_executor.py",
        ROOT / "backend" / "app" / "services" / "max" / "openclaw_gate.py",
        ROOT / "openclaw" / "server.py",
    ]
    before = {path: (path.stat().st_mtime_ns, path.stat().st_size) for path in watched_paths}

    result = run_dataset(dataset_id=DATASET_ID, count=25, output_root=tmp_path)

    assert result["report"]["validation_passed"] is True
    after = {path: (path.stat().st_mtime_ns, path.stat().st_size) for path in watched_paths}
    assert after == before
