"""Outbound MAX email recipients.

2026-10-08 (Rafael): Max's emails go ONLY to empirebox2026@gmail.com, with no
standing CC (the 2026-08-16 rafa22giraldo@gmail.com CC is retired). Reply-To
stays max@empirebox.store.
"""
from __future__ import annotations


def test_no_standing_cc():
    from app.services.max.tool_executor import DEFAULT_EMAIL_CC
    assert tuple(DEFAULT_EMAIL_CC) == ()


def test_default_reply_to_constant():
    from app.services.max.tool_executor import DEFAULT_REPLY_TO
    assert DEFAULT_REPLY_TO == "max@empirebox.store"


def test_merge_adds_nothing_when_no_cc():
    from app.services.max.tool_executor import _merge_standing_email_cc
    assert _merge_standing_email_cc("empirebox2026@gmail.com", None) == []
    assert _merge_standing_email_cc("empirebox2026@gmail.com", "") == []


def test_merge_keeps_explicit_cc_only():
    from app.services.max.tool_executor import _merge_standing_email_cc
    assert _merge_standing_email_cc("empirebox2026@gmail.com", "a@x.com, A@x.com") == ["a@x.com", "A@x.com"]


def test_default_recipient_is_empirebox_only():
    from app.services.max.tool_executor import MAX_DOC_EMAIL_TO
    assert MAX_DOC_EMAIL_TO == "empirebox2026@gmail.com"
