"""Input/Output guardrails for MAX AI."""
import os
import re
import logging
from typing import Tuple

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
