"""3D job viewer — fixture jobs, draft preview, founder-tap publish (mock git)."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "job_viewer"
FORBIDDEN = (
    "Acme Textiles",
    "SecretBrand",
    "AT-COG-003",
    "Northside Supply",
    "HiddenMill",
    "88 Hidden Lane",
    "12 Client Street",
    "400 Oak Avenue",
    "9 Mill Road",
    "$18400",
    "$18,400",
    "unit_price",
    "supplier_sku",
)


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def fabric_csv(monkeypatch):
    path = FIXTURE_DIR / "fabrics.csv"
    monkeypatch.setenv("EMPIRE_FABRIC_CODES_CSV", str(path))
    return path


@pytest.fixture
def mock_pages(monkeypatch):
    from app.services.job_viewer import publisher as pub

    pages = pub.MemoryPagesPublisher(base_url="https://viewer.test")
    pub.set_publisher(pages)
    monkeypatch.setenv("JOB_VIEWER_DISABLE_PUBLISH", "")
    yield pages
    pub.set_publisher(None)


@pytest.fixture
def founder_pin(monkeypatch):
    pin = "2468"
    monkeypatch.setenv("FOUNDER_APPROVAL_PIN", pin)
    import app.services.max.access_control as ac
    import app.services.job_viewer.service as svc

    monkeypatch.setattr(ac, "FOUNDER_APPROVAL_PIN", pin)
    monkeypatch.setattr(svc, "FOUNDER_APPROVAL_PIN", pin)
    return pin


def test_fractions_never_decimals():
    from app.services.job_viewer.fractions import inches_label

    assert inches_label(26.75) == '26 3/4"'
    assert inches_label(18) == '18"'
    assert inches_label(0.5) == '1/2"'
    assert "." not in inches_label(26.75)
    assert "." not in inches_label(34.5)


def test_preview_from_banquette_fixture_is_draft_and_private(fabric_csv):
    from app.services.job_viewer.service import preview_from_payload

    job = _load_fixture("banquettes.json")
    result = preview_from_payload(job, draft=True, source_kind="job")
    html = result["html"]
    assert result["draft"] is True
    assert "EMPIRE WORKROOM" in html
    assert "DRAFT" in html
    assert "function fr(" in html
    assert "26 3/4" in html
    assert "V003-Cognac" in html
    assert "RESET ALL" in html
    assert "id=\"ex\"" in html
    assert "dblclick" in html
    assert "locked" in html
    for token in FORBIDDEN:
        assert token not in html, token
    scene = result["scene"]
    assert any(p["l"] == "base" and p.get("locked") for p in scene["parts"])
    assert any(p.get("pillow") for p in scene["parts"])
    assert any(p["l"] == "seat_fabric" for p in scene["parts"])
    # U + L runs in one dining group
    assert len(scene["runs"]) >= 4
    assert any(p["g"] == "Dining" for p in scene["parts"])


def test_bench_furniture_woodwork_fixtures(fabric_csv):
    from app.services.job_viewer.service import preview_from_payload

    for name, expect_layer in (
        ("bench.json", "seat_fabric"),
        ("furniture.json", "back_fabric"),
        ("woodwork.json", "base"),
    ):
        result = preview_from_payload(_load_fixture(name), draft=True)
        html = result["html"]
        assert "EMPIRE WORKROOM" in html
        assert expect_layer in json.dumps(result["scene"]["parts"])
        for token in FORBIDDEN:
            assert token not in html, f"{name} leaked {token}"
        # Woodwork has no fabric layers
        if name == "woodwork.json":
            layers = {p["l"] for p in result["scene"]["parts"]}
            assert "seat_fabric" not in layers
            assert all(p.get("locked") for p in result["scene"]["parts"])


def test_preview_does_not_touch_publisher(fabric_csv, mock_pages):
    from app.services.job_viewer.service import preview_from_payload

    preview_from_payload(_load_fixture("banquettes.json"), draft=True)
    assert mock_pages.log == []
    assert mock_pages.files == {}


def _insert_job(jobs_unified, payload: dict) -> str:
    from app.db.database import get_db

    with get_db() as conn:
        conn.execute(
            "INSERT INTO customers (id, name, email, address) VALUES (?,?,?,?)",
            ("cust-viewer", "Fixture Client", "fix@example.com", "88 Hidden Lane"),
        )
    created = jobs_unified.create_job(
        jobs_unified.JobCreateSchema(
            title=payload["title"],
            customer_id="cust-viewer",
            client_name="Fixture Client",
            client_address=payload.get("client_address"),
            business_unit=payload.get("business_unit") or "workroom",
            description=payload.get("description"),
        )
    )
    job_id = created["job"]["id"]
    for item in payload.get("items") or []:
        jobs_unified.add_job_item(
            job_id,
            jobs_unified.ItemCreate(
                item_key=item.get("item_key"),
                item_type=item.get("item_type"),
                route_to=item.get("route_to"),
                room=item.get("room"),
                name=item["name"],
                measurements={
                    **(item.get("measurements") or {}),
                    **({"cut_list": item["cut_list"]} if item.get("cut_list") else {}),
                    **({"fabric_code": item["fabric_code"]} if item.get("fabric_code") else {}),
                },
            ),
        )
    return job_id


@pytest.fixture
def job_id(monkeypatch, tmp_path, fabric_csv):
    from app.db import database, init_db
    from app.routers import jobs_unified

    importlib.reload(database)
    importlib.reload(init_db)
    init_db.init_database()
    importlib.reload(jobs_unified)
    jobs_unified.init_schema()
    return _insert_job(jobs_unified, _load_fixture("banquettes.json"))


def test_http_preview_publish_republish_unpublish(job_id, founder_pin, mock_pages, fabric_csv):
    from app.routers.job_viewer import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    status = client.get(f"/api/v1/jobs/{job_id}/viewer")
    assert status.status_code == 200
    assert status.json()["published"] is False

    preview = client.post(f"/api/v1/jobs/{job_id}/viewer/preview")
    assert preview.status_code == 200
    body = preview.json()
    assert body["draft"] is True
    assert body["auto_published"] is False
    assert "EMPIRE WORKROOM" in body["html"]
    assert mock_pages.log == []

    denied = client.post(
        f"/api/v1/jobs/{job_id}/viewer/publish",
        json={"founder_pin": "wrong"},
    )
    assert denied.status_code == 403
    assert mock_pages.log == []

    published = client.post(
        f"/api/v1/jobs/{job_id}/viewer/publish",
        json={"founder_pin": founder_pin},
    )
    assert published.status_code == 200
    first = published.json()
    assert first["published"] is True
    slug = first["slug"]
    assert slug and len(slug) >= 6
    assert first["url"] == f"https://viewer.test/{slug}/"
    assert f"{slug}/index.html" in mock_pages.files
    assert "DRAFT" not in mock_pages.files[f"{slug}/index.html"]
    assert "EMPIRE WORKROOM" in mock_pages.files[f"{slug}/index.html"]

    again = client.post(
        f"/api/v1/jobs/{job_id}/viewer/publish",
        json={"founder_pin": founder_pin},
    )
    assert again.status_code == 200
    assert again.json()["slug"] == slug
    assert mock_pages.log.count(("publish", slug)) == 2

    gone = client.post(
        f"/api/v1/jobs/{job_id}/viewer/unpublish",
        json={"founder_pin": founder_pin},
    )
    assert gone.status_code == 200
    assert gone.json()["published"] is False
    assert f"{slug}/index.html" not in mock_pages.files


def test_quote_preview_from_rooms(fabric_csv):
    from app.services.job_viewer.service import preview_from_payload

    quote = {
        "id": "quote-fixture-1",
        "quote_number": "EST-2099-0001",
        "project_name": "Dining banquettes",
        "customer_address": "88 Hidden Lane",
        "total": 9999,
        "rooms": [
            {
                "name": "Dining",
                "items": [
                    {
                        "id": "item-u",
                        "type": "u_banquette",
                        "name": "U booth",
                        "dimensions": {"A": 80, "B": 36, "C": 36, "depth": 22, "height": 18},
                        "fabric_code": "V003-Cognac",
                    }
                ],
            }
        ],
    }
    result = preview_from_payload(quote, draft=True, source_kind="quote")
    assert "EMPIRE WORKROOM" in result["html"]
    assert "88 Hidden Lane" not in result["html"]
    assert "$9999" not in result["html"]
    assert any(p["g"] for p in result["scene"]["parts"])


def test_git_publisher_is_not_used_when_memory_injected(mock_pages):
    from app.services.job_viewer.publisher import GitPagesPublisher, get_publisher

    assert not isinstance(get_publisher(), GitPagesPublisher)
    get_publisher().publish("abc12345", "<html>ok</html>")
    assert "abc12345/index.html" in mock_pages.files


def test_runtime_uses_plain_fractions_and_locks_bases():
    runtime = (
        Path(__file__).resolve().parents[1]
        / "app" / "services" / "job_viewer" / "static" / "viewer_runtime.js"
    ).read_text(encoding="utf-8")
    assert "f + '/' + d + '\"'" in runtime or "f+'/'+d+'\"'" in runtime.replace(" ", "")
    assert "toFixed" not in runtime
    assert "l === 'base'" in runtime or "l=='base'" in runtime
    assert "dblclick" in runtime
