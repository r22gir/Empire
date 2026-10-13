"""Force outbound email / WhatsApp / SMS to fakes under pytest.

This morning a suite run with the backend env loaded handed 10 real SMTP
messages to empirebox2026@gmail.com. Isolation of data paths was not
enough: ``app.services.email.sender`` and ``smtplib`` still saw live
SMTP_* / SENDGRID_* credentials.

Two layers, installed from conftest before app imports and again as
autouse fakes:

1. ``neutralize_send_env()`` blanks send credentials so imported
   senders start unconfigured.
2. ``install_network_tripwires()`` makes a real SMTP connect/send or an
   HTTP post to SendGrid / Twilio / Meta Graph raise TEST_VIOLATION.
3. ``install_fakes(monkeypatch)`` replaces ``send_email`` and the
   family-alert senders with in-memory recorders.

There is no opt-out that re-enables a live send. Tests that need to
inspect payloads monkeypatch the same names after this fixture.
"""
from __future__ import annotations

import os
import smtplib
from typing import Any
from urllib.request import Request

SEND_ENV_BLANK = (
    "SMTP_PASSWORD",
    "SMTP_USER",
    "SMTP_FROM",
    "SENDGRID_API_KEY",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "SMS_ACCOUNT_SID",
    "SMS_AUTH_TOKEN",
    "SMS_FROM_NUMBER",
    "FAMILY_ALERT_PHONE",
    "RAFAEL_ALERT_PHONE",
)

PROD_SMTP_HOSTS = frozenset({
    "smtp.gmail.com",
    "smtp.sendgrid.net",
    "smtp.office365.com",
    "smtp-relay.gmail.com",
    "email-smtp.us-east-1.amazonaws.com",
})

_installed_network = False
outbound_calls: list[dict[str, Any]] = []
violations: list[str] = []


class OutboundSendViolation(RuntimeError):
    """A test reached a live email / WhatsApp / SMS transport."""


def neutralize_send_env() -> dict[str, str]:
    """Blank live send credentials. Returns names that were changed."""
    changed: dict[str, str] = {}
    os.environ["FAMILY_ALERT_ENABLED"] = "false"
    changed["FAMILY_ALERT_ENABLED"] = "forced-false"
    for name in SEND_ENV_BLANK:
        if os.environ.get(name):
            os.environ[name] = ""
            changed[name] = "blanked"
    return changed


def _is_prod_smtp_host(host: str) -> bool:
    h = str(host or "").strip().lower().split(":")[0]
    if not h:
        return False
    if h in PROD_SMTP_HOSTS:
        return True
    return h.endswith(".gmail.com") or h.endswith(".sendgrid.net") or "twilio" in h


def is_outbound_send_url(url: str) -> bool:
    u = str(url or "").strip().lower()
    if not u:
        return False
    if "api.sendgrid.com" in u and "mail/send" in u:
        return True
    if "api.twilio.com" in u and "messages" in u:
        return True
    if "graph.facebook.com" in u and ("/messages" in u or "/media" in u):
        return True
    return False


def _trip(msg: str) -> None:
    expected = getattr(_expect, "caught", None)
    if expected is not None:
        expected.append(msg)
    else:
        violations.append(msg)
    raise OutboundSendViolation(msg)


class _Expect:
    caught: list[str] | None = None


_expect = _Expect()


class expect_outbound_block:
    """Tripwires inside this block are expected and do not fail the test."""

    def __enter__(self):
        self._prev = _expect.caught
        self.caught: list[str] = []
        _expect.caught = self.caught
        return self

    def __exit__(self, *exc):
        _expect.caught = self._prev
        return False


def install_network_tripwires() -> None:
    """Process-wide: real SMTP / send HTTP raises instead of sending."""
    global _installed_network
    if _installed_network:
        return
    _installed_network = True

    real_smtp_init = smtplib.SMTP.__init__
    real_ssl_init = smtplib.SMTP_SSL.__init__
    real_sendmail = smtplib.SMTP.sendmail
    real_ssl_sendmail = smtplib.SMTP_SSL.sendmail

    def _guard_init(original):
        def wrapped(self, host="", port=0, *args, **kwargs):
            if _is_prod_smtp_host(host):
                _trip(
                    f"TEST_VIOLATION: real SMTP connect to {host!r}. "
                    "Tests must use FakeSMTP / monkeypatch; live mail is forbidden."
                )
            return original(self, host, port, *args, **kwargs)
        return wrapped

    def _guard_sendmail(original):
        def wrapped(self, from_addr, to_addrs, msg, *args, **kwargs):
            host = getattr(self, "_host", None) or getattr(self, "host", None)
            if _is_prod_smtp_host(str(host or "")):
                _trip(
                    f"TEST_VIOLATION: real SMTP sendmail to {to_addrs!r} via {host!r}."
                )
            # Even a non-prod host using the real smtplib class is a send.
            outbound_calls.append({"kind": "smtp_sendmail", "to": to_addrs, "host": host})
            return original(self, from_addr, to_addrs, msg, *args, **kwargs)
        return wrapped

    smtplib.SMTP.__init__ = _guard_init(real_smtp_init)
    smtplib.SMTP_SSL.__init__ = _guard_init(real_ssl_init)
    smtplib.SMTP.sendmail = _guard_sendmail(real_sendmail)
    smtplib.SMTP_SSL.sendmail = _guard_sendmail(real_ssl_sendmail)

    try:
        import aiosmtplib

        async def _blocked_aiosmtp(*args, **kwargs):
            _trip("TEST_VIOLATION: real aiosmtplib.send")

        aiosmtplib.send = _blocked_aiosmtp
    except Exception:
        pass

    try:
        import httpx

        real_post = httpx.post

        def _guarded_post(url, *args, **kwargs):
            if is_outbound_send_url(str(url)):
                _trip(f"TEST_VIOLATION: real HTTP send to {url}")
            return real_post(url, *args, **kwargs)

        httpx.post = _guarded_post
    except Exception:
        pass

    import urllib.request

    real_urlopen = urllib.request.urlopen

    def _guarded_urlopen(*args, **kwargs):
        url = args[0] if args else kwargs.get("url")
        target = url.full_url if isinstance(url, Request) else url
        if is_outbound_send_url(str(target)):
            _trip(f"TEST_VIOLATION: real urllib send to {target}")
        return real_urlopen(*args, **kwargs)

    urllib.request.urlopen = _guarded_urlopen


def _record(kind: str, **payload: Any) -> dict[str, Any]:
    row = {"kind": kind, **payload}
    outbound_calls.append(row)
    return row


async def fake_send_email(to, subject, html_body, attachments=None):
    _record("email", to=to, subject=subject, html=html_body, attachments=attachments)
    return False


def fake_send_alert_text(wa_id: str, text: str) -> dict:
    _record("whatsapp", to=wa_id, text=text)
    return {"sent": False, "reason": "test_fake"}


def fake_send_sms(to: str, text: str) -> dict:
    _record("sms", to=to, text=text)
    return {"sent": False, "reason": "test_fake"}


def install_fakes(monkeypatch) -> None:
    """Point alert senders at in-memory recorders. Keep send_email itself
    (tests mock it or hit SendGrid with httpx mocked) but zero SMTP
    module constants captured from a live shell."""
    try:
        import app.services.email.sender as sender

        sender.SMTP_HOST = ""
        sender.SMTP_USER = ""
        sender.SMTP_PASSWORD = ""
        sender.SMTP_FROM = ""
        sender.SENDGRID_API_KEY = ""
    except Exception:
        pass
    monkeypatch.setattr(
        "app.services.whatsapp_cloud.send_alert_text", fake_send_alert_text, raising=False
    )
    monkeypatch.setattr(
        "app.services.family_alert.send_whatsapp",
        lambda to, text: fake_send_alert_text(to, text),
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.family_alert.send_sms", fake_send_sms, raising=False
    )
