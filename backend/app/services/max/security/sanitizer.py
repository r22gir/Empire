"""
Unified Input Sanitizer (v6.0)

Channel-agnostic injection detection, input validation, output sanitization,
and audit logging. Consolidates both guardrails modules into a single
security layer used across all input channels:

  - Telegram messages (text, voice transcripts, photo captions)
  - Command Center chat
  - API requests (pipeline, desk tasks, quote submissions)
  - Desk-generated prompts

Usage:
    from app.services.max.security import sanitizer

    result = sanitizer.check(text, channel="telegram", session_id="chat_123")
    if not result["safe"]:
        # Block and log
        logger.warning("Blocked: %s", result["reason"])

    clean_output = sanitizer.clean_output(ai_response)
"""

import json
import logging
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("max.security.sanitizer")

AUDIT_DIR = Path.home() / "empire-repo" / "backend" / "data" / "security"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


# ── Injection Patterns ───────────────────────────────────────────────────
# Comprehensive set combining both existing guardrails modules + new patterns

INJECTION_PATTERNS = [
    # Prompt injection — role hijacking
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)",
    r"forget\s+(all\s+)?(your|the)\s+(instructions|rules|guidelines)",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"new\s+instruction[s]?\s*:",
    r"disregard\s+(all|your|the)\s+",
    r"override\s+(your|the|all)\s+",
    r"pretend\s+(you\s+are|to\s+be)",
    # Jailbreak keywords
    r"jailbreak",
    r"DAN\s+mode",
    r"developer\s+mode\s+enabled",
    # System prompt extraction
    r"reveal\s+(your\s+)?(system|initial)\s+prompt",
    r"show\s+(your\s+)?(system|initial)\s+prompt",
    r"print\s+(your\s+)?(system|initial)\s+prompt",
    r"what\s+(is|are)\s+your\s+(system\s+)?instructions",
    r"repeat\s+(your\s+)?(system\s+)?prompt\s+verbatim",
    # Encoding attacks
    r"base64\s+decode\s+the\s+following",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__\s*\(",
    # Path traversal (in text input)
    r"\.\./\.\./",
    r"%2e%2e%2f",
]

BLOCKED_TOPICS = [
    r"(make|create|build|write)\s+(a\s+)?(virus|malware|trojan|ransomware)",
    r"(hack|breach|exploit)\s+(into|a|the)\s+",
    r"(how\s+to\s+)?(make|build|create)\s+(a\s+)?(bomb|explosive|weapon)",
]

# Patterns to redact from AI output
SENSITIVE_OUTPUT_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_API_KEY]"),
    (r"sk-ant-[a-zA-Z0-9\-]{20,}", "[REDACTED_API_KEY]"),
    (r"xai-[a-zA-Z0-9]{20,}", "[REDACTED_API_KEY]"),
    (r"ghp_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),
    (r"gho_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),
    (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
    (r"(?:password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{4,}['\"]", "[REDACTED_PASSWORD]"),
    (r"(?:token|secret|key)\s*[=:]\s*['\"][^'\"]{8,}['\"]", "[REDACTED_SECRET]"),
]

# SQL injection patterns (for quote/task text fields)
SQL_INJECTION_PATTERNS = [
    r"(?:union\s+select|drop\s+table|delete\s+from|insert\s+into)\b",
    r"(?:;\s*(?:drop|delete|update|insert|alter|create)\s)",
    r"(?:'\s*(?:or|and)\s+['\d])",
    r"(?:--\s*$)",
]

# XSS patterns
XSS_PATTERNS = [
    r"<script\b[^>]*>",
    r"javascript\s*:",
    r"on(?:load|error|click|mouseover)\s*=",
    r"<iframe\b",
    r"<object\b",
]


class InputSanitizer:
    """Unified security layer for all input channels."""

    def __init__(self):
        self._injection_re = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
        self._blocked_re = [re.compile(p, re.IGNORECASE) for p in BLOCKED_TOPICS]
        self._sql_re = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]
        self._xss_re = [re.compile(p, re.IGNORECASE) for p in XSS_PATTERNS]
        self._output_re = [(re.compile(p), repl) for p, repl in SENSITIVE_OUTPUT_PATTERNS]

        # Rate limiting: per-session sliding window
        self._rate_counts: Dict[str, List[float]] = defaultdict(list)
        self._blocked_sessions: Dict[str, float] = {}

        # Stats
        self._stats = {
            "total_checks": 0,
            "blocked_injection": 0,
            "blocked_topic": 0,
            "blocked_sql": 0,
            "blocked_xss": 0,
            "blocked_rate": 0,
        }

    def check(
        self,
        text: str,
        channel: str = "unknown",
        session_id: str = "",
        rate_limit: int = 30,
        rate_window: int = 60,
    ) -> Dict[str, Any]:
        """Check input text for security threats.

        Args:
            text: Raw input text to check
            channel: Source channel (telegram, chat, api, desk, pipeline)
            session_id: Caller identifier for rate limiting
            rate_limit: Max requests per window (default 30)
            rate_window: Window in seconds (default 60)

        Returns:
            {
                "safe": bool,
                "reason": str or None,
                "threat_type": str or None,  # injection, blocked_topic, sql, xss, rate_limit
                "channel": str,
            }
        """
        self._stats["total_checks"] += 1

        if not text or not text.strip():
            return {"safe": True, "reason": None, "threat_type": None, "channel": channel}

        # Check session block
        if session_id and session_id in self._blocked_sessions:
            block_time = self._blocked_sessions[session_id]
            if time.time() - block_time < 3600:  # 1 hour block
                return self._block("Session blocked due to prior violation", "session_block", channel, session_id, text)
            else:
                del self._blocked_sessions[session_id]

        # Rate limit check
        if session_id and rate_limit > 0:
            now = time.time()
            window = self._rate_counts[session_id]
            window[:] = [t for t in window if t > now - rate_window]
            if len(window) >= rate_limit:
                self._stats["blocked_rate"] += 1
                return self._block(
                    f"Rate limit exceeded ({rate_limit}/{rate_window}s)",
                    "rate_limit", channel, session_id, text,
                )
            window.append(now)

        text_lower = text.lower()

        # Prompt injection
        for pattern in self._injection_re:
            if pattern.search(text_lower):
                self._stats["blocked_injection"] += 1
                if session_id:
                    self._blocked_sessions[session_id] = time.time()
                return self._block(
                    "Prompt injection detected", "injection", channel, session_id, text,
                )

        # Blocked topics
        for pattern in self._blocked_re:
            if pattern.search(text_lower):
                self._stats["blocked_topic"] += 1
                return self._block(
                    "Blocked topic detected", "blocked_topic", channel, session_id, text,
                )

        # SQL injection (only for data-entry channels)
        if channel in ("api", "pipeline", "desk", "chat"):
            for pattern in self._sql_re:
                if pattern.search(text_lower):
                    self._stats["blocked_sql"] += 1
                    return self._block(
                        "SQL injection pattern detected", "sql_injection", channel, session_id, text,
                    )

        # XSS (for web-facing inputs)
        if channel in ("api", "chat", "intake"):
            for pattern in self._xss_re:
                if pattern.search(text):
                    self._stats["blocked_xss"] += 1
                    return self._block(
                        "XSS pattern detected", "xss", channel, session_id, text,
                    )

        return {"safe": True, "reason": None, "threat_type": None, "channel": channel}

    def clean_output(self, text: str) -> str:
        """Sanitize AI output — redact API keys, secrets, sensitive paths."""
        if not text:
            return text
        for pattern, replacement in self._output_re:
            text = pattern.sub(replacement, text)
        return text

    def strip_html(self, text: str) -> str:
        """Strip HTML tags from input (for plain-text fields)."""
        return re.sub(r"<[^>]+>", "", text)

    def get_stats(self) -> Dict[str, Any]:
        """Return cumulative security stats."""
        return dict(self._stats)

    def _block(
        self,
        reason: str,
        threat_type: str,
        channel: str,
        session_id: str,
        text: str,
    ) -> Dict[str, Any]:
        """Log blocked input and return block result."""
        self._audit_log(reason, threat_type, channel, session_id, text)
        return {
            "safe": False,
            "reason": reason,
            "threat_type": threat_type,
            "channel": channel,
        }

    def _audit_log(
        self,
        reason: str,
        threat_type: str,
        channel: str,
        session_id: str,
        text: str,
    ):
        """Append to security audit log on disk."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "threat_type": threat_type,
            "reason": reason,
            "channel": channel,
            "session_id": session_id or "unknown",
            "text_preview": text[:200] if text else "",
        }
        logger.warning(
            "[SECURITY] %s on %s (session=%s): %s",
            threat_type, channel, session_id or "?", reason,
        )

        try:
            log_path = AUDIT_DIR / "audit_log.jsonl"
            with open(log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("Failed to write audit log: %s", e)

        # Also log to brain memory if available
        try:
            from app.services.max.brain.memory_store import MemoryStore
            ms = MemoryStore()
            ms.add_memory(
                category="security",
                subcategory=threat_type,
                content=f"[{channel}] {reason}: {text[:100]}",
                subject="InputSanitizer",
                importance=8,
                source="security",
                tags=["security", threat_type, channel],
            )
        except Exception:
            pass


# Singleton
sanitizer = InputSanitizer()
