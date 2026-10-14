"""Readable WhatsApp webhook/send logs: journald (via stderr) + rotated file.

systemd/empire-backend.service already sets StandardOutput=journal and
SyslogIdentifier=empire-backend. This module also writes a rotating file
under EMPIRE_DATA_DIR/logs/whatsapp.log so send errors stay readable when
journalctl is not at hand. Never logs tokens or app secrets.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.services.data_paths import data_root

LOGGER_NAMES = ("max.whatsapp", "max.whatsapp_log", "max.whatsapp_calling")
_MARKER = "_empire_whatsapp_file"


def log_path() -> Path:
    return data_root() / "logs" / "whatsapp.log"


def ensure_whatsapp_file_logging() -> Path:
    """Idempotent. Attaches a rotating file handler to WhatsApp loggers."""
    dest = log_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest_key = str(dest.resolve()) if dest.parent.exists() else str(dest)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    for name in LOGGER_NAMES:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        already = False
        for handler in logger.handlers:
            if getattr(handler, _MARKER, False) and getattr(handler, "baseFilename", "") == dest_key:
                already = True
                break
        if already:
            logger.propagate = True
            continue
        handler = RotatingFileHandler(
            dest,
            maxBytes=5 * 1024 * 1024,
            backupCount=7,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        setattr(handler, _MARKER, True)
        logger.addHandler(handler)
        # Propagate so uvicorn/journald still sees the same lines.
        logger.propagate = True
    return dest
