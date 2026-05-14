"""
MAX Live Lookup Router — general answer confidence and freshness gate.

Runs BEFORE the main model call. Decides whether to route to live lookup
(web search, dedicated tools) or plain text.

This is a general routing policy, NOT a topic whitelist.
Weather, news, prices, laws, docs, public research are examples — not a closed list.
"""

import re
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class LiveLookupDecision:
    needs_lookup: bool
    reason: Literal[
        "freshness_risk",
        "source_specific",
        "verification_requested",
        "high_stakes",
        "low_confidence",
        "local_dynamic",
        "public_research",
        "user_requested_sources",
        "model_memory_conflict",
        "none",
    ]
    query: str
    preferred_tool: Optional[str]  # tool name | "minimax_web_search" | None
    topic_hint: Literal["weather", "docs", "legal", "product", "company", "financial", "news", "general", "unknown"]
    confidence_without_lookup: Literal["low", "medium", "high"]
    lookup_policy: Literal["required", "optional", "not_needed"]
    decision_notes: str


# ─────────────────────────────────────────────────────────────────────────────
# String pattern sets (plain substring match)
# ─────────────────────────────────────────────────────────────────────────────

_DYNAMIC_SUBJECTS = [
    "stock", "stocks", "crypto", "cryptocurrency", "market", "markets",
    "weather", "forecast", "schedule", "schedules", "ranking", "rankings",
    "availability", "service status", "prices", "pricing",
]

_HIGH_STAKES = [
    "legal", "law", "laws", "regulation", "regulations", "compliance",
    "contract", "contracts", "lawyer", "attorney", "court",
    "medical", "medicine", "medication", "diagnosis", "treatment", "health",
    "financial", "finance", "investment", "taxes", "tax", "irs",
    "immigration", "visa", "residency", "citizenship",
    "insurance", "claim", "coverage", "policy",
    "safety", "hazard", "dangerous",
]

_LOCAL_DYNAMIC = [
    "near me", "nearby", "local",
]

_SOURCE_KEYWORDS = [
    "docs", "documentation", "api reference", "release notes",
    "changelog", "investor relations", "product page", "policy page",
    "legal source", "paper", "report",
]

# Truly specialized/niche jargon that warrants low-confidence on question starters
_SPECIALIZED_JARGON = [
    "saml", "thrift", "prometheus", "grafana", "openssl", "gpg",
    "grpc", "rag", "fine-tune", "fine-tuning", "asyncio", "gil",
    "multiprocessing", "helm", "terraform", "pulumi", "ansible",
    "elastic", "opensearch", "database schema",
    "webpack", "vite", "rollup",
    "rxjava", "coroutines", "flyweight", "actor model",
    "raft consensus", "paxos",
]

_TOPIC_WEATHER = ["weather", "rain", "snow", "forecast"]
_TOPIC_LEGAL = ["legal", "law", "regulation", "contract", "lawyer"]
_TOPIC_DOCS = ["docs", "documentation", "api reference", "reference docs"]
_TOPIC_FINANCIAL = ["stock", "crypto", "market data", "nasdaq", "dow jones"]
_TOPIC_NEWS = ["news", "recent events", "what happened"]


# ─────────────────────────────────────────────────────────────────────────────
# Regex patterns (compiled once for efficiency)
# ─────────────────────────────────────────────────────────────────────────────

def _re(pat: str) -> re.Pattern:
    return re.compile(pat, re.IGNORECASE)

_REGEX = {
    "freshness": [
        _re(r"\btoday\b"), _re(r"\bnow\b"), _re(r"\blatest\b"),
        _re(r"\brecent\b"), _re(r"\bcurrent\b"), _re(r"\bthis week\b"),
        _re(r"\btomorrow\b"), _re(r"\byesterday\b"), _re(r"\bthis month\b"),
        _re(r"\bthis morning\b"), _re(r"\bup.to.date\b"),
        _re(r"\bcurrent\s+\w+"), _re(r"\blatest\s+\w+"),
    ],
    "verification": [
        _re(r"\bare you sure\?"), _re(r"\bverify\b"), _re(r"\bcheck\b"),
        _re(r"\blook it up\b"), _re(r"\blook up\b"), _re(r"\bconfirm\b"),
        _re(r"\bfind out\b"), _re(r"\bsearch\b"), _re(r"\bcompare current\b"),
        _re(r"\bwhat changed\b"), _re(r"\bis this still\b"),
        _re(r"\bwas this still\b"), _re(r"\bdoes this still\b"),
        _re(r"\bhas this changed\b"), _re(r"\bhow recent\b"),
    ],
    "local_dynamic": [
        _re(r"\bhours\b"), _re(r"\bopen\s+now\b"), _re(r"\bopen right now\b"),
        _re(r"\baddress\b"), _re(r"\bdirections?\b"),
        _re(r"\bweather\s+in\b"), _re(r"\bweather\s+like\s+in\b"),
        _re(r"\brain\S*\s+in\b"), _re(r"\bsnow\S*\s+in\b"),
        _re(r"\brestaurants?\s+near\b"), _re(r"\bevents?\s+in\b"),
    ],
    "public_research": [
        _re(r"\brecommendations?\b"), _re(r"\boptions?\b"), _re(r"\btrends?\b"),
        _re(r"\bcompetitors?\b"), _re(r"\breviews?\b"),
        _re(r"\bwhat'?s?\s+out\s+there\b"),
        _re(r"\bwhat\s+do\s+people\s+(say|think)\b"),
        _re(r"\bcompar(e|ing)\b"), _re(r"\bbest\s+current\b"),
        _re(r"\btop\s+current\b"), _re(r"\bavailable\s+options?\b"),
        _re(r"\bgood\s+alternatives?\b"),
    ],
    "source_request": [
        _re(r"\bcite\b"), _re(r"\bsource\b"), _re(r"\blink\b"),
        _re(r"\breference\b"), _re(r"\bcitation\b"),
        _re(r"\bwhere\s+did\s+you\s+get\b"),
        _re(r"\bwhere\s+did\s+this\s+come\s+from\b"),
        _re(r"\bwhere\s+does\s+this\s+info\b"),
    ],
    "question_starters": [
        _re(r"^what\s+is\s+(a\s+)?"), _re(r"^how\s+do\s+i\s+"),
        _re(r"^can\s+you\s+tell\s+me\s+about\s+"),
        _re(r"^explain\s+(what\s+)?"), _re(r"^describe\s+"),
        _re(r"^what'?s?\s+a\s+"),
    ],
}

_URL_RE = _re(r"https?://")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _in(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if p in text:
            return True
    return False


def _re_test(text: str, patterns: list[re.Pattern]) -> bool:
    for p in patterns:
        if p.search(text):
            return True
    return False


def _extract_topic_hint(message: str, reason: str) -> Literal["weather", "docs", "legal", "product", "company", "financial", "news", "general", "unknown"]:
    msg = message.lower()
    if _in(msg, _TOPIC_WEATHER):
        return "weather"
    if _in(msg, _TOPIC_LEGAL):
        return "legal"
    if _in(msg, _TOPIC_DOCS):
        return "docs"
    if _in(msg, _TOPIC_FINANCIAL):
        return "financial"
    if _in(msg, _TOPIC_NEWS):
        return "news"
    if reason == "source_specific":
        if _in(msg, _TOPIC_DOCS):
            return "docs"
        if _in(msg, ["company", "inc", "corp", "ltd"]):
            return "company"
        if _in(msg, ["product", "pricing", "features"]):
            return "product"
    return "general"


def _extract_query(message: str) -> str:
    text = message
    strip_prefixes = [
        r"^(what is|what's|what are|what was|what were)\s+(the\s+)?",
        r"^(who is|who's|who are|who was|who were)\s+(the\s+)?",
        r"^(how do i|how does|how can i|how should i)\s+",
        r"^(how much|how many)\s+",
        r"^(is it|are there|can you|please|tell me)\s+",
        r"^(tell me|can you|i need to|i want to)\s+",
        r"^(explain|describe|define)\s+(what\s+)?",
        r"^(look up|look it up|find|search for|search)\s+",
    ]
    for p in strip_prefixes:
        text = re.sub(p, "", text, flags=re.IGNORECASE)
    filler = ["the ", "a ", "an ", "please ", "actually ", "really ", "currently "]
    for f in filler:
        if f in ("a ", "an "):
            # Only strip a/an from START of query — not from inside words like Iran, Canada
            if text.startswith(f):
                text = text[len(f):]
            # else: don't strip a/an from middle of query
        else:
            text = text.replace(f, " ")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 200:
        text = text[:200]
    return text or message


def should_live_lookup(message: str, context: dict) -> LiveLookupDecision:
    """
    Decide whether a user message requires live external lookup.

    message: the user's input text
    context: dict with optional keys like "image_filename", "desk", "conversation_id"

    Returns LiveLookupDecision with full routing metadata.
    """
    msg_lower = message.lower()
    reasons: list[str] = []
    confidence: Literal["low", "medium", "high"] = "high"
    lookup_policy: Literal["required", "optional", "not_needed"] = "not_needed"
    preferred_tool: Optional[str] = "minimax_web_search"
    notes_parts: list[str] = []

    # ── 1. Freshness risk ──────────────────────────────────────────────
    if _re_test(msg_lower, _REGEX["freshness"]):
        reasons.append("freshness_risk")
        confidence = "low"
        lookup_policy = "required"
        notes_parts.append("freshness modifier detected")

    if _in(msg_lower, _DYNAMIC_SUBJECTS):
        reasons.append("freshness_risk")
        if confidence != "low":
            confidence = "medium"
            lookup_policy = "required"
        notes_parts.append("dynamic subject")

    # ── 2. Source-specific ─────────────────────────────────────────────
    if _URL_RE.search(msg_lower):
        reasons.append("source_specific")
        lookup_policy = "required"
        notes_parts.append("URL in message")

    if _in(msg_lower, _SOURCE_KEYWORDS):
        reasons.append("source_specific")
        lookup_policy = "required"
        notes_parts.append("named specific source")

    # ── 3. Verification requested ───────────────────────────────────────
    if _re_test(msg_lower, _REGEX["verification"]):
        reasons.append("verification_requested")
        lookup_policy = "required"
        notes_parts.append("verification requested")

    # ── 4. High-stakes domains ───────────────────────────────────────────
    if _in(msg_lower, _HIGH_STAKES):
        reasons.append("high_stakes")
        lookup_policy = "required"
        notes_parts.append("high-stakes domain")

    # ── 5. Local/dynamic ────────────────────────────────────────────────
    if _in(msg_lower, _LOCAL_DYNAMIC):
        reasons.append("local_dynamic")
        lookup_policy = "required"
        notes_parts.append("local dynamic data")

    if _re_test(msg_lower, _REGEX["local_dynamic"]):
        if "local_dynamic" not in reasons:
            reasons.append("local_dynamic")
        lookup_policy = "required"
        notes_parts.append("local dynamic pattern")

    # ── 6. Public research ─────────────────────────────────────────────
    if _re_test(msg_lower, _REGEX["public_research"]):
        reasons.append("public_research")
        lookup_policy = "required"
        notes_parts.append("public research signal")

    # ── 7. User requested sources ──────────────────────────────────────
    if _re_test(msg_lower, _REGEX["source_request"]):
        reasons.append("user_requested_sources")
        lookup_policy = "required"
        notes_parts.append("sources requested")

    # ── 8. Low confidence ─────────────────────────────────────────────
    if _re_test(msg_lower, _REGEX["question_starters"]):
        if _in(msg_lower, _SPECIALIZED_JARGON):
            reasons.append("low_confidence")
            if lookup_policy == "not_needed":
                lookup_policy = "optional"
            notes_parts.append("specialized jargon + question starter")

    if reasons and lookup_policy == "not_needed":
        lookup_policy = "optional"

    needs_lookup = lookup_policy in ("required", "optional")
    reason = reasons[0] if reasons else "none"
    topic_hint = _extract_topic_hint(message, reason)
    query = _extract_query(message) if needs_lookup else ""
    decision_notes = "; ".join(notes_parts) if notes_parts else "no specific risk detected"

    return LiveLookupDecision(
        needs_lookup=needs_lookup,
        reason=reason,
        query=query,
        preferred_tool=preferred_tool,
        topic_hint=topic_hint,
        confidence_without_lookup=confidence,
        lookup_policy=lookup_policy,
        decision_notes=decision_notes,
    )