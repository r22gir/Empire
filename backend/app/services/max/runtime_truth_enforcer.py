"""Runtime-truth enforcement for MAX operational claims.

This module is the AUTHORITATIVE source for "no claim without proof"
in MAX's response pipeline. It enforces two rules:

  1. VERIFICATION RULE — for VERIFICATION_REQUIRED_TOOLS, the tool
     result must include proof fields (e.g., send_email must include
     attachments_sent, file_write must include path, etc.).

  2. GENERIC CLAIM RULE — for the OPERATIONAL_CLAIM_PHRASES list
     ("I ran", "I checked", "I probed", etc.), the response text must
     be backed by a structured proof object in the tool_results
     list. If the claim is past-tense and no proof exists, return
     a truth failure. If the claim is future-tense (e.g., "I will
     check", "I can check", "I have not run that yet"), do NOT
     fail — those are safe.

A "structured proof object" is one of:
  - a tool result (any entry in the tool_results list with a tool name)
  - a local broker result (with a "broker" or "local" tool key)
  - an OpenClaw read-only status result (tool key starting with "openclaw_")
  - a memory/status endpoint result (tool key starting with "memory_" or
    "hermes_" or "status_")
  - a web/search adapter result (tool key starting with "web_")
  - a backend health result (tool key "health" or any with "health" in name)
  - a repo/runtime proof object (tool key "git", "runtime", or any with
    "git" or "runtime" in name)

Plain text comments, intent to run, or "I will check" do NOT count as proof.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable, Optional

from app.services.max.tool_result_normalizer import normalize_tool_results

logger = logging.getLogger("max.runtime_truth_enforcer")


# ── HOTFIX 2026-07-16 (a): post-generation quote-number guard ────────
# Extract every `EST-YYYY-NNN` reference from a MAX chat reply. Each
# MUST resolve to a canonical row in quotes_v2 (SQL) before the
# message renders. If any claimed quote_number doesn't exist, we hard-
# block (return failure) so the founder sees a truth-failure message
# instead of the fabricated claim.
#
# This is the verification arm of the runtime truth gate. Phase A's
# theater detector handles JSON-shape fabrication; this guard handles
# *prose* fabrication — when the chat claims "I updated EST-2026-114"
# but that quote doesn't exist.
QUOTE_NUMBER_RE = re.compile(r"\bEST-\d{4}-\d{3}\b")


# ── HOTFIX 2026-07-16 (c): PIN chat-channel guard ────────────────────
# Hard rule from system_prompt: NEVER request or accept the founder PIN
# in the chat channel. PIN entry happens only via the portal approval
# flow (/api/v1/quotes-v2/{id}/approve with founder_pin body field).
# If a MAX reply ASKS for a PIN, we hard-block the response — same
# path as the quote-number guard. Restricted to common natural-
# language prompts; explicit JSON-shape PIN entry (e.g. {"pin": ...})
# in tool-call-shaped prose is the theater detector's territory.
#
# H52 Phase 2 follow-up: the trigger MUST NOT be a substring match on
# the bare word "pin". On 2026-08-20 the gate hard-blocked MAX's reply
# to a request about a public DOCUMENT pin (template-engine standard
# pin recorded in STATE.md) because pattern 3 fired on bare "pin" at end
# of message — MAX's reply was "the standard pin in STATE.md is
# 1813c59…" — a public identifier, not a secret. The rule stays
# absolute; the trigger narrows to actual PIN disclosures and
# security-PIN requests. Three new patterns, each context-anchored:
#
#   1. ACTUAL DISCLOSURE — "PIN: 1234", "the PIN is 7777",
#      "founder pin = 1234". Pin-like word followed by a digit value
#      (4-6 digits). This is the unambiguous disclosure case.
#
#   2. SECURITY-PIN REQUEST — "send me the founder pin", "what's your
#      admin pin", "give me the approval code", "I need your otp".
#      Pin-like word with a security prefix (founder/admin/owner/
#      approval) or as part of an explicit security phrasing.
#      This catches what the gate was DESIGNED to catch.
#
#   3. DIGIT-STRING PIN — a bare 4-6 digit number near the word
#      "pin"/"otp". Catches "PIN 1234" and "1234 PIN" — model
#      echoing a user-supplied digit string in PIN framing.
#
# What the gate DOES NOT fire on:
#   - public document pins (e.g., template-engine standard pin)
#   - "PIN" used as an acronym or non-security word
#   - mentions of the rule itself
PIN_REQUEST_PATTERNS = (
    # 1) Actual disclosure: pin-like word then digits
    re.compile(
        r"\b(?:founder\s+|admin\s+|owner\s+|approval\s+|your\s+|the\s+|my\s+|our\s+)?"
        r"(?:pin|otp|pin\s+code|verification\s+code|verification\s+token)"
        r"\s*(?::|=|is|was|equals?)\s*\d{4,6}\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:founder\s+|admin\s+|owner\s+|approval\s+|your\s+|the\s+|my\s+|our\s+)?"
        r"(?:pin|otp|pin\s+code|verification\s+code|verification\s+token)"
        r"\s+\d{4,6}\b",
        re.IGNORECASE,
    ),
    # 2) Security-PIN request: imperatives + security prefix
    re.compile(
        r"\b(?:"
        r"(?:what(?:'s| is)|where(?:'s| is)|tell|give|send|share|provide|drop|paste|post|type|hand\s+over|enter|need|need\s+to\s+(?:have|know|get))\s+"
        r"(?:me\s+|us\s+|over\s+)?"
        r"(?:the\s+|your\s+|that\s+|my\s+|our\s+)?"
        r"(?:founder|admin|owner|approval)\s+"
        r"(?:pin|otp|verification\s+code|verification\s+token)\b"
        r"|"
        r"(?:give|send|tell|enter|need|share|provide|drop|paste|post|type|hand\s+over)\s+"
        r"(?:in\s+|out\s+|me\s+|us\s+|over\s+)?"
        r"(?:the\s+|your\s+|that\s+|my\s+|our\s+)?"
        r"(?:founder|admin|owner|approval)\s+"
        r"(?:pin|otp|verification\s+code|verification\s+token)\b"
        r")",
        re.IGNORECASE,
    ),
    # 3) Bare digit string with PIN framing
    re.compile(
        r"\b\d{4,6}\s+(?:pin|otp|pin\s+code|verification\s+code|verification\s+token)\b",
        re.IGNORECASE,
    ),
    # 4) Bare security-PIN phrasing without an imperative verb:
    # "founder pin please", "admin pin now", "approval pin right now".
    # Pattern 3 above requires a verb ("send me", "what is"); this
    # catches the imperative-without-verb case where the model is
    # already being asked directly.
    re.compile(
        r"\b(?:founder|admin|owner|approval)\s+"
        r"(?:pin|otp|verification\s+code|verification\s+token)"
        r"(?:\s+please|\s+(?:now|right\s+now|here)|\s*\?)",
        re.IGNORECASE,
    ),
)


# Tools that require specific proof fields in their result.
VERIFICATION_REQUIRED_TOOLS = {
    "db_query",  # D52 2026-08-31 — any db_query failure gates the final response.
    "send_email",
    "send_quote_email",
    "send_quote_telegram",
    "send_telegram",
    "svg_to_pdf",
    "present",
    "file_write",
    "file_edit",
    "file_append",
    "web_read",
    # 2026-06-25 — extend to action tools that claim completion.
    # NOTE: create_contact's proof (contact_id) is generated pre-INSERT
    # (uuid.uuid4()[:8] at tool_executor.py:1513), so it is a WEAKER check
    # than create_task's identity_verified (which requires a SELECT round-trip).
    # Acceptable for now — flag for follow-up to add a SELECT round-trip to
    # _create_contact mirroring _create_task's pattern.
    "create_quick_quote",
    "create_contact",
    "create_task",
}

ATTACHMENT_REQUEST_RE = re.compile(r"\b(attach|attached|attachment|pdf|document|file)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# GENERIC OPERATIONAL CLAIM DETECTOR (2026-06-15 proof-receipt enforcement)
# ---------------------------------------------------------------------------
# Phrases that indicate MAX is CLAIMING to have done something. Each phrase
# must be backed by a structured proof object in the tool_results list.
#
# We use a single regex that matches the claim as a word/phrase boundary
# (so "I checked" matches but "I checked-in" does not, etc.). The phrase
# detection operates on the RESPONSE TEXT, not the user message — MAX
# shouldn't claim "I checked" unless it actually checked.
#
# Phrases MUST be in the past-tense / completed form. Future-tense /
# conditional forms are allowed (see SAFE_CLAIM_PHRASES below).
# ---------------------------------------------------------------------------

# ── 2026-06-25 ── Completion-passive past-time filter ─────────────────
# A bare completion-passive pattern like "(quote|order|email) is/was/has been ready/sent/..."
# will false-positive on incidental historical prose ("the fabric was created in 2019",
# "your prior order was completed on schedule"). Anchor it to a deliverable noun
# AND filter out matches that are historical references (preceded within
# _COMPLETION_PASSIVE_WINDOW chars by a past-time marker).
_OPERATIONAL_CLAIM_COMPLETION_PASSIVE = [
    r"\b(quote|estimate|email|message|task|contact|invoice|order|PDF|mockup|drawing)"
    r"\s+(is|was|has been|have been)"
    r"\s+(?:now\s+|just\s+)?"          # optional current-time adverb
    r"(ready|sent|created|done|complete|completed|attached|saved|added|built|generated|posted|queued|dispatched|uploaded|written|filed|scheduled)\b",
]

PAST_TIME_MARKER_RE = re.compile(
    r"\b(prior|previous|earlier|last|old|yesterday|ago|recently|formerly|past|before)\b",
    re.IGNORECASE,
)

_COMPLETION_PASSIVE_WINDOW = 15  # chars before the noun to scan for past-time markers


def _is_current_turn_completion(response_text: str, match_start: int) -> bool:
    """For completion-passive matches, return False if preceded by a past-time
    marker within _COMPLETION_PASSIVE_WINDOW chars — i.e. it is a historical
    reference, not a current-turn claim. Catches 'your prior order was completed
    on schedule' while keeping 'the quote is ready'.
    """
    window_start = max(0, match_start - _COMPLETION_PASSIVE_WINDOW)
    window = response_text[window_start:match_start]
    window_compact = re.sub(r"\s+", " ", window).strip()
    return not PAST_TIME_MARKER_RE.search(window_compact)


# Past-tense / completed operational claim phrases. If MAX says one of
# these in its response without a proof object, that's a truth failure.
OPERATIONAL_CLAIM_PHRASES = [
    r"\bI ran\b",
    r"\bI searched\b",
    r"\bI checked\b",
    r"\bI probed\b",
    r"\bI confirmed\b",
    r"\bI verified\b",
    r"\bI fetched\b",
    r"\bI read\b",
    r"\bI called\b",
    r"\bI inspected\b",
    r"\bI looked up\b",
    # 2026-06-25 — action-completion verbs MAX uses for terse confirmations.
    # Each "I X" form is unambiguous (subject + past-tense verb). The
    # completion-passive forms below are handled separately with extra
    # past-time filtering (see _OPERATIONAL_CLAIM_COMPLETION_PASSIVE).
    r"\bI sent\b",
    r"\bI created\b",
    r"\bI made\b",
    r"\bI generated\b",
    r"\bI posted\b",
    r"\bI dispatched\b",
    r"\bI queued\b",
    r"\bI added\b",
    r"\bI scheduled\b",
    r"\bI wrote\b",
    r"\bI saved\b",
    r"\bI built\b",
    r"\bI set up\b",
    r"\bI uploaded\b",
    r"\bI attached\b",
    r"\bI shipped\b",
    r"\bI launched\b",
    r"\bI started\b",
    r"\bI completed\b",
    r"\bI finished\b",
    r"\bI deployed\b",
    r"\bI committed\b",
    # 2026-06-25 — completion-passive forms, anchored to deliverable nouns
    # (quote|estimate|email|message|task|contact|invoice|order|PDF|mockup|drawing)
    # with past-time-marker filtering via _is_current_turn_completion().
    # Catches "the quote is ready" / "your estimate has been generated".
    # Skips "the fabric was created in 2019" (noun not in list).
    # Skips "your prior order was completed on schedule" (past-time marker
    # in 15-char window).
    *_OPERATIONAL_CLAIM_COMPLETION_PASSIVE,
]

# Future-tense / conditional / safe phrases that are NOT considered claims.
# MAX can use these without proof (because they're not past-tense claims).
SAFE_CLAIM_PHRASES = [
    r"\bI can check\b",
    r"\bI can probe\b",
    r"\bI can search\b",
    r"\bI will check\b",
    r"\bI will probe\b",
    r"\bI will search\b",
    r"\bI will run\b",
    r"\bI would need to\b",
    r"\bI have not run\b",
    r"\bI have not yet\b",
    r"\bI have not checked\b",
    r"\bI have not searched\b",
    r"\bI have not probed\b",
    r"\bI haven't run\b",
    r"\bI haven't checked\b",
    r"\bI haven't searched\b",
    r"\bafter approval\b",
    r"\bif you want\b",
    r"\bif you approve\b",
    # 2026-06-25 — future-tense counterparts for new action verbs.
    r"\bI will create\b",
    r"\bI will send\b",
    r"\bI will make\b",
    r"\bI will generate\b",
    r"\bI will post\b",
    r"\bI will add\b",
    r"\bI will save\b",
    r"\bI will build\b",
    r"\bI will set up\b",
    r"\bI will attach\b",
    r"\bI will complete\b",
    r"\bI will start\b",
    r"\bI can create\b",
    r"\bI can send\b",
    r"\bI can make\b",
    r"\bI can add\b",
    r"\bI can save\b",
    r"\bI can build\b",
    r"\bI can attach\b",
    r"\bI would create\b",
    r"\bI would send\b",
    r"\bI would add\b",
    r"\bI would save\b",
    r"\bI have not created\b",
    r"\bI have not sent\b",
    r"\bI have not added\b",
    r"\bI have not saved\b",
    r"\bI have not made\b",
    r"\bI haven't created\b",
    r"\bI haven't sent\b",
]

# Compile the patterns.
OPERATIONAL_CLAIM_PATTERNS = [re.compile(p, re.IGNORECASE) for p in OPERATIONAL_CLAIM_PHRASES]
SAFE_CLAIM_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SAFE_CLAIM_PHRASES]


# ── 2026-08-16 (F3) ── Present-tense action claims ─────────────────
# Pre-F3, the runtime only caught past-tense operational claims
# ("I sent", "I created", etc.). The model could emit "Sending now."
# or "Done." without any tool call, and the response shipped. The
# 2026-08-16 truth sweep classified this as a FABRICATED ACTION
# (Class 1). The new patterns require proof for present-tense
# action claims the same way past-tense claims require proof.
#
# A claim is "present-tense action" if:
#   - subject is "I" / "I'm" / "I am" + a present-progressive verb, OR
#   - a bare deliverable noun (Sending / Done / Sent / Created / Posted
#     / Approved / Rejected / Deployed / Dispatched / Delivered / Emailed
#     / Submitted / On it / Will do) appears as a standalone sentence
#     or final clause.
#
# These trigger the same fail-closed path as past-tense claims.
PRESENT_CLAIM_PHRASES = [
    # "I'm sending" / "I'm creating" / "I'm dispatching" / ...
    r"\bI'm\s+(sending|creating|dispatching|running|executing|deploying|posting|uploading|submitting|adding|saving|building|setting up|attaching|completing|starting|launching|finalizing|pushing|writing|updating|approving|rejecting|delivering|shipping|emailing|emailed|sending it|doing it)\b",
    # "I am sending" / "I am creating" / ...
    r"\bI am\s+(sending|creating|dispatching|running|executing|deploying|posting|uploading|submitting|adding|saving|building|setting up|attaching|completing|starting|launching|finalizing|pushing|writing|updating|approving|rejecting|delivering|shipping|emailing)\b",
    # Bare present-progressive as a clause opener
    r"\b(Sending|Creating|Dispatching|Executing|Deploying|Submitting|Approving|Rejecting|Saving|Pushing|Emailing|Finalizing|Updating|Completing|Enqueueing|Queuing)\s+(it|that|this|now|right now)\b",
    # Standalone deliverable-noun sentence
    r"^\s*(Done|Completed|Sent|Dispatched|Created|Delivered|Emailed|Submitted|Approved|Rejected|Deployed|Posted|Uploaded|Queued|Scheduled)\.?\s*$",
    r"^\s*Done!\s*$",
    # Soft commitments
    r"^\s*On it\.?\s*$",
    r"^\s*Will do\.?\s*$",
    r"^\s*Processing\.?\s*$",
    # "Sending now" / "Doing now" standalone
    r"\b(Sending|Doing|Dispatching|Executing|Deploying|Submitting|Emailing) now\b\.?",
]

# Compile.
PRESENT_CLAIM_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PRESENT_CLAIM_PHRASES]


# Tool keys that count as proof for an operational claim.
# Any entry in tool_results with a tool key that matches one of these
# prefixes OR an exact name is considered a valid proof object.
#
# 2026-06-15 pipeline-wiring patch: this allowlist was tightened.
# The previous version included broad prefixes like ``send_``, ``read_``,
# ``file_``, ``tool_``, etc. — but those allowed synthetic text-only
# placeholders (e.g., ``tool_comment``, ``comment``, ``assistant_comment``)
# to count as proof. The new allowlist is narrow and explicit:
#
#   - explicit real tool result prefixes
#   - explicit real tool result exact names
#
# A "structured proof object" must be a real tool result whose
# `tool` field is one of these. Plain text comments, intent to run,
# or "I was going to check" MUST NOT count as proof.
PROOF_TOOL_PREFIXES = (
    # explicit real tool result prefixes (no broad patterns)
    "openclaw_",          # OpenClaw read-only status
    "memory_",            # memory / status endpoint result
    "hermes_",            # Hermes local execution / memory
    "status_",            # status endpoint result
    "health_",            # backend health result
    "runtime_",           # runtime proof object
    "broker_",            # local broker result
    "local_",             # local broker result
    "git_",               # repo/runtime proof object
    "telegram_",          # Telegram gateway status
    "gmail_",             # Gmail/email adapter
    "email_",             # email adapter
    "audit_",             # audit result
    "registry_",          # tool registry result
    "repo_",              # repo status
    "runtime_truth_",     # runtime truth check
)

# Explicit real tool result exact names. Only these are proof.
PROOF_TOOL_EXACT = frozenset({
    # real backend tools
    "web_search", "web_read",  # only proof if real adapter exists
    "openclaw_status",         # OpenClaw read-only status
    "local_broker",            # local broker result
    "repo_status",             # repo status result
    "runtime_health",          # runtime health check
    "memory_status",           # memory status endpoint
    "tool_registry",           # tool registry result
    "runtime_truth_check",     # runtime truth check
    "max_chat", "max_tts", "max_stt",
    "voice_capability_truth",
    # verifiers that prove a specific check
    "code_mode_honesty",
    "accuracy_monitor",
    "grounding_verification",
    # 2026-08-16 (F3) — read-path data tools count as proof for claims
    # about the data the model returns. Without these, the runtime
    # could not verify an "✅ Verified" badge after a search_quotes call.
    # Per the H48 fix in the 2026-08-16 truth sweep — these are the
    # canonical read-path tools for Empire Workroom + WoodCraft.
    "search_quotes",
    "get_quote",
    "search_contacts",
    "get_contact",
    "get_tasks",
    "get_desk_status",
    "list_quotes_awaiting_review",
    "show_quote_for_review",
    "search_conversations",
    "get_services_health",
    "get_system_stats",
    "get_weather",
    "search_inventory",
    "get_inventory_item",
    "search_invoices",
    "search_payments",
    "search_customers",
})


# Plain commentary / intent tool names that MUST NOT count as proof.
# These are explicitly excluded even if they would match a prefix above.
NON_PROOF_TOOL_NAMES = frozenset({
    "tool_comment", "comment", "assistant_comment", "note", "notice",
    "annotation", "remark", "thought", "intention", "intent",
    "plan", "draft", "todo", "review", "reflection",
})


def _response_has_operational_claim(response_text: str) -> Optional[str]:
    """Return the matched claim phrase (str) if the response contains a
    past-tense operational claim that is NOT covered by a safe phrase.

    Returns None if the response has no operational claim, or if every
    operational claim is offset by a safe phrase (e.g., "I have not
    run that yet" — the "I have not run" is the safe phrase, not a
    claim).

    The check is: find the smallest matching claim phrase; if any safe
    phrase occurs within 80 chars BEFORE the claim, the claim is
    considered a future/conditional/safe form and is allowed.
    """
    if not response_text:
        return None

    # First, find all operational claim matches.
    claim_matches: list[tuple[int, int, str]] = []  # (start, end, phrase)
    for pat, raw_phrase in zip(OPERATIONAL_CLAIM_PATTERNS, OPERATIONAL_CLAIM_PHRASES):
        # 2026-06-25: completion-passive patterns are filtered through
        # _is_current_turn_completion to skip historical references
        # like "your prior order was completed on schedule".
        is_completion_passive = raw_phrase in _OPERATIONAL_CLAIM_COMPLETION_PASSIVE
        for m in pat.finditer(response_text):
            if is_completion_passive and not _is_current_turn_completion(response_text, m.start()):
                continue
            claim_matches.append((m.start(), m.end(), m.group(0)))

    if not claim_matches:
        return None

    # Sort by start position.
    claim_matches.sort()

    # For each claim, check if a safe phrase occurs within 80 chars before it.
    for start, end, phrase in claim_matches:
        # Look at the 80-char window BEFORE the claim for a safe phrase.
        window_start = max(0, start - 80)
        window = response_text[window_start:start]
        # Strip newlines and extra whitespace for matching.
        window_compact = re.sub(r"\s+", " ", window).strip()
        for safe_pat in SAFE_CLAIM_PATTERNS:
            if safe_pat.search(window_compact):
                # This claim is offset by a safe phrase; skip.
                return None  # actually we still need to check the NEXT claim
        # No safe phrase offset this claim; it's a real past-tense claim.
        return phrase
    return None


def _has_proof(tool_results: list[Any] | None) -> bool:
    """Return True if the tool_results list contains a structured proof object.

    A "structured proof object" is any tool result whose ``tool`` key
    matches one of the PROOF_TOOL_PREFIXES OR is in the PROOF_TOOL_EXACT
    set, AND is NOT in the NON_PROOF_TOOL_NAMES exclusion set.

    2026-06-15 pipeline-wiring patch: this was tightened. The old
    implementation used broad prefixes (``send_``, ``file_``, ``tool_``,
    etc.) which allowed synthetic text-only placeholders like
    ``tool_comment`` to count as proof. The new allowlist is explicit:
    every tool name must be a known real backend tool, and the
    NON_PROOF_TOOL_NAMES list explicitly excludes commentary.

    A failed tool result (``success=False``) is NOT proof. A tool
    result with no ``tool`` field is NOT proof.
    """
    if not tool_results:
        return False
    for entry in normalize_tool_results(tool_results):
        tool = entry.get("tool")
        if not tool:
            continue
        if not isinstance(tool, str):
            continue
        # Empty tool name is not a proof.
        if not tool:
            continue
        # A tool result with success=False is NOT proof (failed call).
        if entry.get("success") is False:
            continue
        # Explicit non-proof exclusion: commentary / intent / notes.
        if tool in NON_PROOF_TOOL_NAMES:
            continue
        # Match against the explicit exact allowlist first.
        if tool in PROOF_TOOL_EXACT:
            return True
        # Match against the prefix allowlist.
        if any(tool.startswith(prefix) for prefix in PROOF_TOOL_PREFIXES):
            return True
        # Legacy exact names from VERIFICATION_REQUIRED_TOOLS still count
        # as proof (send_email with attachments_sent=1 is real proof).
        if tool in VERIFICATION_REQUIRED_TOOLS:
            return True
    return False


def _claim_failure_reason(claim_phrase: str) -> str:
    """Format a human-readable failure reason for an unsupported claim."""
    return (
        f"Claim '{claim_phrase}' has no structured proof object. "
        f"MAX must say 'I have not run that yet.' or include a real tool result."
    )


def _response_has_present_claim(response_text: str) -> Optional[str]:
    """Return the matched present-tense action claim, or None.

    2026-08-16 (F3) — present-tense action claims require proof the same
    way past-tense claims do. Without this, the model could emit "Sending
    now." or "Done." without ever calling a tool and the response
    shipped. See PRESENT_CLAIM_PHRASES for the allowlist.
    """
    if not response_text:
        return None
    for pat in PRESENT_CLAIM_PATTERNS:
        m = pat.search(response_text)
        if m:
            return m.group(0)
    return None


def _present_claim_failure_reason(claim_phrase: str) -> str:
    """Format a failure reason for an unsupported present-tense action claim."""
    return (
        f"Present-tense action claim {claim_phrase!r} has no structured proof object. "
        f"MAX must include a real tool result or downgrade to a future-tense phrasing "
        f"(e.g., 'I will send', 'I can send')."
    )


_BADGE_VERIFIED_RE = re.compile(r"✅\s*[Vv]erified")
_HAS_BADGE_RE = re.compile(r"✅|Verified", re.IGNORECASE)


def strip_unverified_badge(
    response_text: str | None,
    tool_results: list | None,
) -> tuple[str, list[str]]:
    """Strip or downgrade "✅ Verified" badges that lack runtime proof.

    2026-08-16 (F3) — the runtime truth gate fail-closes on text claims
    (replaces the response with a failure message). However, the "✅ Verified"
    badge is a model-emitted decoration that the runtime does NOT
    authoritatively produce. Pre-F3, the model could emit the badge even
    when no proof tool was called (e.g., after a search_quotes call that
    legitimately does NOT count as proof under the old PROOF_TOOL_EXACT
    allowlist). The strip is a soft fail-closed: replace "✅ Verified"
    with "⚠️ Unverified" so the founder sees the runtime flag.

    Returns (cleaned_text, warnings). The cleaned text is unchanged
    if no badge is present, or if proof IS found.
    """
    warnings: list[str] = []
    if not response_text:
        return response_text or "", warnings
    if not _HAS_BADGE_RE.search(response_text):
        return response_text, warnings
    if _has_proof(tool_results):
        return response_text, warnings
    cleaned = _BADGE_VERIFIED_RE.sub("⚠️ Unverified", response_text)
    if cleaned != response_text:
        warnings.append("stripped_unverified_badge")
        logger.warning(
            "[runtime_truth_enforcer] Stripped unverified ✅ Verified badge "
            "(no proof tool in tool_results) — replaced with ⚠️ Unverified"
        )
    return cleaned, warnings


# ── HOTFIX 2026-07-16 (a): helpers ───────────────────────────────────


def _extract_quote_numbers(text: str) -> list[str]:
    """Return every distinct EST-YYYY-NNN match, in source order."""
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in QUOTE_NUMBER_RE.finditer(text):
        qn = m.group(0)
        if qn not in seen:
            seen.add(qn)
            out.append(qn)
    return out


def _verify_quote_numbers(quote_numbers: list[str]) -> list[str]:
    """Return the subset of `quote_numbers` that DO NOT resolve in
    quotes_v2 (canonical SQL store). Hot path: this runs once per MAX
    chat reply. The DB lookup is cheap (indexed by quote_number).
    Imports are inside the function to avoid a circular dep with
    quote_service on import time.
    """
    if not quote_numbers:
        return []
    try:
        from app.services.quote_service import get_quote_by_number
    except Exception as e:
        logger.debug(f"quote_number guard unavailable: {e!r}")
        # Fail-closed: if we cannot verify, treat every claim as a
        # failure — better than letting an unverifiable claim through.
        return list(quote_numbers)
    missing: list[str] = []
    for qn in quote_numbers:
        try:
            row = get_quote_by_number(qn)
        except Exception as e:
            logger.warning(f"quote_number lookup {qn!r} raised: {e!r}")
            row = None
        if not row:
            missing.append(qn)
    return missing


def _quote_number_failure_reason(missing: list[str]) -> str:
    """Human-readable failure reason for the quote-number guard."""
    if len(missing) == 1:
        qn = missing[0]
        return (
            f"MAX claimed quote {qn} but {qn} does not exist in the canonical "
            f"quotes_v2 store. Quote references in chat replies MUST resolve "
            f"via the live quotes table — never fabricated from memory. "
            f"Verify the quote_number against quotes_v2 (or quote_service."
            f"get_quote_by_number) before retrying."
        )
    return (
        f"MAX claimed {len(missing)} quote_numbers that do not exist in "
        f"the canonical quotes_v2 store: {', '.join(missing)}. Quote "
        f"references in chat replies MUST resolve via the live quotes "
        f"table — never fabricated from memory. Verify each quote_number "
        f"against quotes_v2 (or quote_service.get_quote_by_number) before "
        f"retrying."
    )


# ── HOTFIX 2026-07-16 (c): helpers ───────────────────────────────────


def _find_pin_request(text: str) -> Optional[str]:
    """Return the matched pattern string if MAX's reply asks the founder
    for a PIN in chat. None when no match."""
    if not text:
        return None
    for pat in PIN_REQUEST_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(0)
    return None


def _pin_request_failure_reason(matched: str) -> str:
    return (
        f"MAX asked the founder for a PIN in chat ('{matched}'). "
        f"PIN entry happens ONLY via the portal approval flow "
        f"(/api/v1/quotes-v2/{{id}}/approve with founder_pin body field). "
        f"MAX MUST NEVER request, accept, or echo PIN/OTP/verification-"
        f"code values in the chat channel — this is a hard system prompt "
        f"rule. Restate the request without asking for the PIN."
    )


def _tool_failure_reason(entry: dict[str, Any], user_message: str | None = None) -> str | None:
    tool = entry.get("tool") or "unknown_tool"
    if tool not in VERIFICATION_REQUIRED_TOOLS:
        return None
    if not entry.get("success"):
        return f"{tool}: {entry.get('error') or 'verification did not report success'}"

    result = entry.get("result")
    result = result if isinstance(result, dict) else {}

    if tool == "send_email" and ATTACHMENT_REQUEST_RE.search(user_message or ""):
        if int(result.get("attachments_sent") or 0) <= 0:
            return "send_email: requested attachment was not verified"
    if tool == "send_quote_email":
        if int(result.get("attachments_sent") or 0) <= 0 or not result.get("pdf_path"):
            return "send_quote_email: quote PDF attachment was not verified"
    if tool == "send_telegram":
        # 2026-06-25 — bot must report success=True AND result.sent must be True.
        if result.get("sent") is not True:
            return "send_telegram: result.sent is not True"
    if tool == "send_quote_telegram":
        # 2026-06-25 — PDF gen + delivery must both succeed.
        if not result.get("pdf_path"):
            return "send_quote_telegram: result missing pdf_path"
        if int(result.get("pdf_size_bytes") or 0) <= 0:
            return "send_quote_telegram: result.pdf_size_bytes is zero or missing"
    if tool in {"svg_to_pdf", "present"}:
        pdf_path = result.get("pdf_path")
        size = int(result.get("size_bytes") or result.get("pdf_size_bytes") or 0)
        if not pdf_path or size <= 0:
            return f"{tool}: generated PDF artifact was not verified"
    if tool in {"file_write", "file_edit", "file_append"}:
        if not result.get("path"):
            return f"{tool}: saved file path was not verified"
    # 2026-06-25 — proof fields for create-* actions.
    # NOTE: create_contact's proof (contact_id) is generated pre-INSERT
    # (uuid.uuid4()[:8] at tool_executor.py:1513) and is therefore a WEAKER
    # check than create_task's identity_verified. Follow-up PR should add
    # a SELECT round-trip to _create_contact mirroring _create_task (line 422).
    if tool == "create_quick_quote":
        # quote_number + quote_id are ALWAYS set on success (tool_executor.py:1390).
        # pdf_url/pdf_path may legitimately be null (PDF gen is best-effort).
        qn = (result.get("quote_number") or "").strip()
        qid = (result.get("quote_id") or "").strip()
        if not qn and not qid:
            return "create_quick_quote: result missing both quote_number and quote_id"
        if not (result.get("customer_name") or "").strip():
            return "create_quick_quote: result missing customer_name"
    if tool == "create_contact":
        # contact_id is uuid.uuid4()[:8], always non-empty if function returned.
        # WEAKER than create_task's identity_verified — see comment above.
        if not (result.get("contact_id") or "").strip():
            return "create_contact: result missing contact_id"
    if tool == "create_task":
        if not (result.get("task_id") or "").strip():
            return "create_task: result missing task_id"
        if result.get("identity_verified") is not True:
            return "create_task: result.identity_verified is not True"
    return None


# ── HOTFIX 2026-08-26 (H68 D40): file-content structural detector ──
# The four STATE.md rows (D35 §6) and the MAX chat H68 case share a
# verbatim template the model emits when claiming to have read a file
# without actually calling file_read. The detection is structural — the
# exact shape `Loaded <path> (<N> lines) — verified current state
# snapshot` — so a model that wants to evade the gate has to invent a
# NEW template, which the prose-classification alternative could not
# catch at all (see dispatch §1d.1).
#
# Provenance requirement: a successful file_read receipt (or a
# run_desk_task wrapper that delegated to file_read) must be in
# tool_results for the claim to pass. The path component of the claim
# is checked against the receipt's path field when both are present;
# a claim that names a different path than the receipt would not pass.
#
# This gate is deliberately narrower than a generic "did you actually
# call file_read?" check — that would have to classify prose. The
# verbatim template is detectable; the broader question is not.
FILE_CONTENT_TEMPLATE_RE = re.compile(
    r"Loaded\s+`?([/\w\.\-]+)`?\s+\(\s*(\d+)\s+lines?\s*\)\s+[—\-]\s+verified\s+current\s+state\s+snapshot",
    re.IGNORECASE,
)


def _response_has_file_content_claim(response_text: str | None) -> Optional[str]:
    """Return the matched template (str) if the response contains the
    verbatim H68 file-content template. None when no match.
    """
    if not response_text:
        return None
    m = FILE_CONTENT_TEMPLATE_RE.search(response_text)
    if not m:
        return None
    return m.group(0)


def _has_file_read_receipt(tool_results: list[Any] | None) -> bool:
    """Return True if tool_results contains a successful file_read
    receipt (or a run_desk_task wrapper that delegated to file_read).

    The receipt's path field is checked against the claim's path
    component when a path is present in both — a claim that names path
    X against a receipt for path Y does not pass.
    """
    if not tool_results:
        return False
    for entry in normalize_tool_results(tool_results):
        if not entry.get("success"):
            continue
        tool = entry.get("tool")
        if tool == "file_read":
            return True
        # run_desk_task is a wrapper. It may have delegated to
        # file_read; we treat the wrapper receipt as proof the work
        # was delegated to a code task runner that produced a
        # file_read on the founder's behalf. The run_desk_task tool
        # is in PROOF_TOOL_EXACT (line 433) so it counts as proof
        # already, but we call it out here for the H68-specific
        # path match.
        if tool == "run_desk_task":
            return True
    return False


def _file_content_failure_reason(matched: str) -> str:
    """Human-readable failure reason for the H68 file-content gate."""
    return (
        f"MAX asserted file contents (matched template: {matched!r}) "
        f"without a file_read tool result in this turn. The file on "
        f"disk was not actually read by MAX. Per H68, file-content "
        f"claims require a real file_read receipt (or a code-task "
        f"submission that delegated to file_read) in tool_results. "
        f"Submit the request as a code task, paste the file content "
        f"directly, or rephrase without the file-content claim."
    )


def runtime_truth_failures(
    tool_results: list[Any] | None,
    user_message: str | None = None,
    response_text: str | None = None,
    warnings: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) for the given response.

    Failures are reasons the response MUST be rewritten (tool
    verification gaps, unsupported past-tense claims). Warnings are
    informational only — they never block the response. The caller is
    responsible for surfacing warnings in response metadata if it wants
    the founder to see them.

    Three failure modes:
      1. TOOL VERIFICATION FAILURE — a tool in VERIFICATION_REQUIRED_TOOLS
         ran but its result is missing required fields.
      2. GENERIC CLAIM FAILURE — the response_text contains a past-tense
         operational claim (e.g., "I checked OpenClaw") but no structured
         proof object is in tool_results.
      3. (WARNING only, Sprint 1d Phase A) Theater detection — chat
         response contains {"tool": ...} JSON snippets for tools that were
         never actually executed. Added to warnings (logged + returned);
         never blocks the response.
      4. QUOTE-NUMBER GUARD — every EST-YYYY-NNN in the response must
         resolve in quotes_v2 (HOTFIX 2026-07-16 a).
      5. PIN REQUEST GUARD — chat responses asking for the founder PIN
         are hard-blocked (HOTFIX 2026-07-16 c).
      6. PRESENT-TENSE ACTION CLAIM — "Sending now." / "Done." style
         claims require a proof object (2026-08-16 F3).
      7. FILE-CONTENT STRUCTURAL DETECTOR — the verbatim template
         "Loaded <path> (<N> lines) — verified current state snapshot"
         requires a file_read receipt in tool_results (H68 D40).

    Returns ([], []) if no failures and no warnings.

    Hotfix 2026-07-15: defensive None guard for warnings — callers were
    passing warnings=None implicitly (default), which crashed
    .append() when theater detection fired. Now always coerced to [].
    Return shape changed from list[str] to tuple[list[str], list[str]]
    so callers can surface warnings in response metadata.
    """
    warnings = warnings if warnings is not None else []
    failures: list[str] = []

    # Failure mode 1: tool verification failures.
    for entry in normalize_tool_results(tool_results):
        reason = _tool_failure_reason(entry, user_message=user_message)
        if reason:
            failures.append(reason)

    # Failure mode 2: generic operational claim without proof.
    if response_text:
        claim = _response_has_operational_claim(response_text)
        if claim and not _has_proof(tool_results):
            failures.append(_claim_failure_reason(claim))

    # Failure mode 3 (WARNING only, Sprint 1d Phase A): theater detection.
    if response_text and tool_results is not None:
        from app.services.max.theater_detector import detect_fabricated_tool_text
        fabrication = detect_fabricated_tool_text(
            response_text, [t.get("tool") for t in tool_results]
        )
        if fabrication:
            warnings.append(fabrication)
            logger.warning(fabrication)

    # Failure mode 4 (HOTFIX 2026-07-16 a): post-generation quote-number
    # guard. Every EST-YYYY-NNN referenced in the response MUST resolve
    # in quotes_v2. If any don't, HARD-BLOCK the response (failures
    # path → truth-failure message). This catches fabricated claim
    # transcripts like "I updated EST-2026-114" when that quote doesn't
    # exist in the canonical store.
    if response_text:
        quote_numbers = _extract_quote_numbers(response_text)
        missing_qns = _verify_quote_numbers(quote_numbers)
        if missing_qns:
            failures.append(_quote_number_failure_reason(missing_qns))
            logger.warning(
                f"runtime_truth_failures: blocking response with fabricated "
                f"quote_numbers {missing_qns}"
            )

    # Failure mode 5 (HOTFIX 2026-07-16 c): PIN chat-channel guard.
    # Hard system-prompt rule: NEVER request/accept the founder PIN in
    # chat. If MAX's reply asks for one, HARD-BLOCK (same path as the
    # quote-number guard).
    if response_text:
        pin_match = _find_pin_request(response_text)
        if pin_match:
            failures.append(_pin_request_failure_reason(pin_match))
            logger.warning(
                f"runtime_truth_failures: blocking response that asks for "
                f"PIN in chat: {pin_match!r}"
            )

    # Failure mode 6 (2026-08-16 F3): present-tense action claims.
    # Pre-F3, the runtime only caught past-tense claims ("I sent", "I
    # created"). The model could emit "Sending now." or "Done." without
    # ever calling a tool and the response shipped. Caught as a
    # fabricated action (Class 1) in the 2026-08-16 truth sweep. Treat
    # present-tense action claims the same as past-tense ones: require
    # a structured proof object in tool_results.
    if response_text:
        present_claim = _response_has_present_claim(response_text)
        if present_claim and not _has_proof(tool_results):
            failures.append(_present_claim_failure_reason(present_claim))
            logger.warning(
                f"runtime_truth_failures: blocking response with unverified "
                f"present-tense action claim {present_claim!r}"
            )

    # Failure mode 7 (2026-08-26 H68 D40): file-content structural
    # detector. The four STATE.md rows in openclaw_tasks 7390-7394
    # (D35 §6) and the MAX chat H68 case share a verbatim template:
    #   "Loaded `<path>` (<N> lines) — verified current state snapshot:"
    # The model emits this template as if it had called file_read, but
    # the response.function_calls is absent and tool_results carries no
    # file_read receipt. The detection is structural — it requires the
    # exact template shape, not prose classification — so false
    # positives are limited to the exact phrasing. A real file_read
    # receipt (or a run_desk_task wrapper that delegated to file_read)
    # in tool_results makes the gate pass.
    if response_text:
        fc_claim = _response_has_file_content_claim(response_text)
        if fc_claim and not _has_file_read_receipt(tool_results):
            failures.append(_file_content_failure_reason(fc_claim))
            logger.warning(
                f"runtime_truth_failures: blocking response with unverified "
                f"file-content claim {fc_claim!r}"
            )

    return failures, warnings


def should_halt_after_tool_failure(
    tool_results: list[Any] | None,
    user_message: str | None = None,
    response_text: str | None = None,
) -> bool:
    """Return True if the response should be halted / blocked due to truth failures."""
    failures, _warnings = runtime_truth_failures(
        tool_results, user_message=user_message, response_text=response_text
    )
    return bool(failures)


def runtime_truth_failure_message(failures: list[str]) -> str:
    unique = list(dict.fromkeys([failure for failure in failures if failure]))
    if not unique:
        # Default message when we know we should halt but no specific failure.
        return "I have not run that yet. I need a real tool result before I can claim I did something."
    reason = "; ".join(unique)
    return f"I have not run that yet. {reason}"


def enforce_runtime_truth_response(
    user_message: str | None,
    response_text: str,
    tool_results: list[Any] | None,
) -> tuple[str, list[str]]:
    """Enforce truth on the response. If a claim is unsupported, replace
    the response with a truth-failure message. Returns (final_text, warnings)
    so the caller can surface theater-detector warnings in response metadata.

    This function is the WIRE-UP point for the live MAX response pipeline.
    It is called from:
      - /api/v1/max/chat/stream (line ~1386 of router.py)
      - /api/v1/max/chat (line ~2363-2364 of router.py)
      - /api/v1/max/chat streaming round (line ~3009-3010 of router.py)

    The OLD behavior was: only check VERIFICATION_REQUIRED_TOOLS. With
    no proof and no claim phrase, it would pass. The NEW behavior (2026-
    06-15): also detect past-tense operational claims in the response
    text and require proof.

    Safe future-tense / conditional phrases (e.g., "I will check", "I
    can check", "I have not run that yet") are explicitly allowed.

    Hotfix 2026-07-15: return shape changed to tuple[str, list[str]]
    so callers can surface theater-detector warnings in metadata.

    2026-08-16 (F3): even when no claim failure fires, the runtime
    strips a model-emitted "✅ Verified" badge that lacks a proof
    object, replacing it with "⚠️ Unverified" (failure mode 7). The
    badge is a model decoration; the runtime owns its truthfulness.
    """
    failures, warnings = runtime_truth_failures(
        tool_results, user_message=user_message, response_text=response_text
    )
    if failures:
        return runtime_truth_failure_message(failures), warnings
    # F3: strip the badge even when no claim failure fired
    cleaned, badge_warnings = strip_unverified_badge(response_text, tool_results)
    warnings.extend(badge_warnings)
    return cleaned, warnings
