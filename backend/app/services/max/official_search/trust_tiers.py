"""Trust tiers, topic allowlists, and primary-source-first filtering."""
from __future__ import annotations

from typing import Iterable, Optional
from urllib.parse import urlparse

TIER_OFFICIAL = 1
TIER_WIRE = 2
TIER_UNVERIFIED = 3

TIER_LABELS = {
    "en": {1: "Official", 2: "Not official", 3: "Not official"},
    "es": {1: "Oficial", 2: "No oficial", 3: "No oficial"},
}

# Registrable suffixes that are always Tier 1.
_TIER1_SUFFIXES = (".gov", ".mil", ".edu", ".gob", ".gob.mx", ".gob.co", ".gov.uk")

# Named regulators, courts, standards bodies, and primary-data hosts.
TIER1_HOSTS = frozenset({
    "congress.gov", "govinfo.gov", "regulations.gov", "federalregister.gov",
    "supremecourt.gov", "uscourts.gov", "justice.gov", "whitehouse.gov",
    "house.gov", "senate.gov", "gao.gov", "cbo.gov", "loc.gov",
    "cdc.gov", "nih.gov", "nlm.nih.gov", "ncbi.nlm.nih.gov", "fda.gov",
    "cms.gov", "hhs.gov", "who.int",
    "sec.gov", "treasury.gov", "federalreserve.gov", "irs.gov", "cftc.gov",
    "fdic.gov", "occ.gov", "bls.gov", "census.gov", "bea.gov",
    "nist.gov", "nasa.gov", "noaa.gov", "nsf.gov", "energy.gov", "epa.gov",
    "ed.gov", "state.gov", "dhs.gov", "defense.gov", "va.gov",
    "iso.org", "iec.ch", "ietf.org", "w3.org", "oasis-open.org",
    "un.org", "europa.eu", "ec.europa.eu", "who.int",
    "pubmed.ncbi.nlm.nih.gov",
})

TIER2_HOSTS = frozenset({
    "reuters.com", "apnews.com", "ap.org", "bbc.com", "bbc.co.uk",
    "npr.org", "pbs.org", "nytimes.com", "wsj.com", "washingtonpost.com",
    "theguardian.com", "ft.com", "bloomberg.com",
    "nature.com", "science.org", "sciencemag.org", "nejm.org", "thelancet.com",
    "associatedpress.com",
    "wikipedia.org", "wikidata.org",
})

TOPIC_ALLOWLISTS: dict[str, tuple[str, ...]] = {
    "law": (
        "congress.gov", "govinfo.gov", "regulations.gov", "federalregister.gov",
        "supremecourt.gov", "uscourts.gov", "justice.gov", "house.gov", "senate.gov",
    ),
    "health": (
        "cdc.gov", "nih.gov", "nlm.nih.gov", "ncbi.nlm.nih.gov", "fda.gov",
        "cms.gov", "hhs.gov", "who.int", "pubmed.ncbi.nlm.nih.gov",
    ),
    "finance": (
        "sec.gov", "treasury.gov", "federalreserve.gov", "irs.gov",
        "cftc.gov", "fdic.gov", "bls.gov", "bea.gov", "census.gov",
    ),
    "science": (
        "nist.gov", "nasa.gov", "noaa.gov", "nsf.gov", "energy.gov",
        "epa.gov", "pubmed.ncbi.nlm.nih.gov",
    ),
    "education": ("ed.gov",),
}

_TOPIC_HINTS = (
    ("law", ("law", "bill", "statute", "regulation", "court", "ley", "decreto", "norma")),
    ("health", ("health", "cdc", "fda", "nih", "pubmed", "salud", "vacuna", "disease")),
    ("finance", ("sec", "edgar", "irs", "tax", "impuesto", "treasury", "fed ")),
    ("science", ("nist", "nasa", "noaa", "climate", "standard")),
    ("education", ("education", "educaci", "department of education")),
)


def hostname(url: str) -> str:
    host = (urlparse(url or "").hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def registrable_domain(url: str) -> str:
    host = hostname(url)
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"gov", "gob", "ac", "co", "org", "com", "edu"} and len(parts[-1]) <= 3:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def classify_domain(url: str, *, entity_domain: str | None = None) -> int:
    """Return 1 (official), 2 (established wire), or 3 (unverified)."""
    host = hostname(url)
    if not host:
        return TIER_UNVERIFIED
    entity = (entity_domain or "").lower().lstrip(".")
    if entity and (host == entity or host.endswith("." + entity)):
        return TIER_OFFICIAL
    if any(host == h or host.endswith("." + h) for h in TIER1_HOSTS):
        return TIER_OFFICIAL
    if any(host.endswith(suf) for suf in _TIER1_SUFFIXES):
        return TIER_OFFICIAL
    if any(host == h or host.endswith("." + h) for h in TIER2_HOSTS):
        return TIER_WIRE
    return TIER_UNVERIFIED


def detect_topic(query: str) -> Optional[str]:
    blob = (query or "").lower()
    for topic, hints in _TOPIC_HINTS:
        if any(h in blob for h in hints):
            return topic
    return None


def topic_allowlist(query: str, *, entity_domain: str | None = None) -> list[str]:
    topic = detect_topic(query)
    hosts = list(TOPIC_ALLOWLISTS.get(topic or "", ()))
    if entity_domain:
        hosts.append(entity_domain.lower().lstrip("."))
    # Always include suffix-class primaries via host list + .gov/.mil/.edu filter.
    if not hosts:
        hosts = sorted(TIER1_HOSTS)
    # Dedup, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for host in hosts:
        key = host.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def is_allowlisted(url: str, allowlist: Iterable[str], *, entity_domain: str | None = None) -> bool:
    host = hostname(url)
    if classify_domain(url, entity_domain=entity_domain) == TIER_OFFICIAL:
        if not allowlist:
            return True
        if any(host == a or host.endswith("." + a) for a in allowlist):
            return True
        # Suffix-class official (.gov/.mil/.edu) always counts in official mode.
        if any(host.endswith(suf) for suf in _TIER1_SUFFIXES):
            return True
        if any(host == h or host.endswith("." + h) for h in TIER1_HOSTS):
            return True
    return False


def one_per_domain(results: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in results:
        domain = registrable_domain(str(item.get("url") or ""))
        if not domain or domain in seen:
            continue
        seen.add(domain)
        out.append(item)
    return out


def filter_by_tiers(
    results: list[dict],
    *,
    official: bool,
    query: str = "",
    entity_domain: str | None = None,
    widen: bool = True,
    max_results: int = 10,
) -> dict:
    """Primary-source-first. Widen to lower tiers only when Tier 1 is empty.

    Official mode returns only allowlisted / Tier 1 hosts unless widening
    is needed, in which case lower tiers are labeled unverified.
    """
    annotated: list[dict] = []
    for item in results or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        row = dict(item)
        row["tier"] = classify_domain(url, entity_domain=entity_domain)
        row["domain"] = hostname(url)
        annotated.append(row)

    allow = topic_allowlist(query, entity_domain=entity_domain) if official else []
    tier1 = [
        r for r in annotated
        if r["tier"] == TIER_OFFICIAL and (
            not official or is_allowlisted(r["url"], allow, entity_domain=entity_domain)
        )
    ]
    tier1 = one_per_domain(tier1)
    widened = False
    picked = list(tier1)
    if official and not picked and widen:
        widened = True
        lower = [r for r in annotated if r["tier"] != TIER_OFFICIAL]
        picked = one_per_domain(lower)
    elif not official:
        picked = one_per_domain(annotated)

    picked = picked[:max_results]
    return {
        "results": picked,
        "tier1_count": sum(1 for r in picked if r.get("tier") == TIER_OFFICIAL),
        "widened": widened,
        "independent": len({registrable_domain(r.get("url") or "") for r in picked}) >= 2,
        "official_mode": official,
        "no_tier1": official and not any(r.get("tier") == TIER_OFFICIAL for r in picked),
    }


def date_in_range(value: str | None, start: str | None, end: str | None) -> bool:
    if not value:
        return not start and not end
    if start and value < start:
        return False
    if end and value > end:
        return False
    return True
