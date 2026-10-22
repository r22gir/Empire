"""Fabric code registry: sequential V/F/L codes, never reused, CSV import, client vs internal."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.services.fabric_codes import (
    CSV_HEADER,
    DEFAULT_CSV,
    FabricCodeError,
    assign_code,
    client_view,
    format_client_material,
    highest_sequence,
    import_csv,
    internal_view,
    next_sequence,
    retire_code,
    validate_csv_header,
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_csv_header_matches_fabric_codes_file():
    text = DEFAULT_CSV.read_text(encoding="utf-8")
    header = text.splitlines()[0].split(",")
    validate_csv_header(header)
    assert header == CSV_HEADER


def test_import_reserves_v001_through_v008_then_assigns_v009():
    conn = _conn()
    result = import_csv(conn, path=DEFAULT_CSV)
    assert result["errors"] == []
    assert result["inserted"] == 8
    assert result["highest"]["V"] == 8
    assert next_sequence(conn, "V") == 9

    row = assign_code(
        conn,
        color="Cognac",
        material_type="vinyl",
        specs="marine-grade vinyl",
        brand="HiddenBrand",
        supplier="HiddenSupplier",
        supplier_sku="HS-99",
    )
    assert row["code"] == "V009-Cognac"
    assert row["sequence"] == 9
    assert row["supplier"] == "HiddenSupplier"

    client = client_view(row)
    assert client["code"] == "V009-Cognac"
    assert client["color"] == "Cognac"
    assert client["specs"] == "marine-grade vinyl"
    assert "brand" not in client
    assert "supplier" not in client
    assert "supplier_sku" not in client
    assert "HiddenBrand" not in str(client)
    assert "HiddenSupplier" not in str(client)

    line = format_client_material(row)
    assert "V009-Cognac" in line
    assert "Cognac" in line
    assert "HiddenBrand" not in line
    assert "HiddenSupplier" not in line


def test_codes_are_never_reused_after_retire():
    conn = _conn()
    import_csv(conn, path=DEFAULT_CSV)
    first = assign_code(conn, color="Navy", material_type="fabric")
    assert first["code"] == "F001-Navy"
    retire_code(conn, "F001-Navy")
    second = assign_code(conn, color="Ivory", material_type="fabric")
    assert second["code"] == "F002-Ivory"
    assert highest_sequence(conn, "F") == 2
    with pytest.raises(sqlite3.IntegrityError):
        # sequence 1 stays consumed even if someone tries to re-insert
        conn.execute(
            "INSERT INTO fabric_code_registry (code, prefix, sequence, color, material_type, retired, created_at) "
            "VALUES ('F001-Reuse', 'F', 1, 'Reuse', 'fabric', 0, 'now')"
        )


def test_soft_gold_stays_camel_case_like_sprint_m():
    conn = _conn()
    import_csv(conn, path=DEFAULT_CSV)
    row = assign_code(conn, color="Soft Gold", material_type="vinyl")
    assert row["code"] == "V009-SoftGold"
    again = assign_code(conn, color="SoftGold", material_type="fabric")
    assert again["code"] == "F001-SoftGold"


def test_leather_and_vinyl_prefixes_are_independent():
    conn = _conn()
    import_csv(conn, path=DEFAULT_CSV)
    leather = assign_code(conn, color="Cognac", material_type="leather")
    vinyl = assign_code(conn, color="Cognac", material_type="vinyl")
    assert leather["code"] == "L001-Cognac"
    assert vinyl["code"] == "V009-Cognac"


def test_import_skips_existing_codes_does_not_overwrite():
    conn = _conn()
    import_csv(conn, path=DEFAULT_CSV)
    again = import_csv(conn, path=DEFAULT_CSV)
    assert again["inserted"] == 0
    assert again["skipped"] == 8
    assert highest_sequence(conn, "V") == 8


def test_import_rejects_wrong_header():
    conn = _conn()
    with pytest.raises(FabricCodeError, match="header"):
        import_csv(conn, csv_text="sku,name\nV001,x\n")


def test_blank_code_row_allocates_after_highest_existing():
    conn = _conn()
    import_csv(conn, path=DEFAULT_CSV)
    extra = (
        ",".join(CSV_HEADER)
        + "\n"
        + ",Sand,vinyl,54,0,0,,54in vinyl,,,,new incoming\n"
    )
    result = import_csv(conn, csv_text=extra)
    # First 8 already present → skipped; blank-code row allocates V009-Sand
    assert result["inserted"] == 1
    assert result["highest"]["V"] == 9
    row = conn.execute(
        "SELECT code, color FROM fabric_code_registry WHERE sequence = 9 AND prefix = 'V'"
    ).fetchone()
    assert row["code"] == "V009-Sand"
    assert row["color"] == "Sand"


def test_quote_pdf_line_never_shows_supplier():
    from app.services.fabric_codes import client_fabric_line
    line = client_fabric_line({
        "fabric_code": "V008-Cognac",
        "fabric_color": "Cognac",
        "fabric_specs": "54in marine vinyl",
        "brand": "Kravet",
        "supplier": "Secret Mill",
        "fabric_name": "Kravet Cognac from Secret Mill",
    })
    assert "V008-Cognac" in line
    assert "Cognac" in line
    assert "Kravet" not in line
    assert "Secret Mill" not in line


def test_internal_view_keeps_supplier():
    row = {
        "code": "V008-Cognac",
        "color": "Cognac",
        "material_type": "vinyl",
        "specs": "54in",
        "brand": "BrandX",
        "supplier": "SupplierY",
        "supplier_sku": "SKU-1",
        "width_inches": 54,
    }
    internal = internal_view(row)
    assert internal["supplier"] == "SupplierY"
    assert internal["brand"] == "BrandX"
    client = client_view(row)
    assert "supplier" not in client
    assert "brand" not in client
