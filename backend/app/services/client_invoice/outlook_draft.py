"""Outlook Graph drafts only: createReply / create draft + attach PDF. Never send."""
from __future__ import annotations

import base64
import logging
import re
from typing import Any, Callable, Optional
from urllib.parse import quote, urlparse

import httpx

logger = logging.getLogger("max.client_invoice.outlook")

GRAPH = "https://graph.microsoft.com/v1.0"
_FORBIDDEN_PATH = re.compile(r"/(send)(Mail)?/?$", re.IGNORECASE)
_REDACT = re.compile(r"(?i)(authorization|access_token|bearer)\s*[:=]\s*\S+")

_ALLOWED_GET = (
    re.compile(r"^/me/messages$"),
    re.compile(r"^/me/messages/[A-Za-z0-9_\-=%]+$"),
    re.compile(r"^/users/[^/]+/messages$"),
    re.compile(r"^/users/[^/]+/messages/[A-Za-z0-9_\-=%]+$"),
)
_ALLOWED_WRITE = (
    re.compile(r"^/me/messages$"),  # create draft
    re.compile(r"^/me/messages/[A-Za-z0-9_\-=%]+$"),  # PATCH draft body
    re.compile(r"^/me/messages/[A-Za-z0-9_\-=%]+/createReply$"),
    re.compile(r"^/me/messages/[A-Za-z0-9_\-=%]+/attachments$"),
    re.compile(r"^/users/[^/]+/messages$"),
    re.compile(r"^/users/[^/]+/messages/[A-Za-z0-9_\-=%]+$"),
    re.compile(r"^/users/[^/]+/messages/[A-Za-z0-9_\-=%]+/createReply$"),
    re.compile(r"^/users/[^/]+/messages/[A-Za-z0-9_\-=%]+/attachments$"),
)


class OutlookSendForbidden(RuntimeError):
    """Raised if any Graph call would send mail."""


class OutlookDraftError(RuntimeError):
    pass


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _REDACT.sub(r"\1: [redacted]", value)
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if str(k).lower() in {"authorization", "access_token", "token", "contentbytes"}:
                out[k] = "[redacted]"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _log(log: list | None, event: str, **fields: Any) -> None:
    row = {"event": event, **_redact(fields)}
    if log is not None:
        log.append(row)
    logger.info("outlook %s %s", event, {k: v for k, v in row.items() if k != "event"})


def _graph_path(url: str) -> str:
    p = urlparse(url)
    path = p.path or url
    if path.startswith("/v1.0"):
        path = path[5:]
    return path


def _assert_allowed(method: str, path: str) -> None:
    if _FORBIDDEN_PATH.search(path) or "sendMail" in path:
        raise OutlookSendForbidden(f"Outlook send path is forbidden: {path}")
    rules = _ALLOWED_GET if method.upper() == "GET" else _ALLOWED_WRITE
    if method.upper() not in {"GET", "POST", "PATCH"}:
        raise OutlookSendForbidden(f"Outlook {method} is not allowed")
    if not any(r.match(path) for r in rules):
        raise OutlookSendForbidden(f"Outlook path not on the draft allowlist: {method} {path}")


class OutlookDraftClient:
    """createReply / create draft + attach. There is no send method."""

    def __init__(
        self,
        *,
        access_token: str,
        mailbox: str = "",
        http: Optional[httpx.Client] = None,
        http_factory: Optional[Callable[[], httpx.Client]] = None,
        log: Optional[list] = None,
        api_base: str = GRAPH,
    ):
        if not (access_token or "").strip():
            raise OutlookDraftError("Outlook access token is not configured for this business")
        self._token = access_token
        self.mailbox = (mailbox or "").strip()
        self._http = http
        self._http_factory = http_factory
        self.log = log if log is not None else []
        self.api_base = api_base.rstrip("/")

    def _root(self) -> str:
        if self.mailbox and self.mailbox.lower() not in {"me", "/me"}:
            return f"/users/{quote(self.mailbox)}"
        return "/me"

    def _client(self) -> httpx.Client:
        if self._http is not None:
            return self._http
        if self._http_factory is not None:
            return self._http_factory()
        return httpx.Client(timeout=20)

    def request(self, method: str, path: str, json_body: dict | None = None, params: dict | None = None) -> dict:
        path = path if path.startswith("/") else "/" + path
        _assert_allowed(method, path)
        url = path if path.startswith("http") else f"{self.api_base}{path}"
        own = self._http is None and self._http_factory is None
        client = self._client()
        try:
            resp = client.request(
                method.upper(), url,
                headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
                json=json_body, params=params,
            )
        finally:
            if own:
                client.close()
        _log(self.log, "outlook_http", method=method.upper(), path=_graph_path(url),
             is_draft=True, status=resp.status_code)
        if resp.status_code >= 400:
            raise OutlookDraftError(f"Outlook {method} {_graph_path(url)} failed ({resp.status_code})")
        try:
            return resp.json() if resp.content else {}
        except Exception as exc:
            raise OutlookDraftError("Outlook returned a non-JSON body") from exc

    def find_thread_message(self, client_email: str) -> Optional[dict]:
        email = (client_email or "").strip()
        if not email:
            return None
        data = self.request(
            "GET", f"{self._root()}/messages",
            params={
                "$search": f'"from:{email}"',
                "$top": "1",
                "$select": "id,subject,conversationId,from,receivedDateTime,isDraft",
            },
        )
        msgs = data.get("value") or []
        return msgs[0] if msgs else None

    def create_draft_reply(
        self,
        *,
        body_html: str,
        subject: str,
        to_email: str,
        pdf_bytes: bytes,
        pdf_name: str,
        reply_to_id: str | None = None,
    ) -> dict:
        """Draft reply in the existing thread, or a standalone draft if none exists.

        Graph verbs used: createReply (preferred) or POST /messages with isDraft=true.
        Never calls send or sendMail.
        """
        root = self._root()
        if reply_to_id:
            draft = self.request("POST", f"{root}/messages/{quote(reply_to_id, safe='')}/createReply")
            _log(self.log, "outlook_create_reply", draft_id=draft.get("id"), reply_to=reply_to_id)
        else:
            draft = self.request("POST", f"{root}/messages", {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": [{"emailAddress": {"address": to_email}}],
                "isDraft": True,
            })
            _log(self.log, "outlook_create_draft", draft_id=draft.get("id"), thread_found=False)
        draft_id = draft.get("id")
        if not draft_id:
            raise OutlookDraftError("Outlook did not return a draft id")

        self.request("PATCH", f"{root}/messages/{quote(draft_id, safe='')}", {
            "body": {"contentType": "HTML", "content": body_html},
            "isDraft": True,
        })
        self.request("POST", f"{root}/messages/{quote(draft_id, safe='')}/attachments", {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": pdf_name,
            "contentType": "application/pdf",
            "contentBytes": base64.b64encode(pdf_bytes or b"").decode("ascii"),
        })
        _log(self.log, "outlook_draft_ready", draft_id=draft_id, is_draft=True,
             attached=pdf_name, sent=False)
        return {
            "draft_id": draft_id,
            "is_draft": True,
            "sent": False,
            "thread_found": bool(reply_to_id),
            "conversation_id": draft.get("conversationId"),
            "web_link": draft.get("webLink"),
        }
