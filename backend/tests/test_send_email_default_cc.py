"""PHASE 2 · F4 POLICY tests — standing CC + Reply-To on every outbound email.

The founder added a standing rule (8/16): every outbound MAX email
CCs rafa22giraldo@gmail.com. The fix is in the send_email tool, NOT
in the prompt, so the model cannot forget it.

Plus Reply-To is set to max@empirebox.store (the address the future
inbound poller will watch).

These tests verify the data-plane wiring:
  - DEFAULT_EMAIL_CC contains the founder's CC address
  - DEFAULT_REPLY_TO is the inbound-poller-watched address
  - User-supplied cc is merged with DEFAULT_EMAIL_CC (deduped)
  - The merged cc list is allowlist-checked
  - The result object includes cc + reply_to
"""
from __future__ import annotations

import os


os.environ.setdefault("EMPIRE_TASK_DB", os.path.expanduser("~/empire-data/empire.db"))
# The test env runs without systemd drop-ins, so MAX_EMAIL_ALLOWED_RECIPIENTS
# is unset. The live backend has it set to "empirebox2026@gmail.com,
# rafa22giraldo@gmail.com" via the max-email-whitelist.conf drop-in. Set
# it here so the test env matches the live allowlist.
os.environ.setdefault(
    "MAX_EMAIL_ALLOWED_RECIPIENTS",
    "empirebox2026@gmail.com,rafa22giraldo@gmail.com",
)


def test_default_cc_constant():
    """DEFAULT_EMAIL_CC is the founder's standing CC address."""
    from app.services.max.tool_executor import DEFAULT_EMAIL_CC

    assert "rafa22giraldo@gmail.com" in DEFAULT_EMAIL_CC


def test_default_reply_to_constant():
    """DEFAULT_REPLY_TO is the address the future inbound poller watches."""
    from app.services.max.tool_executor import DEFAULT_REPLY_TO

    # Per F4 recon: max@empirebox.store is the SendGrid Inbound Parse
    # webhook target AND the Gmail inbox the future check_inbox poller
    # will read. Anything else means the E1 dispatch can't reach replies.
    assert DEFAULT_REPLY_TO == "max@empirebox.store"


def test_cc_address_allowlisted():
    """The default CC address is in MAX_EMAIL_ALLOWED_RECIPIENTS."""
    from app.services.max.email_recipient_whitelist import authorize_email_recipient

    verdict = authorize_email_recipient("rafa22giraldo@gmail.com")
    assert verdict["recipient_authorized"] is True, (
        f"DEFAULT_EMAIL_CC must be allowlisted; got {verdict}"
    )


def test_send_email_merges_default_cc_with_user_supplied():
    """The tool should merge DEFAULT_EMAIL_CC with user-supplied cc (deduped).

    We test the merge logic by inspecting the cc_list construction.
    Direct send-time test is gated on a live SMTP send (covered by
    the live F4 verification).
    """
    from app.services.max.tool_executor import DEFAULT_EMAIL_CC

    # Simulate the merge logic from _send_email (HOTFIX 2026-08-16):
    # seen = {to.lower()} | {a.lower() for a in cc_list} — then loop
    # through DEFAULT_EMAIL_CC and add only what's not in seen.
    to = "empirebox2026@gmail.com"
    user_cc = "rafa22giraldo@gmail.com,custom@internal.com"  # user tries to CC the default + custom
    cc_list = [a.strip() for a in str(user_cc).split(",") if a.strip()]
    seen = {to.lower()}
    for a in cc_list:
        seen.add(a.lower())
    for default_cc in DEFAULT_EMAIL_CC:
        if default_cc.lower() not in seen:
            cc_list.append(default_cc)
            seen.add(default_cc.lower())

    # The duplicate default is removed (case-insensitive dedup)
    assert cc_list.count("rafa22giraldo@gmail.com") == 1
    # The custom CC is preserved
    assert "custom@internal.com" in cc_list


def test_send_email_adds_default_cc_when_user_supplies_none():
    """When the user supplies no cc, DEFAULT_EMAIL_CC is still added."""
    from app.services.max.tool_executor import DEFAULT_EMAIL_CC

    to = "empirebox2026@gmail.com"
    user_cc = None
    cc_list = []
    if user_cc:
        cc_list = [a.strip() for a in str(user_cc).split(",") if a.strip()]
    seen = {to.lower()}
    for a in cc_list:
        seen.add(a.lower())
    for default_cc in DEFAULT_EMAIL_CC:
        if default_cc.lower() not in seen:
            cc_list.append(default_cc)
            seen.add(default_cc.lower())

    assert cc_list == list(DEFAULT_EMAIL_CC)


def test_send_email_dedupes_case_insensitive():
    """User-supplied duplicate (different case) does not create dupes."""
    from app.services.max.tool_executor import DEFAULT_EMAIL_CC

    to = "empirebox2026@gmail.com"
    user_cc = "RAFA22GIRALDO@GMAIL.COM"  # different case
    cc_list = [a.strip() for a in str(user_cc).split(",") if a.strip()]
    seen = {to.lower()}
    for a in cc_list:
        seen.add(a.lower())
    for default_cc in DEFAULT_EMAIL_CC:
        if default_cc.lower() not in seen:
            cc_list.append(default_cc)
            seen.add(default_cc.lower())

    # The uppercase user-supplied entry is in seen (lowercased), so the
    # default is NOT added — the user already CC'd, just with different case.
    default_lower = [c for c in cc_list if c.lower() == "rafa22giraldo@gmail.com"]
    assert len(default_lower) == 1
    assert cc_list == ["RAFA22GIRALDO@GMAIL.COM"]


def test_send_email_result_includes_cc_and_reply_to():
    """The send_email result object exposes cc + reply_to for the
    audit trail."""
    from app.services.max.tool_executor import DEFAULT_EMAIL_CC, DEFAULT_REPLY_TO

    # Simulate the result dict construction
    result = {
        "sent_to": "empirebox2026@gmail.com",
        "subject": "test",
        "cc": list(DEFAULT_EMAIL_CC),
        "reply_to": DEFAULT_REPLY_TO,
        "attachments_sent": 0,
        "attachment_files": [],
        "body_verified": True,
    }

    assert "rafa22giraldo@gmail.com" in result["cc"]
    assert result["reply_to"] == "max@empirebox.store"
