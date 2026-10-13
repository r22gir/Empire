"""Tests must never send real email / WhatsApp / SMS."""
from __future__ import annotations

import os
import smtplib

import pytest

import _outbound_send_guard as _osg
from _outbound_send_guard import (
    OutboundSendViolation,
    expect_outbound_block,
    is_outbound_send_url,
    neutralize_send_env,
)


def test_send_env_is_neutralized():
    assert os.environ.get("FAMILY_ALERT_ENABLED") == "false"
    assert not os.environ.get("SMTP_PASSWORD")
    assert not os.environ.get("SENDGRID_API_KEY")
    assert not os.environ.get("TWILIO_AUTH_TOKEN")
    changed = neutralize_send_env()
    assert changed["FAMILY_ALERT_ENABLED"] == "forced-false"
    assert _osg.violations is not None


def test_prod_smtp_init_is_a_violation():
    with expect_outbound_block():
        with pytest.raises(OutboundSendViolation, match="real SMTP"):
            smtplib.SMTP("smtp.gmail.com", 587)


def test_send_urls_are_classified():
    assert is_outbound_send_url("https://api.sendgrid.com/v3/mail/send")
    assert is_outbound_send_url("https://api.twilio.com/2010-04-01/Accounts/AC/Messages.json")
    assert is_outbound_send_url("https://graph.facebook.com/v21.0/555/messages")
    assert not is_outbound_send_url("https://api.telegram.org/botx/getMe")
    assert not is_outbound_send_url("https://example.com/messages")


def test_create_ticket_without_email_mock_does_not_smtp(monkeypatch, tmp_path):
    """The bug: notify_new_ticket + live SMTP_* emailed Rafael from pytest."""
    root = tmp_path / "amp"
    root.mkdir()
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "100000")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_USER", "empirebox2026@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "would-have-been-real")
    monkeypatch.setenv("SMTP_FROM", "empirebox2026@gmail.com")
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()
    from app.services.family_help import create_ticket

    ticket = create_ticket(message="aviso sin mock de correo", notify=True)
    assert ticket["id"].startswith("fh-")
    # If the guard failed, SMTP("smtp.gmail.com") would have raised above.


def test_urllib_twilio_and_graph_tripwire():
    from urllib.request import urlopen

    with expect_outbound_block():
        with pytest.raises(OutboundSendViolation, match="urllib send"):
            urlopen("https://api.twilio.com/2010-04-01/Accounts/AC/Messages.json")
        with pytest.raises(OutboundSendViolation, match="urllib send"):
            urlopen("https://graph.facebook.com/v21.0/555/messages")
