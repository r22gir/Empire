"""Input/Output guardrails for MAX AI."""
import os
import re
import logging
from datetime import datetime
from typing import Any, Tuple

logger = logging.getLogger("max.guardrails")

_FOUNDER_CHAT_ID = os.getenv("TELEGRAM_FOUNDER_CHAT_ID")

# ── EmpireDell GPU Stability Lock ────────────────────────────────────
# EmpireDell (Xeon E5-2650 v3, Quadro K600) runs a fragile NVIDIA 470 stack.
# Kernel 6.8.0-31-generic + NVIDIA 470.239.06 is the known-good stable state.
# HWE kernels and DKMS-based NVIDIA installs have caused crashes.
# See: ~/EMPIREDELL_GRAPHICS_STABLE_STATE.md

GPU_SAFETY_LOCK = """**EmpireDell GPU stability lock is active.** Known-good stack: kernel 6.8.0-31-generic + NVIDIA 470.239.06 (Quadro K600). Do NOT change kernel/NVIDIA packages without running a simulation first and getting founder approval. Run this to simulate: `sudo apt-get -s upgrade | grep -Ei "linux|nvidia|dkms|grub" || true`"""

GPU_RISKY_PATTERNS = [
    r"\bapt\s+autoremove\b",
    r"\bapt\s+upgrade\b",
    r"\bapt\s+full-upgrade\b",
    r"\bapt-get\s+dist-upgrade\b",
    r"\bubuntu-drivers\s+autoinstall\b",
    r"\bapt\s+install\s+nvidia-driver",
    r"\bapt\s+install\s+nvidia-dkms",
    r"\bapt\s+install\s+nvidia-kernel-source",
    r"\bapt\s+install\s+nvidia-kernel-common",
    r"\bapt\s+purge\s+nvidia",
    r"\bapt\s+remove\s+nvidia",
    r"\blinux-headers-generic-hwe",
    r"\blinux-image-generic-hwe",
    r"\blinux-generic-hwe",
    r"\bhwe-kernel",
    r"\bupdate-grub\b",
    r"\bgrub-set-default\b",
    r"\bgrub-install\b",
    r"\bdkms\s+remove\b",
    r"\bdkms\s+add\b",
    r"\bdkms\s+build\b",
    r"\bsensors-detect\b",
    r"\bnvidia-smi\s+--reset\b",
    r"\bmodprobe\s+-r\s+nvidia",
    r"\bmodprobe\s+nvidia-drm\b",
    r"\bxrandr\s+--output\b.*\s+(--mode|--scale|--rotate|--primary)\b",
    r"\bnvidia-settings\b",
    r"\bupdate-initramfs\s+-u\b",
    r"\bapt-mark\s+unhold\b",
    r"\bapt-mark\s+unhold\b",
    r"\bapt\s+remove\s+--purge\b.*\s+linux-image",
    r"\bpurge\s+linux-image",
    r"\blinux-image-\d+\.\d+",
]

GPU_SAFETY_KEYWORDS = [
    "nvidia driver", "nvidia upgrade", "upgrade nvidia", "update nvidia",
    "nvidia driver install", "nvidia driver upgrade", "nvidia 470",
    "nvidia-driver-470", "nvidia-dkms-470", "nvidia-kernel-source-470",
    "kernel upgrade", "upgrade kernel", "linux kernel", "hwe kernel",
    "upgrade ubuntu", "update ubuntu", "ubuntu upgrade",
    "graphics broken", "resolution broken", "screen black", "display broken",
    "gpu crash", "nvidia crash", "driver crash",
    "autoremove", "apt autoremove",
    "ubuntu drivers", "ubuntu-drivers", "proprietary drivers",
    "install nvidia", "installing nvidia",
]


def check_gpu_safety(text: str) -> tuple[bool, str]:
    """Check if a message is about risky GPU/kernel/apt operations.

    Returns (is_risky: bool, safety_message: str).
    If is_risky is True, the caller should prepend safety_message to the response.
    """
    text_lower = text.lower()
    for pattern in GPU_RISKY_PATTERNS:
        if re.search(pattern, text_lower):
            return True, GPU_SAFETY_LOCK
    for keyword in GPU_SAFETY_KEYWORDS:
        if keyword in text_lower:
            return True, GPU_SAFETY_LOCK
    return False, ""


GPU_VERIFICATION_COMMANDS = """To verify EmpireDell GPU stability, run:
```
uname -r          # should be: 6.8.0-31-generic
nvidia-smi        # should show Driver Version 470.239.06
lsmod | grep -E "nvidia|nouveau"  # should show nvidia, NOT nouveau
xrandr | head -30  # should show 2560x1080 active
apt-mark showhold | grep -E "nvidia|linux|hwe" || true
apt-cache policy nvidia-utils-470 linux-image-6.8.0-31-generic | sed -n '1,120p'
```"""


def is_founder_message(message_context: dict) -> bool:
    """Determine if message is from the founder.
    CC / web = always founder (Command Center is the owner's tool).
    Telegram = match by chat_id.
    Unknown channel = not founder (require PIN fallback).
    H74 (D45, 2026-08-28): missing or unrecognized channel resolves to
    anonymous, NEVER founder. Pre-fix the allow-list tuple contained ""
    and `request.channel or ""` defaulted to "", so any caller omitting
    the `channel` body field walked past every privilege gate. The empty
    string is intentionally absent from the tuple below.
    """
    channel = message_context.get("channel", "")
    # Command Center (any variant) = always founder.
    # NO empty string in this tuple: see H74 docstring above.
    if channel in ("web", "web_cc", "cc", "command_center", "command-center"):
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
    """Scan input for prompt-injection and blocked-topic patterns.

    H81 Phase 2 (2026-09-01): the scan ALWAYS RUNS — even for
    founder. Detections are logged at WARNING with the matched
    pattern, channel, chat_id, founder flag, and a truncated
    excerpt, so a later review can reconstruct what was attempted.
    Nothing is refused on the basis of that detection for founder
    traffic; the message proceeds. Non-founder callers are still
    refused as before — the gate has NOT been weakened.

    Founder ruling (Phase 2 dispatch): scan and log, never block.
    Phase 3 will add identity-checking before the scan for an
    attacker who can reach the chat endpoint.
    """
    text_lower = text.lower()
    msg_ctx = message_context or {}
    founder = is_founder_message(msg_ctx)
    channel = msg_ctx.get("channel", "")
    chat_id = msg_ctx.get("chat_id", "")
    excerpt = (text or "")[:80]  # truncate; full text in caller scope
    ts = datetime.now().isoformat()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.warning(
                f"Guardrail detection [{ts}] kind=prompt_injection "
                f"pattern={pattern!r} channel={channel!r} "
                f"chat_id={chat_id!r} founder={founder} "
                f"excerpt={excerpt!r}"
            )
            if not founder:
                return False, "prompt_injection"

    for pattern in BLOCKED_TOPICS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.warning(
                f"Guardrail detection [{ts}] kind=blocked_topic "
                f"pattern={pattern!r} channel={channel!r} "
                f"chat_id={chat_id!r} founder={founder} "
                f"excerpt={excerpt!r}"
            )
            if not founder:
                return False, "blocked_topic"

    return True, "ok"


# ── Reasoning tag stripper ─────────────────────────────────────────────
# Removes AI internal reasoning (think tags) from output so users never see it.
# Handles complete blocks, orphan open/close tags, and cross-chunk splits.

def strip_reasoning_tags(text: str, *, trim_edges: bool = True) -> str:
    """Remove all AI reasoning/reasoning tag content from text."""
    if not text:
        return text

    # 1. Remove complete <think>... blocks (non-greedy .*? so each block matched individually,
    #    DOTALL so . matches newlines, optional trailing newline preserved)
    text = re.sub(r"<think>.*?<\/think>\n?", "", text, flags=re.IGNORECASE | re.DOTALL)

    # 2. Remove <thinking>...</thinking> blocks
    text = re.sub(r"<thinking>[\s\S]*?</thinking>", "", text, flags=re.IGNORECASE)

    # 3. Remove orphan closing tag  at end of chunk (no opening in this chunk)
    #    This appears after strip of complete tags leaves stray closing tag
    text = re.sub(r"<\/think>$", "", text, flags=re.IGNORECASE)

    # 4. Handle cross-chunk split: orphaned <think> at START of text
    #    Strip everything from <think> to the last newline before real content
    while text.startswith("<think>"):
        nl_idx = text.rfind("\n")
        if nl_idx > 0:
            text = text[nl_idx + 1:]
        else:
            # No newline, just strip the tag itself
            text = text[len("<think>"):]

    # 5. Remove stray opening tags
    text = re.sub(r"<think>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<think>", "", text, flags=re.IGNORECASE)

    # 6. Remove stray closing tags
    text = re.sub(r"", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</think>", "", text, flags=re.IGNORECASE)

    # 7. Remove answer/final wrapper tags (extract content)
    text = re.sub(r"<answer>([\s\S]*?)</answer>", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"<final>([\s\S]*?)</final>", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"<回答>([\s\S]*?)</回答>", r"\1", text, flags=re.IGNORECASE)

    # 8. Collapse excessive blank lines (more than 2 consecutive newlines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 9. Trim leading/trailing whitespace for full responses only.
    # Streaming chunks must preserve edge whitespace so chunk boundaries
    # don't collapse words when concatenated in the browser.
    if trim_edges:
        text = text.strip()

    return text


def sanitize_output(text: str) -> str:
    """Sanitize output: remove API keys and strip reasoning tags."""
    text = re.sub(r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_KEY]", text)
    text = re.sub(r"xai-[a-zA-Z0-9]{20,}", "[REDACTED_KEY]", text)
    text = strip_reasoning_tags(text, trim_edges=True)
    return text


def sanitize_output_streaming(text: str) -> str:
    """Streaming-safe sanitization: preserves edge whitespace per chunk."""
    text = re.sub(r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_KEY]", text)
    text = re.sub(r"xai-[a-zA-Z0-9]{20,}", "[REDACTED_KEY]", text)
    text = strip_reasoning_tags(text, trim_edges=False)
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


_UNCERTAINTY_FALLBACK_TOPIC_MAX_LEN = 120

# Tools that mutate Empire data or complete founder-requested deliverables.
# If any succeeded in the same turn, never replace the reply with research fallback.
_WRITE_OR_DELIVERABLE_TOOLS = frozenset({
    "create_contact",
    "create_engine_quote",
    "create_quick_quote",
    "photo_to_quote",
    "update_contact",
    "create_task",
    "send_quote_email",
    "send_email",
    "svg_to_pdf",
    "generate_quote_pdf",
    "create_invoice",
    "db_write",
    "file_write",
    "file_edit",
    "file_append",
})

_IMPERATIVE_VERBS = (
    "create", "make", "generate", "save", "split", "email", "send me", "send ",
    "invoice", "quote", "build", "draft", "produce", "add ", "update ", "delete ",
    "remove ", "schedule", "queue", "dispatch", "run ", "execute", "prepare",
)

_IMPERATIVE_NOUNS = (
    "estimate", "estimates", "quote", "quotes", "invoice", "invoices",
    "pdf", "pdfs", "contact", "crm", "line item", "line items",
)


def summarize_uncertainty_topic(message: str, *, max_len: int = _UNCERTAINTY_FALLBACK_TOPIC_MAX_LEN) -> str:
    """Short label for uncertainty fallback — never echo the full user prompt."""
    text = re.sub(r"\s+", " ", (message or "").strip())
    if not text:
        return "that topic"
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def is_imperative_action_request(message: str | None) -> bool:
    """True when the user is ordering MAX to act (tools/routes), not asking a factual Q."""
    text = re.sub(r"\s+", " ", (message or "").strip().lower())
    if not text:
        return False
    if "founder action request" in text:
        return True
    if re.search(r"^\s*\d+[\).:\-]\s+", text):
        return True
    has_verb = any(v in text for v in _IMPERATIVE_VERBS)
    has_noun = any(n in text for n in _IMPERATIVE_NOUNS)
    if has_verb and has_noun:
        return True
    if has_verb and re.search(r"\b(create_engine_quote|create_contact|send_quote_email)\b", text):
        return True
    return False


def _successful_write_tools(tool_results: list[Any] | None) -> set[str]:
    names: set[str] = set()
    for entry in tool_results or []:
        if not isinstance(entry, dict):
            continue
        if not entry.get("success"):
            continue
        tool = str(entry.get("tool") or "").strip()
        if tool:
            names.add(tool)
    return names


def founder_action_tools_remaining(message: str | None, tool_results: list[Any] | None) -> list[str]:
    """Explicit tool names mentioned in the request that have not succeeded yet."""
    if not is_imperative_action_request(message):
        return []
    text = (message or "").lower()
    succeeded = _successful_write_tools(tool_results)
    remaining: list[str] = []
    for tool_name in (
        "create_contact",
        "create_engine_quote",
        "create_quick_quote",
        "send_quote_email",
        "send_email",
        "svg_to_pdf",
    ):
        if tool_name in text and tool_name not in succeeded:
            remaining.append(tool_name)
    if not remaining and is_imperative_action_request(message):
        wants_quotes = any(w in text for w in ("estimate", "quote", "invoice"))
        wants_pdf = "pdf" in text
        wants_email = "email" in text or "send " in text
        if wants_quotes and not (succeeded & {"create_engine_quote", "create_quick_quote"}):
            if any(v in text for v in ("create", "make", "save", "generate", "new ")):
                remaining.append("create_engine_quote")
        if wants_pdf and "svg_to_pdf" not in succeeded and "generate_quote_pdf" not in succeeded:
            if any(v in text for v in ("generate", "pdf", "save")):
                remaining.append("svg_to_pdf")
        if wants_email and not (succeeded & {"send_quote_email", "send_email"}):
            if any(v in text for v in ("email", "send")):
                remaining.append("send_quote_email")
    return remaining


def uncertainty_fallback(topic: str, suggestions: list[str] = None) -> str:
    if suggestions is None:
        suggestions = [
            "Search the web for current information",
            "Check our internal business records (Hermes memory)",
            "Note this as a topic to research later",
        ]
    lines = "\n".join(f"{i}. {s}" for i, s in enumerate(suggestions, 1))
    short_topic = summarize_uncertainty_topic(topic)
    return (
        f"I don\'t have verified information on \"{short_topic}\" from reliable Empire sources.\n\n"
        f"Would you like me to:\n{lines}"
    )


def should_defer_uncertain(
    message: str,
    confidence: float = None,
    *,
    tool_results: list[Any] | None = None,
) -> bool:
    """Whether to replace the model reply with the research fallback.

    Applies only to factual Q&A with no supporting tool data — never to
    founder imperative actions or turns that already ran write/deliverable tools.
    """
    if is_imperative_action_request(message):
        return False
    succeeded = _successful_write_tools(tool_results)
    if succeeded & _WRITE_OR_DELIVERABLE_TOOLS:
        return False
    if confidence is not None and confidence < 0.6:
        return True
    uncertain_patterns = [
        r'\b(maybe|perhaps|possibly|probably|likely|unlikely)\b',
        r'\b(what\s+if|hypothetical|theoretical|speculate)\b',
        r'\b(guess|roughly|approximately)\b',
        r'\b(i\s+estimate|my\s+estimate|ballpark\s+estimate|rough\s+estimate)\b',
        r"(i\s+(don.t|do\s*not)\s+have\s+(that\s+)?(info|data|information|memory))",
    ]
    return any(re.search(p, message, re.I) for p in uncertain_patterns)
