"""Gmail attachments + Google Drive in find_files, with stubbed Google APIs (no network, temp files only)."""
from __future__ import annotations

import base64
import json
import os
import time

import pytest

from app.services.max import cloud_files as cf
from app.services.max import file_finder as ff
from app.services.max import tools_files as tf


class _Exec:
    def __init__(self, value):
        self.value = value

    def execute(self):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


PDF = b"%PDF-1.4 gmail attachment"


class FakeGmail:
    def __init__(self, messages):
        self.messages_data = messages
        self.queries = []

    def users(self):
        return self

    def messages(self):
        return self

    def attachments(self):
        return self

    def list(self, userId, q, maxResults):
        self.queries.append(q)
        return _Exec({"messages": [{"id": m["id"]} for m in self.messages_data]})

    def get(self, userId, id=None, format=None, messageId=None):
        if messageId:  # attachments().get
            return _Exec({"data": base64.urlsafe_b64encode(PDF).decode()})
        return _Exec(next(m for m in self.messages_data if m["id"] == id))


def _msg(mid, subject, files):
    return {"id": mid, "threadId": "t" + mid, "internalDate": str(int(time.time() * 1000)),
            "payload": {"headers": [{"name": "Subject", "value": subject}, {"name": "From", "value": "Lauren <l@x.com>"}],
                        "parts": [{"filename": f, "mimeType": "application/pdf",
                                   "body": {"attachmentId": f"a-{i}", "size": 1234}} for i, f in enumerate(files)]}}


class FakeDrive:
    def __init__(self, files):
        self.files_data = files
        self.queries = []

    def files(self):
        return self

    def list(self, **kw):
        self.queries.append(kw["q"])
        return _Exec({"files": self.files_data})

    def get_media(self, fileId, supportsAllDrives=True):
        return _Exec(b"%PDF-1.4 drive file")

    def export(self, fileId, mimeType):
        assert mimeType == "application/pdf"
        return _Exec(b"%PDF-1.4 exported doc")


class RefreshError(Exception):
    pass


@pytest.fixture()
def env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "jobs" / "nehal-elrefai").mkdir(parents=True)
    (home / "jobs" / "nehal-elrefai" / "EST-2026-297-phase1-v26-FINAL-nobump.pdf").write_bytes(b"%PDF local")
    aliases = tmp_path / "aliases.json"
    aliases.write_text(json.dumps({"clients": [{"name": "Nehal Elrefai", "aliases": ["Dahlia", "Nehal"], "address": ""}]}))
    monkeypatch.setenv("MAX_CLIENT_ALIASES_PATH", str(aliases))
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(home))
    monkeypatch.setenv("GDRIVE_TOKEN_PATH", str(tmp_path / "no-drive-token.json"))
    ff.INDEX.clear()
    gmail = FakeGmail([
        _msg("m1", "Nehal estimate signed", ["EST-2026-298-phase2-signed.pdf", "token.json", ".env", "empire-amp-notes.pdf"]),
        _msg("m2", "Dahlia drapery photos", ["living-room.pdf"]),
    ])
    drive = FakeDrive([
        {"id": "d1", "name": "Nehal Elrefai estimate FINAL", "mimeType": "application/vnd.google-apps.document",
         "modifiedTime": "2026-10-05T12:00:00Z", "webViewLink": "https://docs.google.com/d1"},
        {"id": "d2", "name": "client_secret_backup.json", "mimeType": "application/json", "modifiedTime": "2026-10-05T12:00:00Z"},
    ])
    yield {"home": home, "gmail": gmail, "drive": drive, "tmp": tmp_path}
    ff.INDEX.clear()


def _patch(monkeypatch, gmail=None, drive=None, gmail_exc=None):
    monkeypatch.setattr(cf, "_gmail_service", (lambda: (_ for _ in ()).throw(gmail_exc)) if gmail_exc else (lambda: gmail))
    if drive is not None:
        monkeypatch.setattr(cf, "_drive_service", lambda: drive)
        monkeypatch.setattr(cf, "drive_token_path", lambda: type("P", (), {"exists": lambda self: True})())


def test_gmail_query_uses_aliases_and_readonly_only(env):
    q = ff.parse_query("Dahlia estimate")
    gq = cf.gmail_query(q)
    assert gq.startswith("has:attachment") and "dahlia" in gq and "elrefai" in gq
    assert cf.GMAIL_SCOPES == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert cf.DRIVE_SCOPES == ["https://www.googleapis.com/auth/drive.readonly"]


def test_find_files_merges_local_gmail_drive_ranked(env, monkeypatch):
    _patch(monkeypatch, gmail=env["gmail"], drive=env["drive"])
    r = tf._find_files({"query": "Nehal estimate"})
    assert r.success
    res = r.result
    names = [m["name"] for m in res["matches"]]
    srcs = {m["source"] for m in res["matches"]}
    assert {"local", "gmail", "drive"} <= srcs
    assert "EST-2026-297-phase1-v26-FINAL-nobump.pdf" in names
    assert "EST-2026-298-phase2-signed.pdf" in names and "Nehal Elrefai estimate FINAL" in names
    for bad in ("token.json", ".env", "empire-amp-notes.pdf", "client_secret_backup.json"):
        assert bad not in names
    scores = [m["score"] for m in res["matches"]]
    assert scores == sorted(scores, reverse=True)
    assert res["sources"] == {"local": "ok", "gmail": "ok", "drive": "ok"}


def test_bad_gmail_auth_says_needs_reauth_not_missing(env, monkeypatch):
    _patch(monkeypatch, gmail_exc=RefreshError("invalid_grant: Token has been expired or revoked."))
    r = tf._find_files({"query": "Nehal estimate"})
    assert r.success  # local still found
    assert r.result["sources"]["gmail"] == "needs_reauth"
    assert "Gmail needs re-auth" in r.result["message"]
    assert r.result["sources"]["drive"] == "not_connected" and "Drive is not connected" in r.result["message"]
    # nothing local either: error must say the source was not searched
    r2 = tf._find_files({"query": "zzqx invoice from plumber"})
    assert not r2.success and "Gmail needs re-auth" in r2.error and "not searched" in r2.error.lower()


def test_drive_token_with_write_scope_refused(env, monkeypatch, tmp_path):
    tok = tmp_path / "drive-token.json"
    tok.write_text(json.dumps({"token": "x", "refresh_token": "y", "client_id": "c", "client_secret": "s",
                               "token_uri": "https://oauth2.googleapis.com/token",
                               "scopes": ["https://www.googleapis.com/auth/drive"]}))
    monkeypatch.setenv("GDRIVE_TOKEN_PATH", str(tok))
    res = cf.search_drive(ff.parse_query("Nehal estimate"))
    assert res["status"] == "error" and "drive.readonly" in res["message"] and res["hits"] == []


def test_share_gmail_attachment_studio_and_email(env, monkeypatch):
    _patch(monkeypatch, gmail=env["gmail"], drive=env["drive"])
    r = tf._find_files({"query": "Nehal estimate"})
    gm = next(m for m in r.result["matches"] if m["source"] == "gmail")
    s = tf._share_file({"file_id": gm["file_id"], "via": "studio"})
    assert s.success and s.result["viewer_url"].startswith("/api/v1/files/found?t=")
    real = ff.verify_share_token(s.result["viewer_url"].split("t=", 1)[1])
    assert real and open(real, "rb").read() == PDF and "max-cloud-share-" in real
    import app.services.max.tool_executor as te
    sent = []

    class R:
        def __init__(self, d): self.d = d
        def to_dict(self): return self.d

    monkeypatch.setattr(te, "execute_tool", lambda call, **kw: (sent.append(call), R({"success": True, "result": {
        "sent_to": call["to"], "message_id": "<m>", "attachments_sent": 1}}))[1])
    e = tf._share_file({"file_id": gm["file_id"], "via": "email"})
    assert e.success and sent[0]["to"] == "empirebox2026@gmail.com"
    bad = tf._share_file({"file_id": gm["file_id"], "via": "email", "to": "client@example.com"})
    assert not bad.success and "explicit yes" in bad.error


def test_share_google_doc_exports_pdf(env, monkeypatch):
    _patch(monkeypatch, gmail=env["gmail"], drive=env["drive"])
    r = tf._find_files({"query": "Nehal estimate"})
    dm = next(m for m in r.result["matches"] if m["source"] == "drive")
    s = tf._share_file({"file_id": dm["file_id"], "via": "studio"})
    assert s.success and s.result["name"].endswith(".pdf")
    real = ff.verify_share_token(s.result["viewer_url"].split("t=", 1)[1])
    assert open(real, "rb").read().startswith(b"%PDF-1.4 exported")


def test_share_remote_with_bad_token_says_reauth(env, monkeypatch):
    _patch(monkeypatch, gmail=env["gmail"], drive=env["drive"])
    r = tf._find_files({"query": "Nehal estimate"})
    gm = next(m for m in r.result["matches"] if m["source"] == "gmail")
    monkeypatch.setattr(cf, "_gmail_service", lambda: (_ for _ in ()).throw(RefreshError("invalid_grant")))
    s = tf._share_file({"file_id": gm["file_id"], "via": "email"})
    assert not s.success and "Gmail needs re-auth" in s.error


def test_voice_find_files_keeps_source_and_notes(env, monkeypatch):
    _patch(monkeypatch, gmail_exc=RefreshError("invalid_grant"))
    from app.services.max import voice_live as vl
    out = vl.run_voice_tool("find_files", {"query": "Nehal estimate"})
    assert out["success"]
    assert out["result"]["sources"]["gmail"] == "needs_reauth"
    assert any("Gmail needs re-auth" in n for n in out["result"]["source_notes"])
    assert all("source" in m for m in out["result"]["matches"])
