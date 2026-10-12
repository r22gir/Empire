"""Outbound audit for desk auto_execute.

Nothing customer-facing (email, invoice send, charge, publish, deploy)
runs without a founder tap. Auto-execute may draft, write internal
records, and notify the founder on Telegram.
"""
from __future__ import annotations

from app.services.max.scout_routing import RESTRICTED_ACTIONS

# Extra outbound verbs desks might use that are not already restricted.
EXTRA_OUTBOUND = frozenset({
    "publish",
    "publish_to_prod",
    "send_auto_response",
    "post_to_social",
    "schedule_public_post",
    "issue_pay_link",
    "deposit_pay_link",
})

OUTBOUND_ACTIONS = RESTRICTED_ACTIONS | EXTRA_OUTBOUND

# What auto_execute is allowed to do vs what must stay held.
# notify_founder = Telegram to Rafael (not a customer send).
DESK_AUTO_EXECUTE_AUDIT: dict[str, dict[str, tuple[str, ...]]] = {
    "forge": {
        "allowed": ("draft_quote", "lookup", "notify_founder"),
        "outbound": (),
    },
    "sales": {
        "allowed": ("draft_proposal", "notify_founder"),
        "outbound": ("send_customer_message",),
    },
    "support": {
        "allowed": ("draft_reply", "notify_founder"),
        "outbound": ("send_customer_message",),
    },
    "marketing": {
        "allowed": ("draft_post", "hashtag_research", "notify_founder"),
        "outbound": ("publish", "post_to_social", "schedule_public_post"),
    },
    "market": {
        "allowed": ("draft_listing", "notify_founder"),
        "outbound": ("publish",),
    },
    "finance": {
        "allowed": ("draft_invoice", "notify_founder"),
        "outbound": ("create_invoice", "send_invoice", "create_payment", "issue_pay_link"),
    },
    "clients": {
        "allowed": ("draft_note", "notify_founder"),
        "outbound": ("send_customer_message",),
    },
    "contractors": {
        "allowed": ("draft_dispatch", "notify_founder"),
        "outbound": ("send_customer_message",),
    },
    "it": {
        "allowed": ("health_check", "log_analysis", "notify_founder"),
        "outbound": ("deploy",),
    },
    "website": {
        "allowed": ("draft_copy", "seo_analysis", "notify_founder"),
        "outbound": ("publish",),
    },
    "legal": {
        "allowed": ("draft_policy", "notify_founder"),
        "outbound": ("approve_legal_text",),
    },
    "lab": {
        "allowed": ("prototype_note", "notify_founder"),
        "outbound": (),
    },
    "innovation": {
        "allowed": ("research_note", "notify_founder"),
        "outbound": (),
    },
    "analytics": {
        "allowed": ("metrics_report", "notify_founder"),
        "outbound": (),
    },
    "quality": {
        "allowed": ("audit_report", "notify_founder"),
        "outbound": (),
    },
    "intake": {
        "allowed": ("classify", "notify_founder"),
        "outbound": ("send_auto_response",),
    },
    "codeforge": {
        "allowed": ("draft_patch", "notify_founder"),
        "outbound": ("commit_code", "push_code", "deploy"),
    },
}


def is_outbound_action(action: str) -> bool:
    return (action or "").strip().lower() in OUTBOUND_ACTIONS


def auto_execute_may_run(action: str) -> bool:
    """True only for non-outbound actions (drafts / founder Telegram)."""
    return not is_outbound_action(action)
