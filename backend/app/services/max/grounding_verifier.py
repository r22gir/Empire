"""
Grounding Verifier — Post-processing layer for web-sourced AI responses.
Strips hallucinated citations, flags unverifiable claims, and optionally
cross-checks via a second model.
"""
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("max.grounding")


@dataclass
class VerifiedResponse:
    """Result of grounding verification."""
    original: str
    verified: str
    claims_found: int = 0
    claims_verified: int = 0
    claims_stripped: int = 0
    phantom_citations_removed: int = 0


def verify_web_response(
    ai_response: str,
    tool_results: list[dict],
) -> VerifiedResponse:
    """
    Verify an AI response against the actual web content that was fetched.

    1. Collect all fetched web content from tool results (web_search snippets + web_read content)
    2. Find all URL citations in the AI response
    3. For each citation, check if the surrounding claim can be traced to the fetched content
    4. Strip phantom citations (URL cited but claim not in source)
    5. Flag unverifiable claims

    Args:
        ai_response: The raw AI response text
        tool_results: List of tool result dicts from the chat handler
    """
    if not tool_results:
        return VerifiedResponse(original=ai_response, verified=ai_response)

    # Step 1: Build a map of URL → fetched content
    source_content = _collect_source_content(tool_results)

    if not source_content:
        # No web content was fetched, nothing to verify
        return VerifiedResponse(original=ai_response, verified=ai_response)

    # Step 2: Find all citation patterns in the response
    citations = _extract_citations(ai_response)

    if not citations:
        # No citations to verify
        return VerifiedResponse(original=ai_response, verified=ai_response)

    # Step 3: Verify each citation against source content
    verified_text = ai_response
    claims_verified = 0
    claims_stripped = 0
    phantom_removed = 0

    for citation in citations:
        url = citation["url"]
        claim_text = citation["claim"]
        full_match = citation["full_match"]

        # Find the best matching source for this URL
        source_text = _find_source_for_url(url, source_content)

        if source_text is None:
            # URL was cited but we never fetched it — phantom citation
            logger.warning(f"Phantom citation: {url} was never fetched")
            verified_text = _strip_citation(verified_text, full_match, url)
            phantom_removed += 1
            claims_stripped += 1
            continue

        # Check if the claim can be grounded in the source
        if _claim_is_grounded(claim_text, source_text):
            claims_verified += 1
        else:
            # Claim not found in source — add "unverified" qualifier
            logger.warning(f"Ungrounded claim citing {url}: {claim_text[:80]}...")
            verified_text = _mark_unverified(verified_text, full_match)
            claims_stripped += 1

    return VerifiedResponse(
        original=ai_response,
        verified=verified_text,
        claims_found=len(citations),
        claims_verified=claims_verified,
        claims_stripped=claims_stripped,
        phantom_citations_removed=phantom_removed,
    )


def _collect_source_content(tool_results: list[dict]) -> dict[str, str]:
    """Build URL → content map from web_search and web_read results."""
    sources = {}

    for tr in tool_results:
        if not tr.get("success") or not tr.get("result"):
            continue

        result = tr["result"]
        tool_name = tr.get("tool", "")

        if tool_name == "web_search":
            # Collect snippets from search results
            for r in result.get("results", []):
                url = r.get("url", "")
                snippet = r.get("snippet", "")
                title = r.get("title", "")
                if url:
                    sources[url] = f"{title}\n{snippet}"

        elif tool_name == "web_read":
            url = result.get("url", "")
            content = result.get("content", "")
            if url and content:
                sources[url] = content

    return sources


def _extract_citations(text: str) -> list[dict]:
    """Extract all citation patterns from AI response text.

    Catches patterns like:
    - "According to [source](url), ..."
    - "... (Source: url)"
    - "... [url]"
    - "... (url)"
    - Inline URLs after claims
    """
    citations = []
    url_pattern = r'https?://[^\s\)\]<>\"\']{10,}'

    # Pattern 1: "According to [source](url), CLAIM"
    for m in re.finditer(
        r'(?:According to|Per|As reported by|As stated (?:by|on))\s+\[([^\]]+)\]\(((' + url_pattern + r'))\)[,:]?\s*([^.!?\n]{10,}[.!?])',
        text, re.IGNORECASE
    ):
        citations.append({
            "url": m.group(2),
            "claim": m.group(4).strip(),
            "full_match": m.group(0),
        })

    # Pattern 2: "CLAIM (Source: url)" or "CLAIM (url)"
    for m in re.finditer(
        r'([^.!?\n]{15,}[.!?])\s*\((?:Source:\s*)?(' + url_pattern + r')\)',
        text
    ):
        citations.append({
            "url": m.group(2),
            "claim": m.group(1).strip(),
            "full_match": m.group(0),
        })

    # Pattern 3: "According to URL, CLAIM"
    for m in re.finditer(
        r'(?:According to|Per)\s+(' + url_pattern + r')[,:]?\s*([^.!?\n]{10,}[.!?])',
        text, re.IGNORECASE
    ):
        citations.append({
            "url": m.group(1),
            "claim": m.group(2).strip(),
            "full_match": m.group(0),
        })

    # Deduplicate by full_match
    seen = set()
    unique = []
    for c in citations:
        if c["full_match"] not in seen:
            seen.add(c["full_match"])
            unique.append(c)

    return unique


def _find_source_for_url(cited_url: str, sources: dict[str, str]) -> str | None:
    """Find source content for a cited URL. Handles partial URL matches."""
    # Exact match
    if cited_url in sources:
        return sources[cited_url]

    # Partial match (URL might have trailing slash differences, etc.)
    cited_domain = _extract_domain(cited_url)
    for source_url, content in sources.items():
        if _extract_domain(source_url) == cited_domain:
            return content

    return None


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    m = re.search(r'https?://(?:www\.)?([^/]+)', url)
    return m.group(1).lower() if m else url.lower()


def _claim_is_grounded(claim: str, source_text: str) -> bool:
    """Check if a claim can be found in the source content.

    Uses keyword overlap rather than exact match, since AI paraphrases.
    A claim is considered grounded if enough of its key terms appear in the source.
    """
    # Extract meaningful words (>3 chars, not common stopwords)
    stopwords = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
        'her', 'was', 'one', 'our', 'out', 'has', 'have', 'had', 'this',
        'that', 'with', 'they', 'been', 'from', 'said', 'each', 'which',
        'their', 'will', 'other', 'about', 'many', 'then', 'them', 'would',
        'make', 'like', 'been', 'more', 'some', 'could', 'into', 'than',
        'also', 'according', 'based', 'source', 'states', 'noted', 'reported',
    }

    claim_words = set(
        w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', claim)
        if w.lower() not in stopwords
    )

    if not claim_words:
        return True  # No meaningful words to check

    source_lower = source_text.lower()
    matched = sum(1 for w in claim_words if w in source_lower)

    # Require at least 40% of key terms to appear in source
    ratio = matched / len(claim_words)
    return ratio >= 0.4


def _strip_citation(text: str, full_match: str, url: str) -> str:
    """Remove a phantom citation from the response."""
    # Remove the URL but keep the claim text
    replacement = re.sub(
        r'\s*\((?:Source:\s*)?' + re.escape(url) + r'\)',
        '',
        full_match
    )
    # Also remove "According to [source](url)," prefix if present
    replacement = re.sub(
        r'(?:According to|Per|As reported by)\s+\[[^\]]*\]\([^\)]*\)[,:]?\s*',
        '',
        replacement
    )
    return text.replace(full_match, replacement.strip())


def _mark_unverified(text: str, full_match: str) -> str:
    """Add 'unverified' qualifier to an ungrounded citation."""
    # Prepend "(unverified)" before the claim
    marked = f"(unverified) {full_match}"
    return text.replace(full_match, marked, 1)


def log_to_audit(
    user_query: str,
    verification: VerifiedResponse,
    model_used: str,
    response_time_ms: int = 0,
    channel: str = "chat",
    output_type: str = "response",
):
    """Log grounding verification result to the accuracy audit table."""
    try:
        from app.services.max.accuracy_monitor import accuracy_monitor
        accuracy_monitor.log_audit(
            user_query=user_query,
            response_text=verification.verified,
            verification=verification,
            model_used=model_used,
            response_time_ms=response_time_ms,
            channel=channel,
            output_type=output_type,
        )
    except Exception as e:
        logger.warning(f"Failed to log to accuracy audit: {e}")


async def cross_check_with_secondary_model(
    response: str,
    source_content: dict[str, str],
    ai_router=None,
) -> str:
    """Optional: Route response through a secondary model for fact-checking.

    Uses a cheaper/faster model (Claude Haiku or Ollama) to verify claims
    against the actual source content.
    """
    if not ai_router or not source_content:
        return response

    # Build a compact source summary for the fact-checker
    source_summary = ""
    for url, content in list(source_content.items())[:3]:
        source_summary += f"\n--- Source: {url} ---\n{content[:2000]}\n"

    if not source_summary:
        return response

    from app.services.max.ai_router import AIMessage, AIModel

    check_prompt = f"""You are a fact-checker. Compare the AI response below against the actual source content.

RESPONSE TO CHECK:
{response[:3000]}

ACTUAL SOURCE CONTENT:
{source_summary[:4000]}

Instructions:
1. Identify any claims in the response that are NOT supported by the source content
2. Identify any claims that CONTRADICT the source content
3. Return the corrected response with unsupported claims removed or marked as "[unverified]"
4. Keep all claims that ARE supported by the sources
5. If the response is accurate, return it unchanged
6. Be concise — return ONLY the corrected response text, nothing else"""

    try:
        # Use a fast/cheap model for fact-checking
        messages = [AIMessage(role="user", content=check_prompt)]
        result = await ai_router.chat(
            messages,
            model=AIModel.OLLAMA,  # Cheapest option
            system_prompt="You are a precise fact-checker. Only flag claims that clearly contradict or are absent from the source material."
        )
        if result and result.content and len(result.content) > 50:
            return result.content
    except Exception as e:
        logger.warning(f"Cross-check failed, returning original: {e}")

    return response
