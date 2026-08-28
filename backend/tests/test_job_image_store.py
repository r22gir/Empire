"""D44 — tests for the single-writer (job_image_store) and channel hooks.

Coverage:
  - Schema: job_documents has nullable job_id, new quote_id, source_channel.
  - Writer: store_job_image happy path + invalid-bytes rejection.
  - Buckets: job_id, quote_id, unassigned all land in the right directory.
  - Source-channel whitelist rejects unknown values.
  - Listing: list_job_documents filters and rejects no-filter calls.
  - Re-read: read_and_validate_job_image round-trips through the D43 guard.
  - Negative case: a non-image payload does NOT produce a row or a file.
  - Channel integration: each wired channel inserts a row with the right
    source_channel. Email is intentionally NOT wired — verified separately.
  - MAX tools: list_job_images and describe_job_image dispatch through
    execute_tool with the right success/failure paths.
"""
from __future__ import annotations

import io
import os
import sqlite3
import sys
from pathlib import Path

import pytest
from PIL import Image


# ── fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def d44_env(tmp_path, monkeypatch, isolated_empire_db):
    """Wire EMPIRE_DB_PATH + EMPIRE_PHOTOS_DIR to test paths so job_image_store
    never touches production. The isolated_empire_db fixture (from conftest)
    already built the unified_business_migration schema on EMPIRE_TASK_DB;
    we point EMPIRE_DB_PATH at the same file so the writer sees the same DB,
    then build the jobs_unified schema (which adds job_documents v2)."""
    monkeypatch.setenv("EMPIRE_DB_PATH", isolated_empire_db)
    monkeypatch.setenv("EMPIRE_PHOTOS_DIR", str(tmp_path / "photos"))
    (tmp_path / "photos").mkdir(parents=True, exist_ok=True)

    # Build the jobs_unified schema (creates job_documents v2) on the test DB.
    from app.routers import jobs_unified
    jobs_unified.init_schema()

    yield {
        "db_path": isolated_empire_db,
        "photos_dir": Path(os.environ["EMPIRE_PHOTOS_DIR"]),
        "tmp_path": tmp_path,
    }


def _png_bytes(width: int = 32, height: int = 32, color=(255, 128, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(buf, format="PNG")
    return buf.getvalue()


# ── schema tests ───────────────────────────────────────────────────

def test_job_documents_schema_has_nullable_job_id_and_new_columns(d44_env):
    """Per STOP 1 ruling #1: job_id nullable, quote_id + source_channel added."""
    conn = sqlite3.connect(d44_env["db_path"])
    cols = {row[1]: row for row in conn.execute("PRAGMA table_info(job_documents)").fetchall()}
    assert "job_id" in cols
    assert "quote_id" in cols
    assert "source_channel" in cols
    assert "route_to" in cols  # preserved with prior semantics
    assert cols["job_id"][3] == 0, "job_id must be nullable"
    conn.close()


def test_job_documents_has_indexes_for_new_columns(d44_env):
    conn = sqlite3.connect(d44_env["db_path"])
    idx = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='job_documents'"
        ).fetchall()
    }
    assert "idx_job_docs_quote" in idx
    assert "idx_job_docs_source" in idx
    assert "idx_job_docs_job" in idx  # pre-existing
    conn.close()


# ── writer: happy path ─────────────────────────────────────────────

def test_store_job_image_happy_path_writes_file_and_row(d44_env):
    from app.services.job_image_store import store_job_image

    row = store_job_image(
        _png_bytes(),
        source_channel="quote_ui",
        quote_id="Q-TEST-1",
        original_filename="window.png",
    )

    # Row shape.
    assert row["quote_id"] == "Q-TEST-1"
    assert row["job_id"] is None
    assert row["source_channel"] == "quote_ui"
    assert row["document_type"] == "photo"
    assert row["visible_to_client"] == 0
    assert row["revision"] == 1
    assert row["filename"].endswith(".png")
    assert row["url"].startswith("/api/v1/photos/job/quote_Q-TEST-1/")

    # File on disk.
    landed = d44_env["photos_dir"] / "job" / "quote_Q-TEST-1" / row["filename"]
    assert landed.exists()
    assert landed.stat().st_size > 0
    assert landed.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_store_job_image_with_job_id_uses_job_key(d44_env):
    from app.services.job_image_store import store_job_image, list_job_documents

    row = store_job_image(
        _png_bytes(),
        source_channel="max_chat",
        job_id="J-2026-0001",
        original_filename="kitchen.jpg",
    )
    landed = d44_env["photos_dir"] / "job" / "J-2026-0001" / row["filename"]
    assert landed.exists()
    rows = list_job_documents(job_id="J-2026-0001")
    assert len(rows) == 1 and rows[0]["id"] == row["id"]


def test_store_job_image_unassigned_bucket(d44_env):
    from app.services.job_image_store import store_job_image, list_job_documents

    row = store_job_image(
        _png_bytes(),
        source_channel="telegram",
        item_key="telegram_chat:12345",
    )
    landed = d44_env["photos_dir"] / "job" / "unassigned" / row["filename"]
    assert landed.exists()
    rows = list_job_documents(unassigned=True)
    assert len(rows) == 1 and rows[0]["item_key"] == "telegram_chat:12345"


def test_store_job_image_preserves_route_to_for_business_routing(d44_env):
    from app.services.job_image_store import store_job_image, get_job_document

    row = store_job_image(
        _png_bytes(),
        source_channel="quote_ui",
        quote_id="Q-BENCH",
        route_to="woodcraft",
    )
    fetched = get_job_document(row["id"])
    assert fetched["route_to"] == "woodcraft"


# ── writer: rejection paths ────────────────────────────────────────

def test_store_job_image_rejects_non_image_bytes(d44_env):
    from app.services.job_image_store import store_job_image

    with pytest.raises(ValueError, match="image rejected"):
        store_job_image(
            b"this is plain text, not an image",
            source_channel="max_chat",
            original_filename="readme.txt",
        )

    # No row, no file.
    conn = sqlite3.connect(d44_env["db_path"])
    n_rows = conn.execute("SELECT COUNT(*) FROM job_documents").fetchone()[0]
    assert n_rows == 0
    conn.close()
    # The photos/job dir may not even exist if no successful landing
    # happened; that's fine. If it does exist, it must be empty.
    job_dir = d44_env["photos_dir"] / "job"
    if job_dir.exists():
        for sub in job_dir.iterdir():
            assert list(sub.iterdir()) == [], f"unexpected file under {sub}"


def test_store_job_image_rejects_unknown_source_channel(d44_env):
    from app.services.job_image_store import store_job_image

    with pytest.raises(ValueError, match="unknown source_channel"):
        store_job_image(_png_bytes(), source_channel="reddit_dm")


def test_store_job_image_rejects_tiny_payload(d44_env):
    from app.services.job_image_store import store_job_image

    # 30 bytes — under the 32-byte minimum enforced by the D43 guard.
    with pytest.raises(ValueError):
        store_job_image(b"\x89PNG\r\n\x1a\n" + b"x" * 22, source_channel="max_chat")


# ── listing + read-back ────────────────────────────────────────────

def test_list_job_documents_requires_filter(d44_env):
    from app.services.job_image_store import list_job_documents, store_job_image

    store_job_image(_png_bytes(), source_channel="max_chat", quote_id="Q1")
    with pytest.raises(ValueError, match="requires job_id, quote_id, or unassigned"):
        list_job_documents()


def test_read_and_validate_job_image_round_trips(d44_env):
    from app.services.job_image_store import (
        store_job_image, get_job_document, read_and_validate_job_image,
    )

    raw = _png_bytes()
    row = store_job_image(raw, source_channel="quote_ui", quote_id="Q-RT")
    fetched = get_job_document(row["id"])
    out = read_and_validate_job_image(fetched)
    assert out == raw


def test_read_and_validate_rejects_if_file_corrupted(d44_env, tmp_path):
    from app.services.job_image_store import (
        store_job_image, get_job_document, read_and_validate_job_image,
    )

    row = store_job_image(_png_bytes(), source_channel="quote_ui", quote_id="Q-CORRUPT")
    fetched = get_job_document(row["id"])
    # Truncate the file to simulate corruption after landing.
    landed = d44_env["photos_dir"] / "job" / "quote_Q-CORRUPT" / row["filename"]
    landed.write_bytes(b"NOT A VALID PNG ANYMORE")
    with pytest.raises(ValueError):
        read_and_validate_job_image(fetched)


# ── MAX tool surface ──────────────────────────────────────────────

def test_list_job_images_tool_returns_rows(d44_env):
    from app.services.job_image_store import store_job_image
    from app.services.max.tool_executor import execute_tool

    store_job_image(_png_bytes(), source_channel="max_chat", quote_id="Q-LIST")
    r = execute_tool(
        {"tool": "list_job_images", "quote_id": "Q-LIST"},
        founder=True,
    )
    assert r.success is True
    assert r.result["count"] == 1
    assert r.result["images"][0]["quote_id"] == "Q-LIST"
    assert r.result["images"][0]["source_channel"] == "max_chat"


def test_list_job_images_tool_rejects_no_filter(d44_env):
    from app.services.max.tool_executor import execute_tool

    r = execute_tool({"tool": "list_job_images"}, founder=True)
    assert r.success is False
    assert "exactly one" in r.error


def test_describe_job_image_tool_rejects_missing_doc(d44_env):
    from app.services.max.tool_executor import execute_tool

    r = execute_tool(
        {"tool": "describe_job_image", "document_id": "deadbeef"},
        founder=True,
    )
    assert r.success is False
    assert "not found" in r.error


def test_describe_job_image_tool_reads_and_validates(d44_env):
    from app.services.job_image_store import store_job_image
    from app.services.max.tool_executor import execute_tool

    row = store_job_image(_png_bytes(), source_channel="quote_ui", quote_id="Q-DESC")
    r = execute_tool(
        {"tool": "describe_job_image", "document_id": row["id"]},
        founder=True,
    )
    # Vision may fail in CI if API keys absent — that's a known infra
    # gap (xAI key disabled, OpenAI not configured). The D44 contract is
    # that the file is re-validated BEFORE vision runs, so success of
    # the validation step is what we assert here.
    if not r.success:
        # Vision failed — but validation passed. Confirm error mentions vision.
        assert "vision failed" in r.error or "Image understanding failed" in r.error
    else:
        assert r.result["document_id"] == row["id"]
        assert r.result["source_channel"] == "quote_ui"
        assert r.result["quote_id"] == "Q-DESC"


# ── channel integration: writer insertion paths ──────────────────

def test_files_upload_writes_d44_row(d44_env):
    """Channel 1 (MAX chat web): /api/v1/files/upload inserts a job_documents row.

    Calls the route handler directly to avoid spinning up the full app
    (which triggers prod-DB module-level captures in unrelated routers).
    """
    import asyncio
    from app.api.v1.files import upload_file
    from fastapi import UploadFile

    png = _png_bytes()
    upload = UploadFile(filename="window.png", file=io.BytesIO(png))

    result = asyncio.run(upload_file(upload))
    assert result["status"] == "success"

    conn = sqlite3.connect(d44_env["db_path"])
    rows = conn.execute(
        "SELECT source_channel, document_type, quote_id, job_id, filename "
        "FROM job_documents"
    ).fetchall()
    assert len(rows) == 1, f"expected 1 D44 row, got {len(rows)}: {rows}"
    sc, dtype, qid, jid, fname = rows[0]
    assert sc == "max_chat"
    assert dtype == "photo"
    assert qid is None
    assert jid is None
    conn.close()


def test_quote_photos_upload_writes_d44_row_with_quote_id(d44_env):
    """Channel 4 (quote UI): /api/v1/photos/upload entity_type=quote keys by quote_id."""
    import asyncio
    from app.routers.photos import upload_photos
    from fastapi import UploadFile

    png = _png_bytes()
    files = [UploadFile(filename="intake-photo.jpg", file=io.BytesIO(png))]
    result = asyncio.run(upload_photos(
        entity_type="quote",
        entity_id="Q-INT-1",
        source="web",
        files=files,
    ))
    assert result["total"] == 1

    conn = sqlite3.connect(d44_env["db_path"])
    rows = conn.execute(
        "SELECT source_channel, quote_id, route_to FROM job_documents"
    ).fetchall()
    assert len(rows) == 1
    sc, qid, route = rows[0]
    assert sc == "quote_ui"
    assert qid == "Q-INT-1"
    assert route == "workroom"
    conn.close()


def test_intake_photos_upload_writes_d44_row_with_intake_key(d44_env):
    """Channel 5 (LuxeForge): exercise the same hook code path as the route.

    The route is JWT-gated and depends on a real intake_projects row. We
    verify the hook by calling store_job_image with the same args the
    intake_auth.upload_photo handler uses, then asserting the row shape.
    """
    from app.services.job_image_store import store_job_image

    png = _png_bytes()
    intake_id = "intk-d44-test"
    store_job_image(
        png,
        source_channel="luxeforge_intake",
        item_key=f"intake_project:{intake_id}",
    )

    conn = sqlite3.connect(d44_env["db_path"])
    rows = conn.execute(
        "SELECT source_channel, item_key FROM job_documents"
    ).fetchall()
    assert len(rows) == 1
    sc, ikey = rows[0]
    assert sc == "luxeforge_intake"
    assert ikey == f"intake_project:{intake_id}"
    conn.close()

    # Also verify the actual hook code is wired in the route (not just
    # reachable via direct service call). Source-inspect intake_auth.
    import inspect
    from app.routers import intake_auth
    src = inspect.getsource(intake_auth.upload_photo)
    assert "luxeforge_intake" in src
    assert "store_job_image" in src


def test_email_channel_is_not_wired(d44_env):
    """Email is intentionally NOT wired (SendGrid retired 2026-08-27).

    Verify no code path inserts a job_documents row with source_channel='email'.
    The webhooks.py handler does not store attachment bytes and does not call
    store_job_image. This test enforces the gap by checking the writer whitelist.
    """
    from app.services.job_image_store import SOURCE_CHANNELS
    # The whitelist DOES include 'email' (so future wiring can use it),
    # but no channel hook in this dispatch calls it. Verify via inspection:
    import inspect
    from app.routers import webhooks
    src = inspect.getsource(webhooks)
    assert "store_job_image" not in src, "email channel is unexpectedly wired"


# ── cross-channel smoke: 4 channels land 4 rows with distinct keys ─

def test_four_channels_produce_four_distinct_rows(d44_env):
    """End-to-end: simulate the four wired channels landing one image each,
    assert each row is findable by its source_channel and the right bucket."""
    from app.services.job_image_store import (
        store_job_image, list_job_documents,
    )

    # Channel 1: max_chat (no entity context)
    r1 = store_job_image(_png_bytes(), source_channel="max_chat")
    # Channel 2: telegram (chat_id item_key, unassigned bucket)
    r2 = store_job_image(
        _png_bytes(),
        source_channel="telegram",
        item_key="telegram_chat:99999",
    )
    # Channel 4: quote_ui with quote_id
    r3 = store_job_image(
        _png_bytes(),
        source_channel="quote_ui",
        quote_id="Q-FOUR",
        route_to="workroom",
    )
    # Channel 5: luxeforge_intake with intake_project item_key
    r4 = store_job_image(
        _png_bytes(),
        source_channel="luxeforge_intake",
        item_key="intake_project:IP-FOUR",
    )

    # Bucket resolution.
    assert (d44_env["photos_dir"] / "job" / "unassigned" / r1["filename"]).exists()
    assert (d44_env["photos_dir"] / "job" / "unassigned" / r2["filename"]).exists()
    assert (d44_env["photos_dir"] / "job" / "quote_Q-FOUR" / r3["filename"]).exists()
    # Channel 5 falls in unassigned (no quote_id, no job_id) keyed by item_key.
    assert (d44_env["photos_dir"] / "job" / "unassigned" / r4["filename"]).exists()

    # DB queryability per source_channel.
    # 3 channels land in unassigned (no quote_id, no job_id);
    # channel 4 (quote_ui with quote_id="Q-FOUR") lands under that quote.
    assert len(list_job_documents(unassigned=True)) == 3
    assert len(list_job_documents(quote_id="Q-FOUR")) == 1

    conn = sqlite3.connect(d44_env["db_path"])
    by_channel = dict(conn.execute(
        "SELECT source_channel, COUNT(*) FROM job_documents GROUP BY source_channel"
    ).fetchall())
    assert by_channel == {"max_chat": 1, "telegram": 1, "quote_ui": 1, "luxeforge_intake": 1}
    conn.close()
