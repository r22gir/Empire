"""Review gate for scheduled desk output.

A task is marked done only when this gate passes. Canned templates,
raw ```tool blocks, empty results, and generic one-liners fail.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

TOOL_BLOCK_RE = re.compile(r"```\s*tool\b[\s\S]*?```", re.I)

CANNED_PHRASES = (
    "recommended: send payment reminders, escalate 30+ day overdue",
    "follow-up prepared for",
    "quote workflow initiated for",
    "process: measure → select fabric",
    "your order has been shipped. please check your tracking",
    "we have initiated your refund",
    "ticket auto-resolved",
    "3-day follow-up scheduled",
    "connect to accounting system for full financials",
    "this reflects in-session data only",
)

TOOL_FENCE_RE = re.compile(r"```\s*tool\b", re.I)
GENERIC_ONLY_RE = re.compile(
    r"^(overdue check: \d+ invoice\(s\) outstanding\.|"
    r"follow-up prepared for .+recommended actions)",
    re.I,
)


@dataclass
class ReviewVerdict:
    passed: bool
    reason: str


def review_desk_output(
    result_text: str | None,
    *,
    findings: list[dict] | None = None,
    require_named: bool = True,
) -> ReviewVerdict:
    text = (result_text or "").strip()
    if not text:
        return ReviewVerdict(False, "empty result")
    if text.startswith("No available provider could satisfy"):
        return ReviewVerdict(False, "provider unavailable")
    if text.startswith("FAILED:"):
        return ReviewVerdict(False, text[7:].strip() or "explicit failure")
    if TOOL_FENCE_RE.search(text) or TOOL_BLOCK_RE.search(text):
        return ReviewVerdict(False, "raw tool block not executed")
    lowered = text.lower()
    for phrase in CANNED_PHRASES:
        if phrase in lowered:
            return ReviewVerdict(False, f"canned template: {phrase[:48]}")
    if GENERIC_ONLY_RE.search(lowered) and len(text) < 200:
        return ReviewVerdict(False, "generic one-liner")
    named = findings or []
    if require_named and named:
        # At least one finding name must appear in the output.
        hits = 0
        for f in named:
            name = str(f.get("name") or "").strip()
            customer = str(f.get("customer") or "").strip()
            if name and name in text:
                hits += 1
            elif customer and customer != "Unknown" and customer in text:
                hits += 1
        if hits == 0:
            return ReviewVerdict(False, "findings not named in output")
    return ReviewVerdict(True, "ok")
