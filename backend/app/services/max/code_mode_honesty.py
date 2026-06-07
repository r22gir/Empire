"""Code-mode honesty guardrail for MAX.

MAX must distinguish between:
  (A) "I can draft code as text in this chat"   (always available, just text)
  (B) "I have verified write access to this repo"  (only via async code-task runner)

When MAX's response contains claims like "I just wrote the file" or "I have
updated the file" WITHOUT the response also reporting a real code-task ID
from /api/v1/max/code-task, the response is a hallucination. The user will
see the file on disk unchanged.

This module detects the false-claim pattern and returns a guardrail banner
that the MAX chat layer can prepend or append to the response.

The detector is conservative:
    - Only flags the strongest claim patterns ("I wrote", "I edited",
      "I created", "I committed", "I updated the file").
    - Does NOT flag "here is a draft", "you could write", "I suggest".
    - Does NOT flag draft code shown in code blocks.
    - Provides a clear reason code so the UI can show the founder WHY
      MAX's claim was flagged.
"""
from __future__ import annotations

import re
from typing import Any


# Strong claim patterns: MAX saying it performed a write action on the
# repo in the current turn. Each pattern's group(0) is the matched claim.
WRITE_CLAIM_PATTERNS = (
    r"\bi (?:just |have |already |now |successfully )?(?:wrote|written|writed) (?:the |a |an |to )?(?:file|module|script|function|class|component|page|route|handler|service|test|fixture|config|\.py|\.ts|\.tsx|\.js|\.json|\.yaml|\.yml|\.toml|\.md)\b",
    r"\bi (?:just |have |already |now |successfully )?(?:edited|modified|updated|patched|fixed|rewrote|rewritten) (?:the |a |an |to )?(?:file|module|script|function|class|component|page|route|handler|service|test|fixture|config|\.py|\.ts|\.tsx|\.js|\.json|\.yaml|\.yml|\.toml|\.md)\b",
    r"\bi (?:just |have |already |now |successfully )?(?:created|made|added|inserted|wrote) (?:the |a |an )?(?:new )?(?:file|module|script|function|class|component|page|route|handler|service|test|fixture|config|\.py|\.ts|\.tsx|\.js|\.json)\b",
    r"\bi (?:just |have |already |now |successfully )?(?:committed|pushed|merged) (?:the |a |an )?(?:change|fix|update|commit|file)\b",
    r"\bi (?:just |have |already |now |successfully )?(?:saved|wrote|updated) (?:the |a |an )?file\b",
    r"\bi (?:just |have |already |now )?deleted (?:the |a |an )?(?:file|module|script|directory|folder)\b",
    r"\bi (?:just |have |already |now )?renamed (?:the |a |an )?(?:file|module|script)\b",
    r"\bthe (?:file|module|script) has been (?:written|edited|updated|created|modified|deleted|saved)\b",
    r"\bthe change(?:s)? (?:have been|has been|were|was) (?:applied|committed|pushed|saved|written|merged)\b",
    r"\bi(?:'ve|'ve| have) updated (?:the |a |an )?(?:file|module|script|function|class|component|page|route|handler|service)\b",
    r"\bi(?:'ve|'ve| have) edited (?:the |a |an )?(?:file|module|script|function|class|component|page|route|handler|service)\b",
    r"\bi(?:'ve|'ve| have) created (?:the |a |an )?(?:new )?(?:file|module|script|function|class|component|page|route|handler|service)\b",
    r"\bfile (?:written|saved|updated|created|edited|modified) at\b",
    r"\b(?:wrote|written|created|updated|edited|modified) the file to disk\b",
)


# Compound these into a single compiled regex with case-insensitive flag.
_WRITE_CLAIM_RE = re.compile(
    "|".join(WRITE_CLAIM_PATTERNS),
    re.IGNORECASE,
)


# A code-task ID looks like "ct-..." or "task-..." or similar UUID-ish
# shape. The chat response is allowed to legitimately claim a write if
# it also surfaces such an ID.
CODE_TASK_ID_PATTERN = re.compile(
    r"\b(?:ct|task|code[_-]task)[_-]?[a-z0-9]{6,}\b",
    re.IGNORECASE,
)

# Phrases that indicate MAX is being honest (just drafting, not claiming write)
DRAFT_PHRASES = (
    "here is a draft",
    "here's a draft",
    "you can paste this",
    "you would write",
    "you could write",
    "as a sketch",
    "as an example",
    "this is a starting point",
    "draft code",
    "for reference",
    "i can draft",
    "i can suggest",
    "i can help you write",
    "would you like me to",
    "to apply this",
    "to commit this",
    "to actually write",
    "via the code-task endpoint",
    "via /code-task",
    "by submitting this to",
)


def _looks_like_draft(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in DRAFT_PHRASES)


def check_code_mode_honesty(response_text: str, tool_results: list | None = None) -> dict:
    """Return a guardrail result for a MAX chat response.

    Returns a dict:
        flagged: True if the response makes a write claim without a
            code-task ID (or contains 'I just wrote ...' style text).
        reason_code: machine-readable reason (e.g. "UNVERIFIED_WRITE_CLAIM").
        reason: human-readable description.
        matched_claim: the regex match that triggered the flag (if any).
        recommendation: what the user should do (e.g. "submit as a code task").
    """
    if not response_text:
        return {
            "flagged": False,
            "reason_code": None,
            "reason": None,
            "matched_claim": None,
            "recommendation": None,
        }

    # 1. Find a write-claim match in the response.
    match = _WRITE_CLAIM_RE.search(response_text)
    if not match:
        return {
            "flagged": False,
            "reason_code": None,
            "reason": None,
            "matched_claim": None,
            "recommendation": None,
        }

    # 2. If the response also surfaces a code-task ID, the claim may be
    #    legitimate (a code-task was actually submitted).
    tool_results = tool_results or []
    if CODE_TASK_ID_PATTERN.search(response_text):
        return {
            "flagged": False,
            "reason_code": None,
            "reason": None,
            "matched_claim": None,
            "recommendation": None,
        }
    if any(CODE_TASK_ID_PATTERN.search(str(tr)) for tr in tool_results):
        return {
            "flagged": False,
            "reason_code": None,
            "reason": None,
            "matched_claim": None,
            "recommendation": None,
        }

    # 3. If the response is clearly framing the code as a draft, the
    #    claim is not unverified.
    if _looks_like_draft(response_text):
        return {
            "flagged": False,
            "reason_code": None,
            "reason": None,
            "matched_claim": None,
            "recommendation": None,
        }

    # 4. The claim is unverified — flag it.
    matched_claim = match.group(0)
    return {
        "flagged": True,
        "reason_code": "UNVERIFIED_WRITE_CLAIM",
        "reason": (
            f"MAX claimed a repo write action (\"{matched_claim}\") without "
            "submitting a real code task via /api/v1/max/code-task. The "
            "file on disk is unchanged. This is a draft, not a verified "
            "change."
        ),
        "matched_claim": matched_claim,
        "recommendation": (
            "If you want this code applied, ask MAX to submit it as a code "
            "task (Code Mode) so Atlas/CodeForge can actually run the edits."
        ),
    }


def format_code_mode_banner(check_result: dict) -> str:
    """Return a one-line human-readable banner to append to the response."""
    if not check_result.get("flagged"):
        return ""
    return (
        f"\n\n> ⚠️ **Code-mode honesty guardrail** — "
        f"I can draft code in chat, but I do NOT have verified write access "
        f"to this repo from this turn. The code above is a draft. "
        f"Reason: {check_result['reason_code']}. "
        f"{check_result['recommendation']}"
    )
