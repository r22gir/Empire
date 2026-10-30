#!/usr/bin/env python3
"""Import Fine Fabrics vendor CSVs from the configured data directory.

Usage:
  python scripts/import_fine_fabrics.py --list
  python scripts/import_fine_fabrics.py
  python scripts/import_fine_fabrics.py --file greenhouse_prices.csv

Reads FINE_FABRICS_DATA_DIR (default: sibling of EMPIRE_TASK_DB named
fine_fabrics_vendor). Never commit live mill books — only mock files
under backend/app/data/fine_fabrics/ belong in git.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Empire Fine Fabrics vendor CSVs")
    parser.add_argument("--dir", dest="directory", help="Override FINE_FABRICS_DATA_DIR")
    parser.add_argument("--file", dest="filename", help="Import a single CSV from the data dir")
    parser.add_argument("--list", action="store_true", help="List CSVs in the data dir")
    args = parser.parse_args()

    if args.directory:
        os.environ["FINE_FABRICS_DATA_DIR"] = args.directory

    from app.services.fine_fabrics.importer import data_dir, import_from_dir, list_import_files
    from app.services.fine_fabrics.schema import ensure_fine_fabrics_schema

    ensure_fine_fabrics_schema()
    root = Path(args.directory) if args.directory else data_dir()
    if args.list:
        print(json.dumps({"directory": str(root), "files": list_import_files(root)}, indent=2))
        return 0
    report = import_from_dir(root, filename=args.filename)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
