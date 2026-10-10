"""check_outlook / outlook_reader: read-only Graph mail, mocked HTTP only (no network, temp token file)."""
from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from app.services.max import outlook_reader as orx

_RealClient = httpx.Client


@pytest.fixture
def tok_path(tmp_path, monkeypatch):
    p = tmp_path / "outlook" / "token.json"
    monkeypatch.setenv("OUTLOOK_TOKEN_PATH", str(p))
    monkeypatch.delenv("OUTLOOK_CLIENT_ID", raising=False)
    monkeypatch.delenv("OUTLOOK_TENANT", raising=False)
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    return p


class Recorder:
    def __init__(self, handler):
        self.handler = handler
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request):
        self.calls.append(request)
        return self.handler(request)

    def client(self):
        return _RealClient(transport=httpx.MockTransport(self))


def _form(req):
    return {k: v[0] for k, v in parse_qs(req.content.decode()).items()}


def _signed_in(p: Path, expires_in=3600, access="AT-valid"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"access_token": access, "refresh_token": "RT-secret",
                             "expires_at": int(time.time()) + expires_in, "scope": "Mail.Read",
                             "client_id": orx.DEFAULT_CLIENT_ID, "tenant": "common"}))


MSG = {"id": "AAMk-1=", "subject": "Channel back fabric", "receivedDateTime": "2026-10-08T14:00:00Z",
       "from": {"emailAddress": {"name": "Marley's", "address": "owner@marleys.example"}},
       "bodyPreview": "Can you confirm the 18 inch cut", "isRead": False, "hasAttachments": True}


def _tool():
    from app.services.max.tool_executor import TOOL_REGISTRY
    return TOOL_REGISTRY["check_outlook"]


# ── not signed in ──────────────────────────────────────────────────────────

def test_tool_not_signed_in_gives_clear_message_and_no_network(tok_path, monkeypatch):
    rec = Recorder(lambda r: pytest.fail("network used while not signed in"))
    monkeypatch.setattr(orx.httpx, "Client", lambda **kw: rec.client())
    res = _tool()({"tool": "check_outlook", "from_sender": "Marley"})
    assert res.success is False
    assert "Outlook not signed in yet" in res.error
    assert "outlook_auth.py" in res.error
    assert rec.calls == []


def test_status_reports_without_secrets(tok_path):
    assert orx.status()["signed_in"] is False
    _signed_in(tok_path)
    s = orx.status()
    assert s["signed_in"] is True
    assert "RT-secret" not in json.dumps(s) and "AT-valid" not in json.dumps(s)


# ── device-code sign-in ───────────────────────────────────────────────────

def test_device_code_requests_only_read_scopes(tok_path):
    def h(req):
        assert req.url.path.endswith("/common/oauth2/v2.0/devicecode")
        f = _form(req)
        assert f["client_id"] == orx.DEFAULT_CLIENT_ID
        assert set(f["scope"].split()) == {"https://graph.microsoft.com/Mail.Read", "offline_access"}
        return httpx.Response(200, json={"device_code": "DC", "user_code": "ABCD-EFGH",
                                         "verification_uri": "https://microsoft.com/devicelogin",
                                         "interval": 1, "expires_in": 900})
    rec = Recorder(h)
    flow = orx.start_device_code(http=rec.client())
    assert flow["user_code"] == "ABCD-EFGH"
    for word in ("Send", "ReadWrite", "Write"):
        assert word not in " ".join(orx.SCOPES)


def test_device_code_poll_saves_token_600_in_700_dir(tok_path):
    seq = [httpx.Response(400, json={"error": "authorization_pending"}),
           httpx.Response(400, json={"error": "slow_down"}),
           httpx.Response(200, json={"access_token": "AT1", "refresh_token": "RT1",
                                     "expires_in": 3600, "scope": "Mail.Read"})]
    rec = Recorder(lambda r: seq.pop(0))
    data = orx.poll_device_code({"device_code": "DC", "interval": 1, "expires_in": 900},
                                http=rec.client(), sleep=lambda s: None)
    assert data["refresh_token"] == "RT1"
    assert stat.S_IMODE(os.stat(tok_path).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(tok_path.parent).st_mode) == 0o700
    assert _form(rec.calls[0])["grant_type"] == "urn:ietf:params:oauth:grant-type:device_code"
    assert orx.status()["signed_in"] is True


def test_device_code_declined_raises(tok_path):
    rec = Recorder(lambda r: httpx.Response(400, json={"error": "authorization_declined"}))
    with pytest.raises(RuntimeError, match="authorization_declined"):
        orx.poll_device_code({"device_code": "DC", "interval": 1, "expires_in": 900},
                             http=rec.client(), sleep=lambda s: None)
    assert not tok_path.exists()


# ── listing / searching ───────────────────────────────────────────────────

def test_search_from_sender_uses_get_and_kql(tok_path):
    _signed_in(tok_path)
    def h(req):
        assert req.method == "GET"
        assert req.url.path == "/v1.0/me/messages"
        assert req.headers["Authorization"] == "Bearer AT-valid"
        assert req.headers["ConsistencyLevel"] == "eventual"
        q = dict(req.url.params)
        assert q["$search"].startswith('"') and "from:Marley" in q["$search"]
        assert "received>=" in q["$search"]
        assert q["$top"] == "5"
        return httpx.Response(200, json={"value": [MSG]})
    rec = Recorder(h)
    res = orx.search_messages(from_sender="Marley", since="2026-10-01", limit=5, http=rec.client())
    assert res["count"] == 1
    e = res["emails"][0]
    assert e["from"] == "Marley's <owner@marleys.example>"
    assert e["subject"] == "Channel back fabric" and e["unread"] is True and e["id"] == "AAMk-1="


def test_list_inbox_recent_uses_filter_and_orderby(tok_path):
    _signed_in(tok_path)
    def h(req):
        assert req.method == "GET"
        assert req.url.path == "/v1.0/me/mailFolders/inbox/messages"
        q = dict(req.url.params)
        assert q["$filter"].startswith("receivedDateTime ge ") and "isRead eq false" in q["$filter"]
        assert q["$orderby"] == "receivedDateTime desc"
        return httpx.Response(200, json={"value": []})
    res = orx.search_messages(folder="Inbox", since="7d", unread_only=True, http=Recorder(h).client())
    assert res["count"] == 0


def test_named_folder_lookup(tok_path):
    _signed_in(tok_path)
    def h(req):
        assert req.method == "GET"
        if req.url.path == "/v1.0/me/mailFolders":
            assert "displayName eq 'Clients'" in dict(req.url.params)["$filter"]
            return httpx.Response(200, json={"value": [{"id": "FOLD/1=", "displayName": "Clients"}]})
        assert req.url.raw_path.startswith(b"/v1.0/me/mailFolders/FOLD%2F1%3D/messages")
        return httpx.Response(200, json={"value": [MSG]})
    assert orx.search_messages(folder="Clients", http=Recorder(h).client())["count"] == 1


def test_bad_since_is_rejected():
    with pytest.raises(ValueError):
        orx._parse_since("last tuesday-ish")


# ── read one message ──────────────────────────────────────────────────────

def test_read_message_text_body_truncated(tok_path):
    _signed_in(tok_path)
    def h(req):
        assert req.method == "GET"
        assert req.headers["Prefer"] == 'outlook.body-content-type="text"'
        return httpx.Response(200, json={**MSG, "body": {"contentType": "text", "content": "x" * 9000},
                                         "toRecipients": [{"emailAddress": {"address": "rafa@example.com"}}]})
    res = orx.read_message("AAMk-1=", http=Recorder(h).client())
    assert res["to"] == ["rafa@example.com"]
    assert res["body"].endswith("[... truncated]") and len(res["body"]) < 8100


def test_read_message_rejects_bad_id(tok_path):
    _signed_in(tok_path)
    with pytest.raises(ValueError):
        orx.read_message("../sendMail", http=Recorder(lambda r: pytest.fail("no call")).client())


# ── token refresh ─────────────────────────────────────────────────────────

def test_expired_token_refreshes_and_keeps_600(tok_path):
    _signed_in(tok_path, expires_in=-10, access="AT-old")
    def h(req):
        if req.url.host == "login.microsoftonline.com":
            f = _form(req)
            assert f["grant_type"] == "refresh_token" and f["refresh_token"] == "RT-secret"
            assert set(f["scope"].split()) == set(orx.SCOPES)
            return httpx.Response(200, json={"access_token": "AT-new", "expires_in": 3600, "scope": "Mail.Read"})
        assert req.headers["Authorization"] == "Bearer AT-new"
        return httpx.Response(200, json={"value": []})
    orx.search_messages(http=Recorder(h).client())
    saved = json.loads(tok_path.read_text())
    assert saved["access_token"] == "AT-new" and saved["refresh_token"] == "RT-secret"
    assert stat.S_IMODE(os.stat(tok_path).st_mode) == 0o600


def test_revoked_refresh_token_says_sign_in_again(tok_path, monkeypatch):
    _signed_in(tok_path, expires_in=-10)
    rec = Recorder(lambda r: httpx.Response(400, json={"error": "invalid_grant"}))
    monkeypatch.setattr(orx.httpx, "Client", lambda **kw: rec.client())
    res = _tool()({"query": "invoice"})
    assert res.success is False and "in again" in res.error and "outlook_auth.py" in res.error
    assert "RT-secret" not in (res.error + json.dumps(res.result or {}))


# ── read-only guarantees ──────────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/me/sendMail", "/me/messages/abc/send", "/me/messages/abc/move",
                                  "/me/messages/abc/reply", "/me/messages/abc/forward", "/me/events",
                                  "/users/someone/messages", "/me/messages/abc/attachments"])
def test_graph_get_refuses_non_read_paths(tok_path, path):
    _signed_in(tok_path)
    with pytest.raises(PermissionError):
        orx._graph_get(Recorder(lambda r: pytest.fail("no call")).client(), path)


def test_module_has_no_write_calls():
    import inspect
    from app.services.max import tools_outlook
    import ast

    def _code(mod):
        tree = ast.parse(inspect.getsource(mod))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and ast.get_docstring(node):
                node.body = node.body[1:] or [ast.Pass()]
        return ast.unparse(tree)
    code = _code(orx) + _code(tools_outlook).split("OUTLOOK_TOOLS_DOC")[0]
    for bad in ("sendMail", '"DELETE"', '"PATCH"', '"PUT"', "/send", "/move", "/reply", "/forward",
                "Mail.Send", "Mail.ReadWrite", "isRead\": True", ".patch(", ".delete(", ".put("):
        assert bad not in code, bad
    # The only non-GET calls are to the Microsoft login token endpoints.
    assert code.count(".request(") == 1 and ".request('GET'" in code


def test_tool_lists_via_handler_and_never_returns_token(tok_path, monkeypatch):
    _signed_in(tok_path)
    rec = Recorder(lambda r: httpx.Response(200, json={"value": [MSG]}))
    monkeypatch.setattr(orx.httpx, "Client", lambda **kw: rec.client())
    res = _tool()({"from": "Marley", "limit": 3})
    assert res.success is True and res.result["emails"][0]["subject"] == "Channel back fabric"
    assert all(r.method == "GET" for r in rec.calls)
    assert "AT-valid" not in json.dumps(res.result) and "RT-secret" not in json.dumps(res.result)
    res2 = _tool()({"message_id": "AAMk-1="})
    assert res2.success is True


def test_family_edition_refused(tok_path, monkeypatch):
    _signed_in(tok_path)
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    rec = Recorder(lambda r: pytest.fail("network used in family edition"))
    monkeypatch.setattr(orx.httpx, "Client", lambda **kw: rec.client())
    res = _tool()({"query": "x"})
    assert res.success is False and "not available" in res.error


def test_registration_doc_aliases_and_untrusted():
    from app.services.max import tool_executor as te
    from app.services.max.founder_session import UNTRUSTED_CONTENT_TOOLS
    from app.services.max.access_control import AccessController
    assert "check_outlook" in te.TOOL_REGISTRY
    assert "**check_outlook**" in te.TOOLS_DOC
    assert "check_outlook" in UNTRUSTED_CONTENT_TOOLS
    src = Path(te.__file__).read_text()
    assert '"outlook": "check_outlook"' in src
    # Founder-only like check_email (not opened to other roles).
    assert int(AccessController.classify_tool(AccessController.__new__(AccessController), "check_outlook")) == \
        int(AccessController.classify_tool(AccessController.__new__(AccessController), "check_email"))


def test_outlook_auth_cli_status(tok_path, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location("outlook_auth", Path(__file__).resolve().parents[1] / "outlook_auth.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--status"]) == 0
    assert "Outlook signed in: no" in capsys.readouterr().out
    _signed_in(tok_path)
    mod.main(["--status"])
    out = capsys.readouterr().out
    assert "Outlook signed in: yes" in out and "RT-secret" not in out
