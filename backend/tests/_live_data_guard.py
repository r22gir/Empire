"""Refuse live Empire data paths and live Meta Graph calls in tests.

WhatsApp chat-log tests import this module so a mis-aimed env cannot
write Rafael's edition data or hit Facebook.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

PROD_PATH_MARKERS = (
    "empire-data/empire.db",
    "empire-data\\empire.db",
    "/empire-data/empire.db",
    "empire-repo/backend/data",
    "empire-repo\\backend\\data",
)

LIVE_GRAPH_MARKERS = (
    "graph.facebook.com",
    "lookaside.fbsbx.com",
    "graph.instagram.com",
)


def _looks_like_prod(value: str) -> bool:
    lowered = (value or "").replace("\\", "/")
    return any(marker.replace("\\", "/") in lowered for marker in PROD_PATH_MARKERS)


def assert_isolated_env() -> None:
    """Fail loudly if this process is pointed at live data or live Graph."""
    for name in ("EMPIRE_TASK_DB", "EMPIRE_DB_PATH", "EMPIRE_DATA_DIR"):
        value = os.getenv(name) or ""
        if _looks_like_prod(value):
            raise RuntimeError(f"{name} points at live data: {value}")
    data_dir = os.getenv("EMPIRE_DATA_DIR") or ""
    if data_dir:
        path = Path(data_dir)
        if path.exists() and path.resolve() == (Path.home() / "empire-repo" / "backend" / "data").resolve():
            raise RuntimeError("EMPIRE_DATA_DIR resolved to the live backend/data folder")


def assert_no_live_graph(url: str) -> None:
    lowered = (url or "").lower()
    if any(host in lowered for host in LIVE_GRAPH_MARKERS):
        raise RuntimeError(f"live Meta Graph call refused in tests: {url}")


@pytest.fixture
def isolated_whatsapp_edition(tmp_path, monkeypatch):
    """Clean per-edition data dir + founder PIN. No live WhatsApp credentials."""
    root = tmp_path / "edition-data"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("FOUNDER_PIN", "test-founder-pin")
    for name in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
    ):
        monkeypatch.delenv(name, raising=False)
    assert_isolated_env()
    return root
