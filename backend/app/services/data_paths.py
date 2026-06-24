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


# --- additive data-dir helpers (Phase 3, behavior-neutral; nothing calls these yet) ---
# Every path resolves through data_root(), i.e. honors EMPIRE_DATA_DIR at cutover.

def db_path(name: str = "empire.db") -> Path:
    return data_root() / name

def brain_dir() -> Path:
    return data_root() / "brain"

def uploads_images_dir() -> Path:
    return data_root() / "uploads" / "images"

def presentations_dir() -> Path:
    return data_root() / "presentations"

def photos_dir() -> Path:
    return data_root() / "photos"

def generated_dir() -> Path:
    return data_root() / "generated"

def intake_uploads_dir() -> Path:
    return data_root() / "intake_uploads"

def notes_uploads_dir() -> Path:
    return data_root() / "notes_uploads"

def socialforge_dir() -> Path:
    return data_root() / "socialforge"

def llcfactory_dir() -> Path:
    return data_root() / "llcfactory"

def reports_dir() -> Path:
    return data_root() / "reports"

def chats_dir() -> Path:
    return data_root() / "chats"

def inbox_dir() -> Path:
    return data_root() / "inbox"

def apostapp_dir() -> Path:
    return data_root() / "apostapp"

def transcriptforge_dir() -> Path:
    return data_root() / "transcriptforge"

def measurements_dir() -> Path:
    return data_root() / "measurements"
