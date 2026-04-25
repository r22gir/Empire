#!/usr/bin/env python3
"""Smoke command for the Empire-native SimulaLab Phase 1 pilot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.simula_lab.registry import run_dataset  # noqa: E402
from app.services.simula_lab.schemas import DATASET_ID  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a deterministic SimulaLab Phase 1 dataset.")
    parser.add_argument("--dataset", default=DATASET_ID, help=f"Dataset id to generate. Default: {DATASET_ID}")
    parser.add_argument("--count", type=int, default=25, help="Number of examples to generate.")
    parser.add_argument("--output-root", default=None, help="Output root. Default: /data/empire/simula")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print summary without writing files.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_dataset(
        dataset_id=args.dataset,
        count=args.count,
        output_root=args.output_root,
        dry_run=args.dry_run,
        command=sys.argv,
    )
    summary = {
        "dataset_id": result["dataset_id"],
        "dry_run": result["dry_run"],
        "sample_count": result["report"]["sample_count"],
        "validation_passed": result["report"]["validation_passed"],
        "hermes_example_count": result["report"]["hermes_example_count"],
        "output_paths": result["paths"],
        "notes": result["report"]["notes"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
