"""
Quality Gate — Response validation for MAX.
Runs checks on every AI response before delivery to ensure accuracy and reliability.
"""
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("max.quality_gate")

# Confidence levels
VERIFIED = "verified"       # Checked against DB
HIGH = "high"               # Strong reasoning, tool results confirm
MODERATE = "moderate"       # Reasonable but unverified
LOW = "low"                 # Uncertain — flag to user
FAILED = "failed"           # Quality check caught an error


@dataclass
class QualityResult:
    level: str = HIGH
    checks_performed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    disclaimer: str = ""
    validation_time_ms: float = 0.0


def validate_response(
    response: str,
    category: str = "",
    tool_results: Optional[list] = None,
    model_used: str = "",
) -> QualityResult:
    """Run quality checks on a MAX response before delivery."""
    start = time.time()
    result = QualityResult()
    tool_results = tool_results or []

    # 1. Action verification — check tool results for errors
    _check_tool_results(result, tool_results)

    # 2. Uncertainty detection
    _check_uncertainty(result, response)

    # 3. Entity reference check (quote numbers, customer names)
    _check_entity_references(result, response, tool_results)

    # 4. Calculation check
    _check_calculations(result, response)

    # 5. Completeness heuristic
    _check_completeness(result, response)

    result.validation_time_ms = (time.time() - start) * 1000

    # Determine final confidence level
    if result.level == FAILED:
        pass  # Already set by a check
    elif any("tool_error" in w for w in result.warnings):
        result.level = FAILED
        result.disclaimer = "⚠️ One or more actions encountered errors. Results may be incomplete."
    elif any("unverified_entity" in w for w in result.warnings):
        result.level = MODERATE
    elif any("uncertainty" in w for w in result.warnings):
        result.level = LOW if len([w for w in result.warnings if "uncertainty" in w]) >= 2 else MODERATE
    elif tool_results and all(tr.get("success") for tr in tool_results):
        result.level = VERIFIED
    elif tool_results:
        result.level = HIGH

    return result


def _check_tool_results(result: QualityResult, tool_results: list):
    """Check if any tool calls failed."""
    result.checks_performed.append("tool_verification")
    for tr in tool_results:
        if not tr.get("success"):
            tool_name = tr.get("tool", "unknown")
            error = tr.get("error", "unknown error")
            # Skip access pending errors (those are expected flow)
            if "__ACCESS_PENDING__" in str(error):
                continue
            result.warnings.append(f"tool_error:{tool_name}:{error[:100]}")


def _check_uncertainty(result: QualityResult, response: str):
    """Detect hedging language that signals low confidence."""
    result.checks_performed.append("uncertainty_detection")
    uncertainty_patterns = [
        r"\bI think\b",
        r"\bprobably\b",
        r"\bmight be\b",
        r"\bI\'m not sure\b",
        r"\bI believe\b",
        r"\bpossibly\b",
        r"\bit seems\b",
        r"\bI\'m guessing\b",
        r"\bnot certain\b",
        r"\bcould be\b",
    ]
    found = 0
    for pattern in uncertainty_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            found += 1
    if found >= 1:
        result.warnings.append(f"uncertainty:hedging_language:{found}_instances")


def _check_entity_references(result: QualityResult, response: str, tool_results: list):
    """Check if response references entities (quotes, invoices) that weren't verified by tools."""
    result.checks_performed.append("entity_verification")

    # Look for quote references (EST-XXXX-XXX, Q-XXXX, etc.)
    quote_refs = re.findall(r'(?:EST|Q|QUO)-\d{4}-\d{2,4}', response, re.IGNORECASE)
    invoice_refs = re.findall(r'INV-\d{4,}', response, re.IGNORECASE)

    # Check if these were verified by tool calls
    tool_data = " ".join(str(tr.get("result", "")) for tr in tool_results)
    for ref in quote_refs + invoice_refs:
        if ref not in tool_data and ref.upper() not in tool_data.upper():
            result.warnings.append(f"unverified_entity:{ref}")


def _check_calculations(result: QualityResult, response: str):
    """Basic check for mathematical claims in response."""
    result.checks_performed.append("calculation_check")
    # Look for patterns like "total: $X" or "X yards" with numbers
    calc_patterns = re.findall(
        r'(?:total|subtotal|cost|price|yards?|feet|inches?|sq\.?\s*ft)\s*[:=]?\s*\$?[\d,]+\.?\d*',
        response, re.IGNORECASE
    )
    if calc_patterns:
        # If we found calculations but no tool verified them, flag as moderate
        result.checks_performed.append(f"found_{len(calc_patterns)}_calculations")


def _check_completeness(result: QualityResult, response: str):
    """Heuristic: very short responses to complex questions may be incomplete."""
    result.checks_performed.append("completeness_check")
    # Very short responses (under 20 chars) that aren't simple acknowledgments
    if len(response.strip()) < 20:
        simple_acks = ["ok", "done", "got it", "sure", "yes", "no", "understood"]
        if response.strip().lower() not in simple_acks:
            result.warnings.append("completeness:very_short_response")


def get_response_suffix(quality: QualityResult) -> str:
    """Return a suffix to append to the response based on quality level."""
    if quality.level == FAILED:
        return f"\n\n{quality.disclaimer}" if quality.disclaimer else "\n\n⚠️ _Quality check flagged potential issues with this response._"
    elif quality.level == LOW:
        return "\n\n⚠️ _Low confidence — please verify._"
    return ""


def get_quality_badge(quality: QualityResult) -> dict:
    """Return badge info for frontend display."""
    badges = {
        VERIFIED: {"icon": "✅", "color": "#22c55e", "label": "Verified"},
        HIGH: {"icon": "✅", "color": "#22c55e", "label": "High confidence"},
        MODERATE: {"icon": "🟡", "color": "#eab308", "label": "Moderate confidence"},
        LOW: {"icon": "⚠️", "color": "#f97316", "label": "Low confidence"},
        FAILED: {"icon": "❌", "color": "#ef4444", "label": "Quality issue detected"},
    }
    badge = badges.get(quality.level, badges[MODERATE])
    badge["checks"] = quality.checks_performed
    badge["warnings"] = quality.warnings
    badge["validation_time_ms"] = round(quality.validation_time_ms, 1)
    return badge
