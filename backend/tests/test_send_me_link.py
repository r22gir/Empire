"""Fix B: send_me_this_link — hardcoded Rafael allowlist, mocked sends only."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from app.services.max import file_finder as ff
from app.services.max import send_me_link as sml


def _touch(p: Path, data: bytes = b"%PDF-1.4 drawing", age_days: float = 0.0) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    if age_days:
        t = time.time() - age_days * 86400
        os.utime(p, (t, t))
    return p


@pytest.fixture()
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    jobs = h / "jobs" / "marley"
    _touch(jobs / "marley-3d-drawing-v1.pdf", age_days=9)
    _touch(jobs / "marley-3d-drawing-latest.pdf", age_days=0.1)
    _touch(jobs / "marley-shop-drawing-26-3-4.pdf", age_days=2)
    aliases = tmp_path / "aliases.json"
    aliases.write_text(json.dumps({"clients": [
        {"name": "Marley", "aliases": ["Marleys", "Marley's"], "address": "Hyattsville"}
    ]}))
    monkeypatch.setenv("MAX_CLIENT_ALIASES_PATH", str(aliases))
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(h))
    monkeypatch.setenv("MAX_CLOUD_FILES_DISABLED", "1")
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    ff.INDEX.clear()
    yield h
    ff.INDEX.clear()


def test_allowlist_is_hardcoded_empirebox_only():
    assert sml.SEND_ME_EMAILS == frozenset({"empirebox2026@gmail.com"})
    assert "rafa22giraldo@gmail.com" in sml.BLOCKED_EMAILS
    assert "rafa22giraldo@gmail.com" not in sml.SEND_ME_EMAILS


@pytest.mark.parametrize("to", [
    "rafa22giraldo@gmail.com",
    "client@example.com",
    "brother@gmail.com",
    "nelma@example.com",
    "workroom@empirebox.store",
])
def test_rejects_any_other_email(to):
    gate = sml.authorize_recipient("email", to)
    assert gate["authorized"] is False
    assert "allowlist" in gate["error"]


def test_accepts_empirebox_and_me_alias():
    assert sml.authorize_recipient("email", "empirebox2026@gmail.com")["authorized"]
    assert sml.authorize_recipient("email", "me")["to"] == "empirebox2026@gmail.com"
    assert sml.authorize_recipient("email", "")["to"] == "empirebox2026@gmail.com"


def test_accepts_rafael_angle_bracket_email():
    gate = sml.authorize_recipient("email", "Rafael <empirebox2026@gmail.com>")
    assert gate["authorized"] is True
    assert gate["to"] == "empirebox2026@gmail.com"


def test_rejects_juan_and_camilo_by_name_and_number(monkeypatch):
    monkeypatch.setattr(sml, "founder_phones_ordered", lambda: ["15555550100"])
    monkeypatch.setattr(sml, "primary_founder_whatsapp", lambda: "15555550100")
    monkeypatch.setattr(sml, "_deliver_email", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no send")))
    monkeypatch.setattr(sml, "_deliver_whatsapp", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no send")))
    for to in (
        "Juan",
        "Camilo",
        "Juan Diego Giraldo",
        "Camilo Giraldo",
        "15715550111",
        "15715550222",
    ):
        wa = sml.authorize_recipient("whatsapp", to)
        assert wa["authorized"] is False, to
        mail = sml.authorize_recipient("email", to)
        assert mail["authorized"] is False, to
        out = sml.send_me_this_link({"query": "the 3D drawing", "via": "whatsapp", "to": to})
        assert not out["success"]


def test_primary_whatsapp_is_first_listed_not_sorted(monkeypatch):
    monkeypatch.setattr(sml, "founder_phones_ordered", lambda: ["15555550999", "12022996975"])
    monkeypatch.setattr(sml, "primary_founder_whatsapp", lambda: "15555550999")
    gate = sml.authorize_recipient("whatsapp", "me")
    assert gate["authorized"]
    assert gate["to"] == "15555550999"


def test_family_edition_data_dir_amp_refuses(monkeypatch, home):
    monkeypatch.setenv("EMPIRE_DATA_DIR", "/data/amp")
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.setattr(sml, "_deliver_email", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no send")))
    monkeypatch.setattr(sml, "_deliver_whatsapp", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no send")))
    out = sml.send_me_this_link({"query": "send me the 3D drawing", "via": "email", "to": "me"})
    assert not out["success"]
    assert "family" in (out.get("error") or "").lower()
    assert sml.send_me_link_doc() == ""
    from app.services.max import file_finder as ff
    assert ff._edition_allowed() is False
    from app.services.max import voice_live as vl
    assert "send_me_this_link" not in vl.voice_tool_allowlist()
    from app.services.max.voice_can_do import capability_list_for_prompt
    cap = capability_list_for_prompt()
    assert "I can send a link or document only to your WhatsApp" not in cap


def test_family_edition_maxine_refuses(monkeypatch, home):
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setattr(sml, "_deliver_email", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no send")))
    monkeypatch.setattr(sml, "_deliver_whatsapp", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no send")))
    out = sml.send_me_this_link({"query": "send me the 3D drawing", "via": "whatsapp", "to": "me"})
    assert not out["success"]
    assert "family" in (out.get("error") or "").lower()
    from app.services.max import file_finder as ff
    assert ff._edition_allowed() is False
    from app.services.max import voice_live as vl
    assert "send_me_this_link" not in vl.voice_tool_allowlist()


def test_rejects_non_founder_whatsapp(monkeypatch):
    monkeypatch.setattr(sml, "founder_whatsapp_numbers", lambda: frozenset({"15555550100"}))

    class _WA:
        @staticmethod
        def normalize_msisdn(n):
            return "".join(c for c in n if c.isdigit())

        @staticmethod
        def is_allowlisted(n):
            return n == "15555550100"

    import app.services.max.whatsapp_channel as wa
    monkeypatch.setattr(wa, "normalize_msisdn", _WA.normalize_msisdn)
    monkeypatch.setattr(wa, "is_allowlisted", _WA.is_allowlisted)
    bad = sml.authorize_recipient("whatsapp", "15551234567")
    assert bad["authorized"] is False


def test_the_3d_drawing_resolves_to_most_recent(home):
    looked = sml.find_latest_document("the 3D drawing")
    assert looked["found"]
    assert looked["match"]["name"] == "marley-3d-drawing-latest.pdf"
    assert looked["query"]


def test_that_drawing_resolves_to_newest_drawing(home):
    looked = sml.find_latest_document("that drawing")
    assert looked["found"]
    name = looked["match"]["name"]
    assert "drawing" in name
    assert name == "marley-3d-drawing-latest.pdf"


def test_email_send_is_mocked_and_only_empirebox(home, monkeypatch):
    sent = []

    def fake_email(path, *, to, subject, body):
        sent.append({"path": path, "to": to, "subject": subject, "body": body})
        return {"message_id": "<mock>"}

    def boom_wa(*a, **k):
        raise AssertionError("WhatsApp must not be called")

    monkeypatch.setattr(sml, "_deliver_email", fake_email)
    monkeypatch.setattr(sml, "_deliver_whatsapp", boom_wa)
    out = sml.send_me_this_link({
        "query": "the 3D drawing",
        "via": "email",
        "to": "me",
    })
    assert out["success"], out.get("error")
    assert sent[0]["to"] == "empirebox2026@gmail.com"
    assert out["result"]["sent_to"] == "empirebox2026@gmail.com"
    assert "3d-drawing-latest" in out["result"]["name"]


def test_whatsapp_send_is_mocked_and_founder_only(home, monkeypatch):
    sent = []
    monkeypatch.setattr(sml, "authorize_recipient", lambda via, to: {
        "authorized": True, "via": "whatsapp", "to": "15555550100", "error": None,
    })

    def fake_wa(path, *, to, caption):
        sent.append({"path": path, "to": to, "caption": caption})
        return {"media_id": "MEDIA-MOCK"}

    def boom_email(*a, **k):
        raise AssertionError("Email must not be called")

    monkeypatch.setattr(sml, "_deliver_whatsapp", fake_wa)
    monkeypatch.setattr(sml, "_deliver_email", boom_email)
    out = sml.send_me_this_link({
        "query": "that drawing",
        "via": "whatsapp",
    })
    assert out["success"], out.get("error")
    assert sent[0]["to"] == "15555550100"
    assert out["result"]["via"] == "whatsapp"
    assert out["result"]["sent_to"] == "rafael_whatsapp"


def test_blocked_email_never_reaches_deliver(home, monkeypatch):
    monkeypatch.setattr(sml, "_deliver_email", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no send")))
    monkeypatch.setattr(sml, "_deliver_whatsapp", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no send")))
    out = sml.send_me_this_link({
        "query": "the 3D drawing",
        "via": "email",
        "to": "rafa22giraldo@gmail.com",
    })
    assert not out["success"]
    assert "allowlist" in (out.get("error") or "")


def test_voice_allowlist_includes_send_me_and_blocks_other_to():
    from app.services.max import voice_live as vl
    assert "send_me_this_link" in vl.VOICE_TOOL_ALLOWLIST
    assert "get_today_agenda" in vl.VOICE_TOOL_ALLOWLIST
    assert "can_you_do" in vl.VOICE_TOOL_ALLOWLIST
    refused = vl.run_voice_tool("send_me_this_link", {"query": "send me the 3D drawing", "to": "client@x.com"})
    assert refused["success"] is False
    assert "empirebox2026@gmail.com" in refused["error"]
    also = vl.run_voice_tool("send_me_this_link", {"query": "send me the 3D drawing", "to": "rafa22giraldo@gmail.com"})
    assert also["success"] is False


def test_voice_send_requires_rafael_asked_to_send(home, monkeypatch):
    from app.services.max import voice_live as vl
    monkeypatch.setattr(sml, "_deliver_email", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no send")))
    monkeypatch.setattr(sml, "_deliver_whatsapp", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no wa")))
    refused = vl.run_voice_tool("send_me_this_link", {"query": "the 3D drawing", "via": "email", "to": "me"})
    assert refused["success"] is False
    assert "not ask" in (refused.get("error") or "").lower() or "not sent" in (refused.get("error") or "").lower()


def test_voice_authorized_send_is_mocked(home, monkeypatch):
    from app.services.max import voice_live as vl
    sent = []

    def fake_email(path, *, to, subject, body):
        sent.append({"path": path, "to": to})
        return {"message_id": "<voice-mock>"}

    monkeypatch.setattr(sml, "_deliver_email", fake_email)
    monkeypatch.setattr(sml, "_deliver_whatsapp", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no wa")))
    out = vl.run_voice_tool(
        "send_me_this_link",
        {"query": "send me the 3D drawing", "via": "email", "to": "me"},
        user_text="send me the 3D drawing",
    )
    assert out["success"], out.get("error")
    assert sent[0]["to"] == "empirebox2026@gmail.com"
