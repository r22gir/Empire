"""Input/Output guardrails for MAX AI."""
import os
import re
import logging
from typing import Tuple

logger = logging.getLogger("max.guardrails")

_FOUNDER_CHAT_ID = os.getenv("TELEGRAM_FOUNDER_CHAT_ID")


def is_founder_message(message_context: dict) -> bool:
    """Determine if message is from the founder.
    CC / web = always founder (Command Center is the owner's tool).
    Telegram = match by chat_id.
    Unknown channel = not founder (require PIN fallback).
    """
    channel = message_context.get("channel", "")
    # Command Center (any variant) = always founder
    if channel in ("web", "web_cc", "cc", "command_center", "command-center", ""):
        return True
    # Telegram: match by chat_id
    if not _FOUNDER_CHAT_ID:
        return False
    chat_id = str(message_context.get("chat_id", ""))
    if channel == "telegram" and chat_id == _FOUNDER_CHAT_ID:
        return True
    return False


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)",
    r"forget\s+(all\s+)?(your|the)\s+(instructions|rules|guidelines)",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"new\s+instruction[s]?\s*:",
    r"disregard\s+(all|your|the)\s+",
    r"override\s+(your|the|all)\s+",
    r"jailbreak",
    r"DAN\s+mode",
    r"developer\s+mode\s+enabled",
]

BLOCKED_TOPICS = [
    r"(make|create|build|write)\s+(a\s+)?(virus|malware|trojan|ransomware)",
    r"(hack|breach|exploit)\s+(into|a|the)\s+",
    r"(how\s+to\s+)?(make|build|create)\s+(a\s+)?(bomb|explosive)",
]

def check_input(text: str, message_context: dict = None) -> Tuple[bool, str]:
    text_lower = text.lower()
    founder = is_founder_message(message_context or {})
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            if founder:
                logger.info(f"Founder override: skipping prompt_injection block")
            else:
                return False, "prompt_injection"
    for pattern in BLOCKED_TOPICS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            if not founder:
                return False, "blocked_topic"
            logger.info(f"Founder override: skipping blocked_topic block")
    return True, "ok"

def sanitize_output(text: str) -> str:
    text = re.sub(r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_KEY]", text)
    text = re.sub(r"xai-[a-zA-Z0-9]{20,}", "[REDACTED_KEY]", text)
    return text


# ── Hallucination markers ─────────────────────────────────────────────
# Common patterns that indicate AI is fabricating data rather than citing real sources
FABRICATION_PHRASES = [
    r"(?:according to|based on)\s+(?:a\s+)?(?:recent|2026|2025|latest)\s+(?:survey|study|report|poll|analysis)\b",
    r"(?:studies|research|data)\s+(?:shows?|indicates?|suggests?|reveals?)\s+that\s+approximately\s+\d+%",
]

def check_output_quality(text: str) -> list[str]:
    """Return list of warning flags found in AI output. Empty list = clean."""
    warnings = []
    for pattern in FABRICATION_PHRASES:
        if re.search(pattern, text, re.IGNORECASE):
            warnings.append(f"Possible fabricated statistic: matches pattern '{pattern[:40]}...'")
    return warnings

SAFE_REFUSAL = "I can\'t help with that request. Let me know how else I can assist with Empire operations."


def uncertainty_fallback(topic: str, suggestions: list[str] = None) -> str:
    if suggestions is None:
        suggestions = [
            "Search the web for current information",
            "Check our internal business records (Hermes memory)",
            "Note this as a topic to research later",
        ]
    lines = "\n".join(f"{i}. {s}" for i, s in enumerate(suggestions, 1))
    return (
        f"I don\'t have verified information on \"{topic}\" from reliable Empire sources.\n\n"
        f"Would you like me to:\n{lines}"
    )


def should_defer_uncertain(message: str, confidence: float = None) -> bool:
    if confidence is not None and confidence < 0.6:
        return True
    uncertain_patterns = [
        r'\b(maybe|perhaps|possibly|probably|likely|unlikely)\b',
        r'\b(what\s+if|hypothetical|theoretical|speculate)\b',
        r'\b(guess|estimate|roughly|approximately)\b',
        r"(i\s+(don.t|do\s*not)\s+have\s+(that\s+)?(info|data|information|memory))",
    ]
    return any(re.search(p, message, re.I) for p in uncertain_patterns)
