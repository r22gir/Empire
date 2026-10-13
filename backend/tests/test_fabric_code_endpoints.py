"""Fabric-code HTTP handlers: sequential V008, no invented codes, GET is read-only."""
from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from app.routers.fabrics import (
    FabricCodeAssign,
    assign_fabric_code,
    fabric_code_catalog,
    import_fabric_codes,
    list_fabric_codes,
)
from app.services.fabric_codes import DEFAULT_CSV, next_sequence


class _Upload:
    def __init__(self, text: str):
        self._text = text.encode("utf-8")

    async def read(self):
        return self._text


def test_catalog_lists_reserved_codes_and_hides_supplier():
    rows = asyncio.run(fabric_code_catalog())
    codes = [r["code"] for r in rows]
    assert codes[:7] == [
        "V001-Assigned", "V002-Assigned", "V003-Assigned",
        "V004-Assigned", "V005-Assigned", "V006-Assigned", "V007-Assigned",
    ]
    blob = str(rows)
    assert "brand" not in blob
    assert "supplier" not in blob
    assert "supplier_sku" not in blob


def test_list_codes_does_not_write_live_db(tmp_path, monkeypatch):
    live = tmp_path / "live-empire.db"
    live.touch()
    monkeypatch.setattr("app.db.database.DB_PATH", str(live))
    before = live.stat().st_mtime_ns
    rows = asyncio.run(list_fabric_codes(internal=False))
    after = live.stat().st_mtime_ns
    assert rows
    assert before == after
    conn = sqlite3.connect(live)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "fabric_code_registry" not in tables


def test_assign_starts_at_v008_on_isolated_db(tmp_path, monkeypatch):
    db = tmp_path / "registry.db"
    monkeypatch.setattr("app.db.database.DB_PATH", str(db))
    row = asyncio.run(assign_fabric_code(FabricCodeAssign(
        color="Cognac",
        material_type="vinyl",
        specs="marine-grade vinyl",
        brand="HiddenBrand",
        supplier="HiddenSupplier",
        supplier_sku="HS-99",
    )))
    assert row["code"] == "V008-Cognac"
    assert row["sequence"] == 8
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    assert next_sequence(conn, "V") == 9
    conn.close()


def test_import_endpoint_skips_existing(tmp_path, monkeypatch):
    db = tmp_path / "registry.db"
    monkeypatch.setattr("app.db.database.DB_PATH", str(db))
    csv_text = Path(DEFAULT_CSV).read_text(encoding="utf-8")
    first = asyncio.run(import_fabric_codes(_Upload(csv_text)))
    again = asyncio.run(import_fabric_codes(_Upload(csv_text)))
    assert first["inserted"] == 7
    assert again["inserted"] == 0
    assert again["skipped"] == 7
    assert again["highest"]["V"] == 7
