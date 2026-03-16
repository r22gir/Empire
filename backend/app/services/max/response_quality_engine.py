"""
Response Quality Engine — Universal validator for all MAX outputs.
Applies channel-specific quality checks before any output reaches humans.
Supports fast-pass (Telegram, casual chat) and full-pass (quotes, emails, client-facing).
"""
import re
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("max.quality")


class Channel(str, Enum):
    CHAT = "chat"
    TELEGRAM = "telegram"
    QUOTE = "quote"
    EMAIL = "email"
    ANALYSIS = "analysis"
    DESK = "desk"
    SMS = "sms"         # future
    WHATSAPP = "whatsapp"  # future


class Severity(str, Enum):
    LOW = "low"         # warn in audit log
    MEDIUM = "medium"   # auto-rewrite the problematic section
    CRITICAL = "critical"  # block output + Telegram alert to founder


class PassMode(str, Enum):
    FAST = "fast"   # light checks — Telegram, casual chat
    FULL = "full"   # deep validation — quotes, emails, client-facing


# Which channels get which mode
CHANNEL_MODE = {
    Channel.CHAT: PassMode.FAST,
    Channel.TELEGRAM: PassMode.FAST,
    Channel.DESK: PassMode.FAST,
    Channel.QUOTE: PassMode.FULL,
    Channel.EMAIL: PassMode.FULL,
    Channel.ANALYSIS: PassMode.FAST,
    Channel.SMS: PassMode.FAST,
    Channel.WHATSAPP: PassMode.FAST,
}


@dataclass
class QualityIssue:
    """A single quality problem found in the output."""
    check: str          # name of the check that found it
    severity: Severity
    message: str        # human-readable description
    auto_fixed: bool = False
    fix_description: str = ""


@dataclass
class QualityResult:
    """Result of quality validation."""
    original: str
    cleaned: str
    channel: str
    mode: str
    passed: bool = True
    blocked: bool = False       # critical issue — output should NOT be sent
    issues: list = field(default_factory=list)
    fixed_count: int = 0

    @property
    def severity(self) -> str:
        if not self.issues:
            return "none"
        severities = [i.severity for i in self.issues]
        if Severity.CRITICAL in severities:
            return "critical"
        if Severity.MEDIUM in severities:
            return "medium"
        return "low"


class ResponseQualityEngine:
    """Universal quality validator for all MAX outputs."""

    def validate(
        self,
        content: str,
        channel: Channel = Channel.CHAT,
        context: Optional[dict] = None,
        founder_override: bool = False,
    ) -> QualityResult:
        """Run quality checks on content before it reaches a human.

        Args:
            content: The text/response to validate
            channel: Which channel this output is for
            context: Optional dict with channel-specific data:
                - For quotes: {"quote_data": {...}, "customer": {...}}
                - For emails: {"recipient": "...", "subject": "...", "quote_data": {...}}
                - For analysis: {"analysis_type": "measurement|mockup|outline"}
            founder_override: If True, skip safety hedging checks but keep quality fixes
        """
        if not content or not content.strip():
            return QualityResult(
                original=content or "",
                cleaned=content or "",
                channel=channel.value,
                mode="skip",
                passed=True,
            )

        mode = CHANNEL_MODE.get(channel, PassMode.FAST)
        ctx = context or {}
        result = QualityResult(
            original=content,
            cleaned=content,
            channel=channel.value,
            mode=mode.value,
        )

        # ── UNIVERSAL CHECKS (all channels) ─────────────────────
        self._check_duplication(result)
        self._check_ai_artifacts(result)
        if not founder_override:
            self._check_empty_claims(result)
        self._check_fake_task_ids(result, ctx)

        # ── CHANNEL-SPECIFIC CHECKS ─────────────────────────────
        if channel == Channel.QUOTE:
            self._check_quote_quality(result, ctx)
        elif channel == Channel.EMAIL:
            self._check_email_quality(result, ctx)
        elif channel == Channel.ANALYSIS:
            self._check_analysis_quality(result)
        elif channel in (Channel.TELEGRAM, Channel.CHAT):
            self._check_chat_quality(result)

        # Apply fixes for MEDIUM severity
        if result.issues:
            result.cleaned = self._apply_auto_fixes(result)

        # Determine pass/block — founder messages are never blocked by quality engine
        if founder_override:
            result.passed = True
            result.blocked = False
        else:
            result.passed = all(i.severity != Severity.CRITICAL for i in result.issues)
            result.blocked = any(i.severity == Severity.CRITICAL for i in result.issues)
        result.fixed_count = sum(1 for i in result.issues if i.auto_fixed)

        if result.issues:
            logger.info(
                f"Quality [{channel.value}]: {len(result.issues)} issues "
                f"({result.severity}), {result.fixed_count} auto-fixed"
                f"{' [founder-override]' if founder_override else ''}"
            )

        return result

    # ── UNIVERSAL CHECKS ────────────────────────────────────────

    def _check_duplication(self, result: QualityResult):
        """Detect duplicated/stacked responses or repeated paragraphs."""
        text = result.cleaned
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) > 30]

        if len(paragraphs) < 2:
            return

        # Check for near-identical paragraphs
        seen = []
        duplicates = []
        for i, para in enumerate(paragraphs):
            # Normalize for comparison
            normalized = re.sub(r'\s+', ' ', para.lower().strip())
            for j, prev in enumerate(seen):
                # Check overlap ratio
                overlap = self._text_similarity(normalized, prev)
                if overlap > 0.7:  # 70% similar = duplicate
                    duplicates.append(i)
                    break
            seen.append(normalized)

        if duplicates:
            # Remove duplicate paragraphs, keep first occurrence
            kept = [p for i, p in enumerate(paragraphs) if i not in duplicates]
            # Preserve non-paragraph content (short lines, headers, etc.)
            all_parts = text.split("\n\n")
            cleaned_parts = []
            dup_idx = 0
            para_idx = 0
            for part in all_parts:
                stripped = part.strip()
                if stripped and len(stripped) > 30:
                    if para_idx not in duplicates:
                        cleaned_parts.append(part)
                    para_idx += 1
                else:
                    cleaned_parts.append(part)

            result.cleaned = "\n\n".join(cleaned_parts)
            result.issues.append(QualityIssue(
                check="duplication",
                severity=Severity.MEDIUM,
                message=f"Removed {len(duplicates)} duplicate paragraph(s)",
                auto_fixed=True,
                fix_description="Duplicate paragraphs removed",
            ))

    def _check_ai_artifacts(self, result: QualityResult):
        """Detect and clean AI processing artifacts."""
        text = result.cleaned
        issues_found = []

        # Pattern: "As an AI..." or "I'm an AI assistant..."
        ai_identity = re.findall(
            r"(?:As an AI|I'?m (?:an? )?AI|As a (?:language |large )?model|I don'?t have (?:personal |real )?(?:feelings|emotions|opinions))",
            text, re.IGNORECASE
        )
        if ai_identity:
            issues_found.append("AI identity disclosure")

        # Pattern: "Let me think about this..." or "Let me analyze..."
        process_narration = re.findall(
            r"(?:Let me (?:think|analyze|process|check|look|search|consider|review)|I'll (?:now |start )(?:analyze|look|check|process))",
            text, re.IGNORECASE
        )
        if process_narration:
            issues_found.append("Process narration")

        # Pattern: "Here's what I found:" repeated
        intro_phrases = re.findall(
            r"(?:Here'?s? (?:what|is)|Based on (?:my|the) (?:analysis|review|search))[^.!?]*[.!?]",
            text, re.IGNORECASE
        )
        if len(intro_phrases) > 1:
            issues_found.append(f"Repeated intro phrases ({len(intro_phrases)}x)")

        if issues_found:
            result.issues.append(QualityIssue(
                check="ai_artifacts",
                severity=Severity.LOW,
                message=f"AI artifacts detected: {', '.join(issues_found)}",
            ))

    def _check_empty_claims(self, result: QualityResult):
        """Detect hedging or empty statements that provide no value."""
        text = result.cleaned
        empty_patterns = [
            r"I (?:don'?t|do not) have (?:access to|information about|data on) (?:that|this|your)",
            r"I (?:cannot|can'?t) (?:verify|confirm|access) (?:that|this)",
            r"(?:Unfortunately|Regrettably),? I (?:don'?t|cannot|am unable)",
        ]

        matches = 0
        for pat in empty_patterns:
            matches += len(re.findall(pat, text, re.IGNORECASE))

        if matches > 2:
            result.issues.append(QualityIssue(
                check="empty_claims",
                severity=Severity.LOW,
                message=f"Response contains {matches} hedging/empty statements",
            ))

    # ── QUOTE-SPECIFIC CHECKS ───────────────────────────────────

    def _check_quote_quality(self, result: QualityResult, ctx: dict):
        """Deep validation for quotes — math, data integrity, anomalies."""
        quote_data = ctx.get("quote_data", {})
        if not quote_data:
            return

        # CHECK 1: Math verification
        line_items = quote_data.get("line_items", [])
        computed_subtotal = sum(
            round(item.get("quantity", 1) * item.get("rate", 0), 2)
            for item in line_items
        )

        # Also check room-based pricing
        rooms = quote_data.get("rooms", [])
        if rooms and computed_subtotal == 0:
            for room in rooms:
                for w in room.get("windows", []):
                    computed_subtotal += w.get("price", 0)
                for u in room.get("upholstery", []):
                    computed_subtotal += u.get("price", 0)
            computed_subtotal = round(computed_subtotal, 2)

        stated_subtotal = quote_data.get("subtotal", 0)
        stated_total = quote_data.get("total", 0)
        tax = quote_data.get("tax_amount", 0)
        discount = quote_data.get("discount_amount", 0)
        expected_total = round(stated_subtotal + tax - discount, 2)

        if stated_subtotal > 0 and abs(computed_subtotal - stated_subtotal) > 1.0:
            result.issues.append(QualityIssue(
                check="quote_math",
                severity=Severity.CRITICAL,
                message=f"Subtotal mismatch: line items sum to ${computed_subtotal:.2f} but subtotal says ${stated_subtotal:.2f}",
            ))

        if stated_total > 0 and abs(stated_total - expected_total) > 1.0:
            result.issues.append(QualityIssue(
                check="quote_math",
                severity=Severity.CRITICAL,
                message=f"Total mismatch: expected ${expected_total:.2f} (subtotal+tax-discount) but total says ${stated_total:.2f}",
            ))

        # CHECK 2: Duplicate line items
        if line_items:
            descriptions = [item.get("description", "").lower().strip() for item in line_items]
            seen_desc = set()
            for desc in descriptions:
                if desc and desc in seen_desc:
                    result.issues.append(QualityIssue(
                        check="quote_duplicates",
                        severity=Severity.MEDIUM,
                        message=f"Duplicate line item: '{desc}'",
                    ))
                    break
                seen_desc.add(desc)

        # CHECK 3: Customer name present
        customer = quote_data.get("customer_name", "")
        if not customer or customer.lower() in ("customer", "unknown", "n/a", ""):
            result.issues.append(QualityIssue(
                check="quote_customer",
                severity=Severity.MEDIUM,
                message="Quote has no valid customer name",
            ))

        # CHECK 4: Abnormal total (compare to historical average)
        if stated_total > 0:
            self._check_quote_anomaly(result, stated_total)

    def _check_quote_anomaly(self, result: QualityResult, total: float):
        """Flag if quote total is >15% off from historical average."""
        try:
            import os
            quotes_dir = os.path.expanduser("~/empire-repo/backend/data/quotes")
            if not os.path.isdir(quotes_dir):
                return

            past_totals = []
            for fname in os.listdir(quotes_dir):
                if not fname.endswith(".json") or fname.startswith("_"):
                    continue
                try:
                    with open(os.path.join(quotes_dir, fname)) as f:
                        q = json.load(f)
                    t = q.get("total", 0)
                    if t > 50:  # Skip test/zero quotes
                        past_totals.append(t)
                except Exception:
                    pass

            if len(past_totals) < 3:
                return  # Not enough history

            avg = sum(past_totals) / len(past_totals)
            deviation = abs(total - avg) / avg

            if deviation > 0.15:  # >15% off
                direction = "higher" if total > avg else "lower"
                result.issues.append(QualityIssue(
                    check="quote_anomaly",
                    severity=Severity.CRITICAL,
                    message=f"Quote total ${total:,.2f} is {deviation:.0%} {direction} than average (${avg:,.2f}). BLOCKED — founder review required.",
                ))
        except Exception as e:
            logger.debug(f"Quote anomaly check failed: {e}")

    # ── EMAIL-SPECIFIC CHECKS ───────────────────────────────────

    def _check_email_quality(self, result: QualityResult, ctx: dict):
        """Validate email content before sending."""
        text = result.cleaned

        # CHECK 1: Recipient match
        recipient = ctx.get("recipient", "")
        subject = ctx.get("subject", "")
        customer_name = ctx.get("customer_name", "")

        if customer_name and customer_name.lower() not in ("customer", "unknown", ""):
            # Check if the email mentions a different customer name
            names_in_text = re.findall(r"Dear\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
            for name in names_in_text:
                # Match if first name or full name overlaps
                name_lower = name.lower()
                customer_lower = customer_name.lower()
                first_name = customer_lower.split()[0]
                if name_lower != first_name and name_lower != customer_lower and first_name not in name_lower:
                    result.issues.append(QualityIssue(
                        check="email_recipient",
                        severity=Severity.CRITICAL,
                        message=f"Email addresses '{name}' but customer is '{customer_name}'",
                    ))
                    break

        # CHECK 2: Duplicate paragraphs (stricter for emails, skip HTML tags)
        paragraphs = [
            p.strip() for p in text.split("\n")
            if p.strip() and len(p.strip()) > 20 and not p.strip().startswith("<")
        ]
        if len(paragraphs) != len(set(paragraphs)):
            result.issues.append(QualityIssue(
                check="email_duplicates",
                severity=Severity.MEDIUM,
                message="Email contains duplicate lines/paragraphs",
                auto_fixed=True,
                fix_description="Duplicate lines removed",
            ))
            # Deduplicate
            seen_lines = set()
            unique_lines = []
            for line in result.cleaned.split("\n"):
                stripped = line.strip()
                if stripped and len(stripped) > 20:
                    if stripped not in seen_lines:
                        seen_lines.add(stripped)
                        unique_lines.append(line)
                else:
                    unique_lines.append(line)
            result.cleaned = "\n".join(unique_lines)

        # CHECK 3: Professional tone (no weird AI artifacts in email)
        weird_patterns = [
            r"(?:As (?:an |your )?AI|I'?m (?:an? )?(?:AI|artificial|language model))",
            r"(?:I hope this (?:email |message )?finds you well){2,}",
            r"\*{2,}[^*]+\*{2,}",  # Markdown bold in email (wrong format)
        ]
        for pat in weird_patterns:
            if re.search(pat, text, re.IGNORECASE):
                result.issues.append(QualityIssue(
                    check="email_tone",
                    severity=Severity.MEDIUM,
                    message=f"Email contains AI artifacts or formatting issues",
                ))
                break

        # CHECK 4: Quote data consistency (if email is about a quote)
        quote_data = ctx.get("quote_data", {})
        if quote_data:
            quote_num = quote_data.get("quote_number", "")
            quote_total = quote_data.get("total", 0)
            if quote_num and quote_num not in text:
                result.issues.append(QualityIssue(
                    check="email_quote_ref",
                    severity=Severity.LOW,
                    message=f"Email about quote {quote_num} but doesn't reference the quote number",
                ))
            # Check if total mentioned in email matches quote total
            if quote_total > 0:
                amounts = re.findall(r'\$[\d,]+\.?\d*', text)
                amounts_float = []
                for a in amounts:
                    try:
                        amounts_float.append(float(a.replace('$', '').replace(',', '')))
                    except ValueError:
                        pass
                if amounts_float and quote_total not in amounts_float:
                    # Check if any amount is close
                    close = any(abs(a - quote_total) < 1.0 for a in amounts_float)
                    if not close and amounts_float:
                        result.issues.append(QualityIssue(
                            check="email_amount",
                            severity=Severity.MEDIUM,
                            message=f"Email mentions ${amounts_float[0]:,.2f} but quote total is ${quote_total:,.2f}",
                        ))

    # ── ANALYSIS-SPECIFIC CHECKS ────────────────────────────────

    def _check_analysis_quality(self, result: QualityResult):
        """Validate AI analysis output (photos, measurements, documents)."""
        text = result.cleaned

        # CHECK 1: No rambling process descriptions
        process_phrases = re.findall(
            r"(?:I (?:can see|notice|observe|am analyzing|will now)|Looking at (?:the|this) (?:image|photo|document))",
            text, re.IGNORECASE
        )
        if len(process_phrases) > 2:
            result.issues.append(QualityIssue(
                check="analysis_rambling",
                severity=Severity.LOW,
                message=f"Analysis contains {len(process_phrases)} process narration phrases",
            ))

        # CHECK 2: Multiple analysis blocks (repeated headers)
        headers = re.findall(r"(?:^|\n)(?:#{1,3}\s|Analysis|Results?|Summary|Findings)[:\s]", text)
        if len(headers) > 3:
            result.issues.append(QualityIssue(
                check="analysis_duplicates",
                severity=Severity.MEDIUM,
                message=f"Analysis contains {len(headers)} section headers — possible duplicate blocks",
            ))

    # ── CHAT/TELEGRAM CHECKS ────────────────────────────────────

    def _check_chat_quality(self, result: QualityResult):
        """Light checks for chat and Telegram responses."""
        text = result.cleaned

        # CHECK 1: Response too long for Telegram
        if result.channel == Channel.TELEGRAM.value and len(text) > 3500:
            result.issues.append(QualityIssue(
                check="telegram_length",
                severity=Severity.LOW,
                message=f"Telegram response is {len(text)} chars (limit 4096)",
            ))

        # CHECK 2: Stacked duplicate responses (same content repeated)
        lines = text.split("\n")
        if len(lines) > 5:
            # Check if first 3 lines appear again later
            first_block = "\n".join(lines[:3]).strip()
            rest = "\n".join(lines[3:])
            if first_block and first_block in rest:
                result.issues.append(QualityIssue(
                    check="chat_stacked",
                    severity=Severity.MEDIUM,
                    message="Response appears to contain stacked duplicate content",
                    auto_fixed=True,
                    fix_description="Stacked duplicate removed",
                ))
                # Keep only the content after the last occurrence
                idx = rest.rfind(first_block)
                if idx >= 0:
                    result.cleaned = rest[idx:]

    # ── FAKE TASK ID CHECK ──────────────────────────────────────

    def _check_fake_task_ids(self, result: QualityResult, ctx: dict):
        """Detect hallucinated task IDs when no create_task tool was called."""
        tools_called = ctx.get("tools_called", [])
        if any(t in ("create_task", "submit_desk_task") for t in tools_called):
            return

        text = result.cleaned
        fake_patterns = [
            r"Task\s+#[0-9a-fA-F]{4,}",
            r"Task\s+ID[:\s]+[0-9a-fA-F]{4,}",
            r"Task\s+#\w{2,8}\s+created",
            r"(?:logged|queued|created)\s+(?:task|Task)\s+#\w+",
        ]

        for pat in fake_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                result.cleaned = re.sub(pat, "I'll create that task now using the task tool", text, flags=re.IGNORECASE)
                result.issues.append(QualityIssue(
                    check="fake_task_id",
                    severity=Severity.MEDIUM,
                    message=f"Fake task ID detected: '{match.group()}' — no create_task tool was called",
                    auto_fixed=True,
                    fix_description="Replaced fabricated task reference with prompt to use tool",
                ))
                return

    # ── AUTO-FIX ENGINE ─────────────────────────────────────────

    def _apply_auto_fixes(self, result: QualityResult) -> str:
        """Apply automatic fixes for MEDIUM severity issues."""
        text = result.cleaned

        for issue in result.issues:
            if issue.severity == Severity.MEDIUM and issue.auto_fixed:
                # Fixes were already applied inline during checks
                continue

        return text

    # ── UTILITY ─────────────────────────────────────────────────

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """Simple word-overlap similarity ratio."""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0


# Singleton
quality_engine = ResponseQualityEngine()
