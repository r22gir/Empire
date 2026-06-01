"""Guarded MAX email capability classification.

Determines what class of request an inbound email represents and whether
it can be handled automatically or requires founder approval.

Never sends email. Never enables auto-reply. Read-only classification.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Capability classes
# ---------------------------------------------------------------------------
CAPABILITY_ANSWER_ONLY = "answer_only"
CAPABILITY_RUNTIME_TRUTH = "runtime_truth"
CAPABILITY_WEB_SEARCH = "web_search_needed"
CAPABILITY_EMPIRE_ACTION = "empire_action_requires_approval"
CAPABILITY_OPENCLAW_TASK = "openclaw_task_requires_approval"
CAPABILITY_ATTACHMENT = "attachment_analysis_needed"
CAPABILITY_UNSAFE = "unsafe_or_blocked"


# ---------------------------------------------------------------------------
# Detection patterns — keep deterministic, not AI-dependent
# ---------------------------------------------------------------------------

_RUNTIME_TRUTH_SIGNALS = (
    "is openclaw online", "is openclaw healthy", "is openclaw running",
    "is hermes online", "is hermes running", "is hermes dashboard",
    "is the backend", "is the frontend", "is max online", "is max running",
    "what services are online", "service health", "services online",
    "what provider", "which model", "is minimax selected",
    "routing state", "model selector", "selected provider",
    "what commit", "current commit", "is the latest code",
    "is the site live", "are we live", "runtime status",
    "what's the status", "status check", "health check",
    "queue status", "is the queue", "worker status",
    "cron status", "is cron", "hermes cron",
)

_WEB_SEARCH_SIGNALS = (
    "search the web", "search for", "look up", "find information",
    "what is the latest", "current news", "recent news",
    "research", "find out about", "google", "look online",
    "what are the current", "what's happening with",
    "price check", "market price", "competitor",
    "trending", "breaking news", "news about",
)

_EMPIRE_ACTION_SIGNALS = (
    "create an invoice", "send invoice", "generate invoice",
    "create a quote", "send quote", "generate quote",
    "update customer", "update order", "update listing",
    "process refund", "issue refund", "cancel order",
    "workroom", "woodcraft", "send to workroom",
    "create shipment", "ship order", "send shipment",
    "update price", "change price", "price update",
    "update inventory", "change inventory",
    "send email to customer", "reply to customer",
    "process payment", "send payment",
)

_OPENCLAW_TASK_SIGNALS = (
    "create an openclaw task", "create openclaw task",
    "execute openclaw task", "run openclaw task",
    "create a task", "run a task", "execute task",
    "openclaw task", "delegate to openclaw",
    "fix this bug", "write code", "implement",
    "refactor", "deploy", "build a",
    "run the test", "run tests",
    "code review", "review this code",
)

_ATTACHMENT_SIGNALS = (
    "attached", "attachment", "see attached",
    "i've attached", "i have attached",
    "check the attached", "look at the attached",
    "pdf", "spreadsheet", "image attached",
    "photo attached", "file attached",
    "document attached", "screenshot",
)


def classify_email_capability(
    sender_authorized: bool,
    subject: str,
    body: str,
    has_attachments: bool = False,
) -> dict[str, Any]:
    """Classify an inbound email into a capability class.

    Args:
        sender_authorized: Whether the sender passed the allowlist check.
        subject: Email subject line.
        body: Email body text.
        has_attachments: Whether the email has file attachments.

    Returns a dict with:
        capability_class, allowed_now, requires_approval, tool_required,
        tool_available, blocker_reason, detection_method
    """
    result: dict[str, Any] = {
        "capability_class": CAPABILITY_UNSAFE,
        "allowed_now": False,
        "requires_approval": False,
        "tool_required": None,
        "tool_available": False,
        "blocker_reason": None,
        "detection_method": "default",
    }

    # 1. Unauthorized sender — block immediately
    if not sender_authorized:
        result["capability_class"] = CAPABILITY_UNSAFE
        result["blocker_reason"] = "sender_not_authorized"
        result["detection_method"] = "allowlist_check"
        return result

    # Normalize text for matching
    text = f"{subject or ''} {body or ''}".lower()
    text = " ".join(text.split())

    # 2. Attachment analysis
    if has_attachments or any(sig in text for sig in _ATTACHMENT_SIGNALS):
        result["capability_class"] = CAPABILITY_ATTACHMENT
        result["requires_approval"] = True
        result["tool_required"] = "attachment_read"
        result["tool_available"] = False  # requires real attachment parsing
        if not has_attachments:
            result["blocker_reason"] = "attachment_mentioned_but_not_provided"
        else:
            result["blocker_reason"] = "attachment_analysis_requires_approval"
        result["detection_method"] = "pattern_match"
        return result

    # 3. Runtime truth / health / status questions
    if any(sig in text for sig in _RUNTIME_TRUTH_SIGNALS):
        result["capability_class"] = CAPABILITY_RUNTIME_TRUTH
        result["allowed_now"] = True
        result["tool_required"] = "empire_runtime_truth_check"
        result["tool_available"] = True
        result["detection_method"] = "pattern_match"
        return result

    # 4. Web search / research / current events
    if any(sig in text for sig in _WEB_SEARCH_SIGNALS):
        result["capability_class"] = CAPABILITY_WEB_SEARCH
        result["requires_approval"] = True
        result["tool_required"] = "web_search"
        result["tool_available"] = False  # email pipeline can't call web yet
        result["blocker_reason"] = "web_search_not_available_in_email_pipeline"
        result["detection_method"] = "pattern_match"
        return result

    # 5. Empire action (invoice, quote, customer, Workroom, etc.)
    if any(sig in text for sig in _EMPIRE_ACTION_SIGNALS):
        result["capability_class"] = CAPABILITY_EMPIRE_ACTION
        result["requires_approval"] = True
        result["tool_required"] = "empire_action_tool"
        result["tool_available"] = False  # no execution without approval
        result["blocker_reason"] = "empire_action_requires_explicit_founder_approval"
        result["detection_method"] = "pattern_match"
        return result

    # 6. OpenClaw task creation/execution
    if any(sig in text for sig in _OPENCLAW_TASK_SIGNALS):
        result["capability_class"] = CAPABILITY_OPENCLAW_TASK
        result["requires_approval"] = True
        result["tool_required"] = "openclaw_task_dispatch"
        result["tool_available"] = False  # no task creation without approval + task ID
        result["blocker_reason"] = "openclaw_task_requires_explicit_founder_approval_and_task_id"
        result["detection_method"] = "pattern_match"
        return result

    # 7. Default: answer_only — safe question, can generate draft
    result["capability_class"] = CAPABILITY_ANSWER_ONLY
    result["allowed_now"] = True
    result["detection_method"] = "default_fallback"
    return result
