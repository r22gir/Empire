"""This instance's own API origin.

Workroom leaves ``EMPIRE_API_BASE`` unset and keeps calling
``http://localhost:8000``. The AMP edition sets the variable to its own
process (``http://127.0.0.1:8011``) so internal calls never hit Workroom.

The default string lives only in this module.
"""
from __future__ import annotations

import os
from pathlib import Path

WORKROOM_API_BASE = "http://localhost:8000"
WORKROOM_LOCK_PATH = Path("/tmp/empire_primary_worker.lock")


def empire_api_base() -> str:
    """Origin of this process's HTTP API, without a trailing slash."""
    raw = os.getenv("EMPIRE_API_BASE", WORKROOM_API_BASE).strip()
    if not raw:
        raw = WORKROOM_API_BASE
    raw = raw.rstrip("/")
    if raw.endswith("/api/v1"):
        raw = raw[: -len("/api/v1")]
    return raw


def empire_api_v1() -> str:
    return empire_api_base() + "/api/v1"


def empire_api_url(path: str = "") -> str:
    """Join a path onto this instance's origin. Absolute URLs pass through."""
    if not path:
        return empire_api_base()
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return empire_api_base() + path


def empire_api_netloc() -> str:
    """Host:port of this instance, for catalogs that record a listen address."""
    from urllib.parse import urlparse

    parsed = urlparse(empire_api_base())
    if parsed.netloc:
        return parsed.netloc
    return urlparse(WORKROOM_API_BASE).netloc


class API_V1:
    """Lazy ``/api/v1`` prefix for f-strings. Resolves ``EMPIRE_API_BASE`` on use.

    Not a ``str`` subclass: httpx treats those as already-resolved URLs.
    Use inside f-strings (``f"{API_V1}/health"``) or call ``empire_api_url``.
    """

    def __str__(self) -> str:
        return empire_api_v1()

    def __format__(self, spec: str) -> str:
        return format(str(self), spec)

    def __add__(self, other: str) -> str:
        return str(self) + other

    def __radd__(self, other: str) -> str:
        return other + str(self)


def primary_worker_lock_path() -> Path:
    """Scheduler singleton lock.

    Workroom (no ``EMPIRE_DATA_DIR`` and no ``EMPIRE_WORKER_LOCK``) keeps
    ``/tmp/empire_primary_worker.lock``. AMP sets ``EMPIRE_DATA_DIR`` so the
    lock lives under that root and the two processes do not share ``/tmp``.
    """
    explicit = os.getenv("EMPIRE_WORKER_LOCK", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    data = os.getenv("EMPIRE_DATA_DIR", "").strip()
    if data:
        return Path(data).expanduser() / "run" / "empire_primary_worker.lock"
    return WORKROOM_LOCK_PATH
