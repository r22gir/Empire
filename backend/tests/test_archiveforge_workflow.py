import json
import uuid
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app
from app.routers import archiveforge


client = TestClient(app)

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff"
    b"\x1f\x00\x03\x03\x02\x00\xef\x97\xda*\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def created_archives():
    ids: list[int] = []
    yield ids
    for archive_id in reversed(ids):
        client.delete(f"/api/v1/archiveforge/archives/{archive_id}")


def _create_archive(created_archives: list[int], **overrides) -> int:
    payload = {
        "reference_issue_id": "google-books-IE8EAAAAMBAJ",
        "reference_source": "google_books",
        "issue_date": "1969-07-25",
        "volume": 67,
        "issue_number": 4,
        "cover_subject": f"ArchiveForge test issue {uuid.uuid4().hex[:8]}",
        "source_box_code": "AF-TST-SRC",
        "processed_box_code": "AF-TST-DST",
        "processed_status": "RAW",
        "archive_location": "qa shelf",
        "tier": "A",
        "marketforge_category_id": "",
        "marketforge_ships_from_zip": "",
    }
    payload.update(overrides)
    res = client.post("/api/v1/archiveforge/archives", json=payload)
    assert res.status_code == 201, res.text
    archive_id = res.json()["id"]
    created_archives.append(archive_id)
    return archive_id


def _transition_to_ready(archive_id: int) -> None:
    for status in ("IDENTIFIED", "PHOTOGRAPHED", "VALUED", "READY_TO_LIST"):
        res = client.patch(
            f"/api/v1/archiveforge/archives/{archive_id}/status",
            json={"status": status},
        )
        assert res.status_code == 200, res.text


def _save_draft(archive_id: int, title: str = "AF draft title", desc: str = "AF draft description") -> None:
    res = client.post(
        f"/api/v1/archiveforge/archives/{archive_id}/save-draft",
        json={"listing_title": title, "listing_description": desc, "batch_tag": "AF-TST"},
    )
    assert res.status_code == 200, res.text


def _upload_photo(archive_id: int) -> dict:
    res = client.post(
        f"/api/v1/archiveforge/uploads/{archive_id}",
        data={"role": "front"},
        files={"file": ("tiny.png", PNG_BYTES, "image/png")},
    )
    assert res.status_code == 201, res.text
    return res.json()


def _prepare_publishable_archive(
    created_archives: list[int],
    *,
    category_id: str = "11111111-1111-1111-1111-111111111111",
    ships_from_zip: str = "98101",
) -> int:
    archive_id = _create_archive(
        created_archives,
        marketforge_category_id=category_id,
        marketforge_ships_from_zip=ships_from_zip,
    )
    _save_draft(archive_id)
    _transition_to_ready(archive_id)
    _upload_photo(archive_id)
    return archive_id


def test_create_archive_item(created_archives):
    archive_id = _create_archive(created_archives)
    assert isinstance(archive_id, int)


def test_list_archive_items_includes_created_item(created_archives):
    archive_id = _create_archive(created_archives)
    res = client.get("/api/v1/archiveforge/archives?limit=20")
    assert res.status_code == 200, res.text
    body = res.json()
    ids = {item["id"] for item in body["items"]}
    assert archive_id in ids


def test_get_archive_detail(created_archives):
    archive_id = _create_archive(created_archives)
    res = client.get(f"/api/v1/archiveforge/archives/{archive_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["id"] == archive_id
    assert body["cover_subject"].startswith("ArchiveForge test issue")


def test_update_metadata_and_status_transition(created_archives):
    archive_id = _create_archive(created_archives)
    update = client.patch(
        f"/api/v1/archiveforge/archives/{archive_id}",
        json={
            "notes": "metadata updated",
            "marketforge_category_id": "22222222-2222-2222-2222-222222222222",
            "marketforge_ships_from_zip": "10001",
        },
    )
    assert update.status_code == 200, update.text

    status = client.patch(
        f"/api/v1/archiveforge/archives/{archive_id}/status",
        json={"status": "IDENTIFIED"},
    )
    assert status.status_code == 200, status.text
    assert status.json()["processed_status"] == "IDENTIFIED"

    detail = client.get(f"/api/v1/archiveforge/archives/{archive_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["notes"] == "metadata updated"
    assert body["marketforge_category_id"] == "22222222-2222-2222-2222-222222222222"
    assert body["marketforge_ships_from_zip"] == "10001"


def test_delete_archive_safely_removes_children_and_files(created_archives):
    archive_id = _create_archive(created_archives)
    _save_draft(archive_id)
    listing_res = client.post(
        f"/api/v1/archiveforge/archives/{archive_id}/listing-draft",
        json={
            "listing_title": "Delete test draft title",
            "description": "Delete test draft description",
            "item_specifics": {},
            "batch_tag": "AF-DEL",
        },
    )
    assert listing_res.status_code == 200, listing_res.text
    photo = _upload_photo(archive_id)

    photos = client.get(f"/api/v1/archiveforge/uploads/{archive_id}")
    assert photos.status_code == 200, photos.text
    assert photos.json()["total"] == 1
    file_path = Path(photos.json()["photos"][0]["file_path"])
    assert file_path.exists()

    with get_db() as db:
        draft_count = db.execute(
            "SELECT COUNT(*) FROM ag_listing_drafts WHERE archive_id = ?",
            (archive_id,),
        ).fetchone()[0]
        photo_count = db.execute(
            "SELECT COUNT(*) FROM ag_archive_photos WHERE archive_id = ?",
            (archive_id,),
        ).fetchone()[0]
    assert draft_count >= 1
    assert photo_count == 1

    deleted = client.delete(f"/api/v1/archiveforge/archives/{archive_id}")
    assert deleted.status_code == 200, deleted.text
    created_archives.remove(archive_id)

    detail = client.get(f"/api/v1/archiveforge/archives/{archive_id}")
    assert detail.status_code == 404
    assert not file_path.exists()
    with get_db() as db:
        draft_count_after = db.execute(
            "SELECT COUNT(*) FROM ag_listing_drafts WHERE archive_id = ?",
            (archive_id,),
        ).fetchone()[0]
        photo_count_after = db.execute(
            "SELECT COUNT(*) FROM ag_archive_photos WHERE archive_id = ?",
            (archive_id,),
        ).fetchone()[0]
    assert draft_count_after == 0
    assert photo_count_after == 0
    assert photo["archive_id"] == archive_id


def test_generate_listing_draft(created_archives):
    archive_id = _create_archive(created_archives)
    res = client.post(
        f"/api/v1/archiveforge/archives/{archive_id}/listing-draft",
        json={
            "listing_title": "Generated draft title",
            "description": "Generated draft description",
            "item_specifics": {},
            "batch_tag": "AF-GEN",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "draft"
    assert body["draft_id"] > 0
    assert body["listing_title"] == "Generated draft title"


def test_save_listing_draft(created_archives):
    archive_id = _create_archive(created_archives)
    _save_draft(archive_id, title="Saved draft title", desc="Saved draft description")
    detail = client.get(f"/api/v1/archiveforge/archives/{archive_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["listing_title"] == "Saved draft title"
    assert body["listing_description"] == "Saved draft description"
    assert body["marketforge_push_status"] == "draft_saved"


def test_publish_status_returns_readiness_fields(created_archives):
    archive_id = _create_archive(created_archives)
    res = client.get(f"/api/v1/archiveforge/publish-status?archive_id={archive_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["approval_required"] is True
    assert body["publish_mode"] == "internal_staged_only"
    assert "marketforge_category_id" in body["required_marketforge_fields"]
    assert "marketforge_ships_from_zip" in body["required_marketforge_fields"]
    assert body["archive_id"] == archive_id
    assert body["publish_ready"] is False


def test_publish_blocked_when_required_marketforge_fields_missing(created_archives):
    archive_id = _create_archive(created_archives)
    _save_draft(archive_id)
    _transition_to_ready(archive_id)
    _upload_photo(archive_id)

    res = client.post(f"/api/v1/archiveforge/push/{archive_id}?approval_confirmed=true")
    assert res.status_code == 409, res.text
    assert "missing fields" in res.json()["detail"].lower()
    assert "marketforge_category_id" in res.json()["detail"]
    assert "marketforge_ships_from_zip" in res.json()["detail"]

    detail = client.get(f"/api/v1/archiveforge/archives/{archive_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["marketforge_push_status"] == "blocked_missing_marketforge_fields"


def test_publish_requires_explicit_approval_flag(created_archives):
    archive_id = _prepare_publishable_archive(created_archives)
    res = client.post(f"/api/v1/archiveforge/push/{archive_id}")
    assert res.status_code == 400, res.text
    assert "explicit approval is required" in res.json()["detail"].lower()


def test_publish_status_blocks_external_target_by_default(monkeypatch):
    monkeypatch.setattr(
        archiveforge,
        "MARKETFORGE_PRODUCTS_URL",
        "https://example.com/marketplace/products",
    )

    class ShouldNotCallAsyncClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("AsyncClient should not be called for blocked external targets")

    monkeypatch.setattr(archiveforge.httpx, "AsyncClient", ShouldNotCallAsyncClient)
    res = client.get("/api/v1/archiveforge/publish-status")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["publish_available"] is False
    assert "external marketforge target is blocked" in body["reason"].lower()


def test_publish_blocks_external_target_without_network_calls(monkeypatch, created_archives):
    archive_id = _prepare_publishable_archive(created_archives)
    monkeypatch.setattr(
        archiveforge,
        "MARKETFORGE_PRODUCTS_URL",
        "https://example.com/marketplace/products",
    )

    class ShouldNotCallAsyncClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("AsyncClient should not be called for blocked external publish targets")

    monkeypatch.setattr(archiveforge.httpx, "AsyncClient", ShouldNotCallAsyncClient)
    res = client.post(f"/api/v1/archiveforge/push/{archive_id}?approval_confirmed=true")
    assert res.status_code == 503, res.text
    assert "external marketforge target is blocked" in res.json()["detail"].lower()


def test_successful_publish_writes_to_internal_target_when_configured(monkeypatch, created_archives):
    archive_id = _prepare_publishable_archive(created_archives)
    internal_target = "http://localhost:8000/marketplace/products"
    monkeypatch.setattr(archiveforge, "MARKETFORGE_PRODUCTS_URL", internal_target)

    called: dict = {}

    class FakeResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload
            self.text = json.dumps(payload)

        def json(self):
            return self._payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, *args, **kwargs):
            called["get_url"] = url
            return FakeResponse(200, {"ok": True})

        async def post(self, url, json=None, *args, **kwargs):
            called["post_url"] = url
            called["payload"] = json or {}
            return FakeResponse(201, {"id": "mf_internal_test_123"})

    monkeypatch.setattr(archiveforge.httpx, "AsyncClient", FakeAsyncClient)

    res = client.post(f"/api/v1/archiveforge/push/{archive_id}?approval_confirmed=true")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["push_status"] == "pushed"
    assert body["marketforge_listing_id"] == "mf_internal_test_123"

    assert called["get_url"] == internal_target
    assert called["post_url"] == internal_target
    assert urlparse(called["post_url"]).hostname in {"localhost", "127.0.0.1", "::1"}
    assert called["payload"]["category_id"] == "11111111-1111-1111-1111-111111111111"
    assert called["payload"]["ships_from_zip"] == "98101"

    detail = client.get(f"/api/v1/archiveforge/archives/{archive_id}")
    assert detail.status_code == 200, detail.text
    record = detail.json()
    assert record["listing_status"] == "pushed"
    assert record["marketforge_listing_id"] == "mf_internal_test_123"
