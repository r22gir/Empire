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

import re
from typing import Any, Iterable, Optional

from app.services.max.tool_result_normalizer import normalize_tool_results


# Tools that require specific proof fields in their result.
VERIFICATION_REQUIRED_TOOLS = {
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


def runtime_truth_failures(
    tool_results: list[Any] | None,
    user_message: str | None = None,
    response_text: str | None = None,
) -> list[str]:
    """Return a list of truth-failure reasons for the given response.

    Two failure modes:
      1. TOOL VERIFICATION FAILURE — a tool in VERIFICATION_REQUIRED_TOOLS
         ran but its result is missing required fields.
      2. GENERIC CLAIM FAILURE — the response_text contains a past-tense
         operational claim (e.g., "I checked OpenClaw") but no structured
         proof object is in tool_results.

    Returns an empty list if no failures.
    """
    failures: list[str] = []

    # Failure mode 1: tool verification failures.
    for entry in normalize_tool_results(tool_results):
        reason = _tool_failure_reason(entry, user_message=user_message)
        if reason:
            failures.append(reason)

    # Failure mode 2: generic operational claim without proof.
    # This is the new behavior added on 2026-06-15.
    if response_text:
        claim = _response_has_operational_claim(response_text)
        if claim and not _has_proof(tool_results):
            failures.append(_claim_failure_reason(claim))

    return failures


def should_halt_after_tool_failure(
    tool_results: list[Any] | None,
    user_message: str | None = None,
    response_text: str | None = None,
) -> bool:
    """Return True if the response should be halted / blocked due to truth failures."""
    return bool(runtime_truth_failures(tool_results, user_message=user_message, response_text=response_text))


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
) -> str:
    """Enforce truth on the response. If a claim is unsupported, replace
    the response with a truth-failure message.

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
    """
    failures = runtime_truth_failures(tool_results, user_message=user_message, response_text=response_text)
    if failures:
        return runtime_truth_failure_message(failures)
    return response_text
