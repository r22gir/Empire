"""Official-sources web search for Max (free-tier providers only).

Family editions (Max-e, Maxine) share this module with their own keys
and the 20% instance usage cap. Maxine never searches or stores Argos
Campestre legal or company details.
"""
from app.services.max.official_search.citations import (
    strip_invented_citations,
    verify_citations,
    verify_quoted_text,
)
from app.services.max.official_search.family import (
    family_search_guard,
    redact_maxine_results,
)
from app.services.max.official_search.footer import (
    attach_sources_footer,
    build_sources_footer,
    detect_reply_language,
)
from app.services.max.official_search.intent import (
    detect_language,
    is_official_intent,
)
from app.services.max.official_search.pipeline import (
    finalize_research_reply,
    official_page_char_cap,
    run_web_search,
)
from app.services.max.official_search.providers import (
    PROVIDER_ORDER,
    BraveProvider,
    DuckDuckGoProvider,
    ExaProvider,
    TavilyProvider,
    MiniMaxCodingPlanProvider,
    minimax_coding_plan_enabled,
    minimax_research_enabled,
    provider_fallback_order,
)
from app.services.max.official_search.trust_tiers import (
    TIER_OFFICIAL,
    TIER_UNVERIFIED,
    TIER_WIRE,
    classify_domain,
    filter_by_tiers,
    is_blocked,
    topic_allowlist,
)

__all__ = [
    "BraveProvider",
    "DuckDuckGoProvider",
    "ExaProvider",
    "PROVIDER_ORDER",
    "TIER_OFFICIAL",
    "TIER_UNVERIFIED",
    "TIER_WIRE",
    "TavilyProvider",
    "MiniMaxCodingPlanProvider",
    "is_blocked",
    "minimax_coding_plan_enabled",
    "attach_sources_footer",
    "build_sources_footer",
    "classify_domain",
    "detect_language",
    "detect_reply_language",
    "family_search_guard",
    "filter_by_tiers",
    "finalize_research_reply",
    "is_official_intent",
    "minimax_research_enabled",
    "official_page_char_cap",
    "provider_fallback_order",
    "redact_maxine_results",
    "run_web_search",
    "strip_invented_citations",
    "topic_allowlist",
    "verify_citations",
    "verify_quoted_text",
]
