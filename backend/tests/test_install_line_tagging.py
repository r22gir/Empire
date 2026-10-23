"""Install-line tagging, LF parse, and quote/invoice save hooks."""
from __future__ import annotations

import json

from app.services.install_line_tagging import (
    dumps_line_items,
    format_feet,
    is_install_line,
    parse_lf,
    parse_windows,
    tag_install_line,
    tag_invoice_lines,
)


def test_detects_install_phrases():
    assert is_install_line("Install drapery")
    assert is_install_line("Removal and installation of existing track")
    assert is_install_line("Remove existing track and install new ripplefold")
    assert is_install_line("Hourly install — 3 hours")
    assert is_install_line("Reinstall hardware after paint")
    assert is_install_line("roman shade", item_type="installation")
    assert is_install_line("labor", category="installation")
    assert not is_install_line("Roman shade fabric — living room")
    assert not is_install_line("Blackout lining")


def test_parse_lf_from_width_inches_and_wall_phrase():
    # 160" wall → 13 1/3 ft
    lf = parse_lf('Install ripplefold — 160" wall')
    assert lf is not None
    assert abs(lf - (160 / 12)) < 1e-9
    assert format_feet(lf) == "13 1/3 ft"
    assert parse_lf(width=160) == 160 / 12
    assert parse_lf("12 lf install") == 12
    assert parse_lf("8 linear feet of track") == 8
    assert parse_lf("Install only") is None


def test_parse_windows_from_description_and_unit():
    assert parse_windows("Install 3 windows living room") == 3
    assert parse_windows("windows: 2 hourly install") == 2
    assert parse_windows("Install drapery", quantity=4, unit="windows") == 4
    assert parse_windows("Install drapery", quantity=4, unit="ea") is None
    assert parse_windows("Install drapery", explicit=6) == 6


def test_tag_install_line_sets_item_type_windows_lf():
    tags = tag_install_line({
        "description": 'Removal and installation — 10 windows — 160" wall',
        "unit_price": 1450,
    })
    assert tags["is_install"] is True
    assert tags["item_type"] == "installation"
    assert tags["windows"] == 10
    assert abs(tags["lf"] - (160 / 12)) < 1e-9


def test_create_quote_tags_install_line(isolated_empire_db):
    from app.services.quote_service import create_quote, get_quote

    quote = create_quote({
        "customer_name": "Willard Mock",
        "project_name": "Willard Est 838",
        "issued_document": "838",
        "line_items": [
            {
                "category": "manual_line",
                "description": 'Install 10 windows — 160" wall',
                "unit_price": 1450,
                "quantity": 1,
            },
            {
                "category": "manual_line",
                "description": "Roman shade fabric living room",
                "unit_price": 590,
                "quantity": 1,
            },
        ],
    })
    items = quote["line_items"]
    install = next(i for i in items if "Install" in (i.get("description") or ""))
    fabric = next(i for i in items if "fabric" in (i.get("description") or ""))
    assert install["item_type"] == "installation"
    assert install["windows"] == 10
    assert abs(float(install["lf"]) - (160 / 12)) < 1e-9
    assert fabric["item_type"] != "installation"

    again = get_quote(quote["id"])
    tagged = next(i for i in again["line_items"] if i["item_type"] == "installation")
    assert tagged["windows"] == 10


def test_add_and_update_line_retag(isolated_empire_db):
    from app.services.quote_service import add_line_item, create_quote, update_line_item

    quote = create_quote({
        "customer_name": "Le Midi Mock",
        "project_name": "Le Midi",
        "line_items": [],
    })
    quote = add_line_item(quote["id"], {
        "category": "manual_line",
        "description": "Hourly install 2 windows",
        "unit_price": 400,
        "quantity": 1,
    })
    item = quote["line_items"][0]
    assert item["item_type"] == "installation"
    assert item["windows"] == 2

    quote = update_line_item(quote["id"], item["id"], {
        "description": 'Remove existing track and install — 4 windows — 96" wall',
    })
    item = quote["line_items"][0]
    assert item["item_type"] == "installation"
    assert item["windows"] == 4
    assert abs(float(item["lf"]) - 8.0) < 1e-9


def test_invoice_line_save_tags(isolated_empire_db):
    tagged = tag_invoice_lines([
        {"description": "Install 3 windows", "amount": 435},
        {"description": "Fabric only", "amount": 200},
    ])
    assert tagged[0]["item_type"] == "installation"
    assert tagged[0]["windows"] == 3
    assert tagged[1].get("item_type") != "installation"
    blob = dumps_line_items([
        {"description": "Hourly install", "total": 300, "width": 72},
    ])
    parsed = json.loads(blob)
    assert parsed[0]["item_type"] == "installation"
    assert abs(parsed[0]["lf"] - 6.0) < 1e-9
