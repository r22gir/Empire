"""Canonical backend data paths.

Keeps production code from reaching into an old checkout such as
``~/empire-repo``. Tests can still monkeypatch module-level path constants.
"""
from __future__ import annotations

import os
from pathlib import Path


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_root() -> Path:
    return Path(os.getenv("EMPIRE_DATA_DIR", backend_root() / "data"))


def quotes_data_dir() -> Path:
    return data_root() / "quotes"


def craftforge_data_dir() -> Path:
    return data_root() / "craftforge"


def craftforge_designs_dir() -> Path:
    return craftforge_data_dir() / "designs"


def quote_pdf_dir() -> Path:
    return quotes_data_dir() / "pdf"
