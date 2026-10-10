"""IMP-0005: file finder — Gmail attachments + Drive search (stubbed Google APIs).

Local search behavior is unchanged; cloud sources are injected via factories
so no Google credentials or network are needed.
"""
import json
import os
from pathlib import Path

import pytest

from app.services.max import file_finder
from app.services.max.file_finder import (
    DRIVE_SCOPES,
    GMAIL_SCOPES,
    find_files,
    is_excluded,
    match_score,
    normalize_alias,
    search_drive,
    search_gmail_attachments,
    search_local,
)


# ── Stub Google services ─────────────────────────────────────────────
class _StubExecutable:
    def __init__(self, payload):
        self._payload = payload

    def execute(self):
        return self._payload


class StubGmailService:
    """Mimics googleapiclient gmail v1 resource chaining."""

    def __init__(self, messages):
        # messages: {id: {"subject": ..., "attachments": [...] }}
        self._messages = messages
        self.list_query = None

    def users(self):
        return self

    def messages(self):
        return self._Msg(self)

    class _Msg:
        def __init__(self, outer):
            self._outer = outer
            self._mode = None
            self._kwargs = {}

        def list(self, **kwargs):
            self._outer.list_query = kwargs.get("q", "")
            self._mode = "list"
            return self

        def get(self, **kwargs):
            self._mode = "get"
            self._kwargs = kwargs
            return self

        def execute(self):
            if self._mode == "list":
                return {"messages": [{"id": mid} for mid in self._outer._messages]}
            mid = self._kwargs["id"]
            msg = self._outer._messages[mid]
            parts = [
                {"filename": name, "body": {"attachmentId": f"att-{i}", "size": 10}}
                for i, name in enumerate(msg["attachments"])
            ]
            return {
                "id": mid,
                "payload": {
                    "headers": [{"name": "Subject", "value": msg["subject"]}],
                    "parts": parts,
                },
            }


class StubDriveService:
    """Mimics googleapiclient drive v3 resource chaining."""

    def __init__(self, files):
        self._files = files
        self.list_query = None

    def files(self):
        return self

    def list(self, **kwargs):
        self.list_query = kwargs.get("q", "")
        return self

    def execute(self):
        return {"files": self._files}


class BadTokenError(Exception):
    pass


def _bad_token_factory():
    raise BadTokenError("invalid_grant: Token has been expired or revoked")


# ── Helpers ──────────────────────────────────────────────────────────
@pytest.fixture()
def local_tree(tmp_path):
    root = tmp_path / "uploads"
    root.mkdir()
    (root / "Johnson-curtain-measurements.pdf").write_text("local proof")
    (root / "johnson quote draft.txt").write_text("local proof")
    (root / ".env").write_text("SECRET=topsecret")
    (root / "gmail-token.json").write_text("{}")
    willard = root / "willard"
    willard.mkdir()
    (willard / "Johnson-family-notes.pdf").write_text("family data")
    return root


GMAIL_MESSAGES = {
    "m1": {"subject": "Johnson drapery final", "attachments": ["Johnson-final-invoice.pdf"]},
    "m2": {"subject": "unrelated", "attachments": ["random-photo.png"]},
}
DRIVE_FILES = [
    {"id": "d1", "name": "Johnson curtain measurements.pdf", "mimeType": "application/pdf"},
    {"id": "d2", "name": "unrelated.xlsx", "mimeType": "application/vnd.ms-excel"},
]


def _factories(gmail=None, drive=None):
    return {
        "gmail_factory": (lambda: gmail) if gmail is not None else None,
        "drive_factory": (lambda: drive) if drive is not None else None,
    }


# ── Tests ────────────────────────────────────────────────────────────
def test_local_search_unchanged(local_tree):
    hits = search_local("johnson curtain", roots=[local_tree])
    names = {h["name"] for h in hits}
    assert "Johnson-curtain-measurements.pdf" in names
    # Local hits carry proof and draft-only share paths.
    hit = next(h for h in hits if h["name"] == "Johnson-curtain-measurements.pdf")
    assert hit["source"] == "local"
    assert hit["verified"] is True
    assert hit["proof"]["path"].endswith("Johnson-curtain-measurements.pdf")
    assert hit["share"]["email_to"], "share must propose Rafael's addresses"
    assert "studio.empirebox.store" in hit["share"]["studio_link"]


def test_secret_and_family_exclusions(local_tree):
    hits = search_local("johnson", roots=[local_tree])
    names = {h["name"] for h in hits}
    assert ".env" not in names
    assert "gmail-token.json" not in names
    assert "Johnson-family-notes.pdf" not in names  # willard family data
    assert is_excluded(".env")
    assert is_excluded("token.json")
    assert is_excluded("family-x.pdf", ("willard",))


def test_alias_matching_same_for_all_sources():
    assert normalize_alias("Johnson_Curtain-Measurements.PDF") == "johnson curtain measurements pdf"
    assert match_score("johnson curtain", "Johnson-curtain-measurements.pdf") >= 60
    assert match_score("johnson curtain", "unrelated.xlsx") == 0


def test_merge_and_rank_local_gmail_drive(local_tree):
    result = find_files(
        "johnson",
        local_roots=[local_tree],
        **_factories(StubGmailService(GMAIL_MESSAGES), StubDriveService(DRIVE_FILES)),
    )
    assert result["gmail_status"] == "ok"
    assert result["drive_status"] == "ok"
    assert result["searched_sources"] == ["local", "gmail", "drive"]
    assert result["failed_sources"] == []
    sources = {h["source"] for h in result["results"]}
    assert sources == {"local", "gmail", "drive"}
    # Ranked by score desc — every hit scored against the same matcher.
    scores = [h["score"] for h in result["results"]]
    assert scores == sorted(scores, reverse=True)
    for hit in result["results"]:
        assert hit["verified"] is True and hit["proof"]


def test_bad_gmail_token_says_needs_reauth(local_tree, monkeypatch):
    monkeypatch.setenv("GMAIL_TOKEN_PATH", "/nonexistent/gmail-token.json")
    result = find_files(
        "johnson",
        local_roots=[local_tree],
        gmail_factory=_bad_token_factory,
        drive_factory=lambda: StubDriveService(DRIVE_FILES),
    )
    assert result["gmail_status"] == "needs_reauth"
    assert "gmail" in result["failed_sources"]
    assert any("Gmail needs re-auth" in n for n in result["notices"])
    # Local + Drive results still returned — never claim nothing exists.
    assert result["drive_status"] == "ok"
    assert any(h["source"] == "local" for h in result["results"])


def test_missing_gmail_token_says_needs_reauth(local_tree, monkeypatch, tmp_path):
    monkeypatch.setenv("GMAIL_TOKEN_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setattr(file_finder, "_GMAIL_CONFIG_TOKEN", tmp_path / "missing2.json")
    monkeypatch.setattr(file_finder, "_backend_dir", lambda: tmp_path)
    result = find_files("johnson", local_roots=[local_tree], drive_factory=lambda: StubDriveService([]))
    assert result["gmail_status"] == "needs_reauth"
    assert any("Gmail needs re-auth" in n for n in result["notices"])


def test_bad_drive_token_surfaces_reauth(local_tree):
    result = find_files(
        "johnson",
        local_roots=[local_tree],
        gmail_factory=lambda: StubGmailService(GMAIL_MESSAGES),
        drive_factory=_bad_token_factory,
    )
    assert result["drive_status"] == "needs_reauth"
    assert "drive" in result["failed_sources"]


def test_drive_skipped_without_credential(local_tree, monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_DRIVE_TOKEN_PATH", raising=False)
    monkeypatch.setattr(file_finder, "_DRIVE_CONFIG_TOKEN", tmp_path / "missing.json")
    result = find_files(
        "johnson",
        local_roots=[local_tree],
        gmail_factory=lambda: StubGmailService(GMAIL_MESSAGES),
    )
    assert result["drive_status"] == "not_configured"
    assert "drive" not in result["searched_sources"]
    assert "drive" not in result["failed_sources"]


def test_read_only_scopes_only():
    assert GMAIL_SCOPES == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert DRIVE_SCOPES == ["https://www.googleapis.com/auth/drive.readonly"]
    for scope in GMAIL_SCOPES + DRIVE_SCOPES:
        assert "readonly" in scope
        assert "drive.file" not in scope or "readonly" in scope


def test_gmail_search_uses_attachment_query():
    svc = StubGmailService(GMAIL_MESSAGES)
    out = search_gmail_attachments("johnson", gmail_factory=lambda: svc)
    assert out["status"] == "ok"
    assert "has:attachment" in svc.list_query
    assert {h["name"] for h in out["hits"]} == {"Johnson-final-invoice.pdf"}


def test_tool_registered_and_works_on_voice_channel(local_tree, monkeypatch):
    from app.services.max import tool_executor

    assert "find_files" in tool_executor.TOOL_REGISTRY
    monkeypatch.setenv("FILE_FINDER_LOCAL_ROOTS", str(local_tree))
    result = tool_executor.execute_tool(
        {"tool": "find_file", "query": "johnson"},  # alias auto-correct
        desk=None,
        access_context={"channel": "voice", "user": None},
        founder=True,
    )
    assert result.success is True
    assert result.result["count"] >= 1


def test_env_example_documents_drive_token():
    example = Path(__file__).resolve().parents[1] / ".env.example"
    text = example.read_text()
    assert "GOOGLE_DRIVE_TOKEN_PATH" in text
    assert "drive.readonly" in text
    assert "gmail.readonly" in text
