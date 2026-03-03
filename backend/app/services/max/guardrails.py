"""Input/Output guardrails for MAX AI."""
import re
from typing import Tuple

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

def check_input(text: str) -> Tuple[bool, str]:
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return False, "prompt_injection"
    for pattern in BLOCKED_TOPICS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return False, "blocked_topic"
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
