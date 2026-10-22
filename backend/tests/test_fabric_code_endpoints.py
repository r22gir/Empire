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
    assert codes[:8] == [
        "V001-Raven", "V002-Cherrywood", "V003-Cognac",
        "V004-Cognac", "V005-Copper", "V006-Bourbon", "V007-Tannery",
        "V008-Bittersweet",
    ]
    blob = str(rows)
    assert "brand" not in blob
    assert "supplier" not in blob
    assert "supplier_sku" not in blob


def test_list_codes_does_not_write_live_db(tmp_path, monkeypatch):
    live = tmp_path / "live-empire.db"
    live.write_bytes(b"")
    monkeypatch.setattr("app.db.database.DB_PATH", str(live))
    before = live.read_bytes()
    rows = asyncio.run(list_fabric_codes(internal=False))
    assert rows
    assert live.read_bytes() == before
    assert live.stat().st_size == 0


def test_assign_starts_at_next_after_csv_on_isolated_db(tmp_path, monkeypatch):
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
    assert row["code"] == "V009-Cognac"
    assert row["sequence"] == 9
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    assert next_sequence(conn, "V") == 10
    conn.close()


def test_import_endpoint_skips_existing(tmp_path, monkeypatch):
    db = tmp_path / "registry.db"
    monkeypatch.setattr("app.db.database.DB_PATH", str(db))
    csv_text = Path(DEFAULT_CSV).read_text(encoding="utf-8")
    first = asyncio.run(import_fabric_codes(_Upload(csv_text)))
    again = asyncio.run(import_fabric_codes(_Upload(csv_text)))
    assert first["inserted"] == 8
    assert again["inserted"] == 0
    assert again["skipped"] == 8
    assert again["highest"]["V"] == 8
