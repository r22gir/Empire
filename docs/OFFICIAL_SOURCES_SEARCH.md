# Official-sources web search (Max)

Trusted, low-noise web research for Max. Free tiers only — no paid search
provider and no credit card.

Base: `deploy/pr82-84-85` (includes #116 / #117).

## What changed

Search used DuckDuckGo HTML (5 results, 10 max) with an optional Brave
fallback. Research read up to 8 pages, kept 3–5, and truncated each to
2,500 characters. There was no official-source mode, no domain tiers, and
the Sources footer was left to the model (English-only). Voice URL
stripping was prompt-only.

This module adds:

1. A provider layer with fallbacks
2. Trust tiers and topic allowlists
3. Official-intent detection (English / Spanish)
4. Citation verification (fetched URLs + quote check)
5. A code-built Sources / Fuentes footer
6. URL stripping in code for voice / Telegram / phone / SMS
7. A 6–8k character page cap for official / long primary documents
8. Optional free authoritative API tools
9. MiniMax built-in `web_search` **off** for research
10. Family-edition isolation (Max-e / Maxine) and the 20% usage cap

## Provider order (Dell live tests, 2026-10)

DuckDuckGo HTML **resets connections from the Dell** (10 of 12 queries
fell back). `BRAVE_API_KEY` is already set on the studio backend.

| Order | Provider | Env | Notes |
| --- | --- | --- | --- |
| 1 | Brave Search | `BRAVE_API_KEY` | **On when the key exists and the monthly free-credit cap is open.** Goggles + allowlist `site:` boosts + hard post-filter. Hard cap `BRAVE_MONTHLY_FREE_REQUESTS` (default **900**, inside Brave's $5 / ~1,000 req credit). Count is persisted per edition, UTC calendar month. At cap, Brave is skipped automatically. |
| 1b | MiniMax Token Plan MCP | `MINIMAX_API_KEY` | `POST /v1/coding_plan/search` `{"q": query}`. Raw 10 hits, **no domain filter**. Merged/deduped with Brave, then trust-filtered. Included in plan quota. |
| 2 | Exa Instant | `EXA_API_KEY` | Free $10/mo fallback. |
| 3 | Tavily basic | `TAVILY_API_KEY` | 1,000 free credits/mo fallback. `include_domains` hard filter. |
| last | DuckDuckGo HTML | none | Last resort. Unreliable from Dell. |

**Do not** use the MiniMax Responses API server-tool `web_search` as an
answer engine: slow, sometimes skips searching, stale/memory answers.
`MINIMAX_WEB_SEARCH_FOR_RESEARCH` stays off. Research prompts always
include **today's calendar date** so the model cannot invent a stale year.

Family editions do **not** inherit the workroom key:

- Max-e: `EXA_API_KEY_MAX_E` / `TAVILY_API_KEY_MAX_E` / `BRAVE_API_KEY_MAX_E`
- Maxine: `EXA_API_KEY_MAXINE` / `TAVILY_API_KEY_MAXINE` / `BRAVE_API_KEY_MAXINE`

`SERPAPI_API_KEY`, `GOOGLE_CSE_API_KEY`, and `BING_API_KEY` are unused
(paid). Social / SEO / aggregator noise (Facebook, YouTube, Reddit,
IndiaMART, Scribd, tax-prep sellers, rehab-center sites, MarketWatch-style
aggregators) is blocked before tiering. Pages are fetched before they
may be cited. If no Tier 1 host remains: **No official source found.**

Fail-closed: if every **enabled** provider errors, `web_search` returns
`success=false`. An empty-but-healthy provider continues to the next.
The Brave monthly counter never exceeds the cap (reserve-before-HTTP).
A store error skips Brave rather than risking a paid overage. The
usage screen Free-Tier Quotas tab shows this month's Brave count.

## Trust tiers

| Tier | Meaning | Badge |
| --- | --- | --- |
| 1 | `.gov` / `.mil` / `.edu`, regulators, courts, standards bodies, the entity's own domain | Official / Oficial |
| 2 | Established wires and journals (Reuters, AP, BBC, NPR, Nature, …) | Not official / No oficial |
| 3 | Everything else | Not official / No oficial (unverified) |

Topic allowlists (law, health, finance, science, education) bias Tier 1
hosts. Official mode is primary-source-first and widens only when Tier 1
is empty. Factual claims prefer 2+ independent sources (max one result
per registrable domain). Date filters: `start_date` / `end_date`.

## Official intent (EN / ES)

Triggers strict mode: `official`, `oficial`, `gobierno`, `.gov`,
`fuente oficial`, `sitio oficial`, `primary source`, …

If no Tier 1 host is found, Max says so plainly and may show lower tiers
labeled unverified.

## Citations and footer

- Only URLs that were actually fetched may be cited.
- Quoted text must appear in fetched page text.
- Invented links are stripped in code.

The Sources footer is built in code (the model does not write it):

```
Sources
1. [CDC Influenza](https://www.cdc.gov/flu) — cdc.gov — 2024-08-15 — Official — read
```

Spanish replies use `Fuentes`, `Oficial` / `No oficial`, `leído` /
`solo fragmento`.

Voice / Telegram / phone / SMS: raw URLs are stripped in code. The
spoken reply keeps source **names** only.

Official / long primary documents use a 6–8k character page cap
(`OFFICIAL_SEARCH_PAGE_CHARS`, default 8000). Other pages stay at 2,500.

## Authoritative API tools (optional, free)

| Tool | Service | Key |
| --- | --- | --- |
| `congress_search` | Congress.gov v3 | `DATA_GOV_API_KEY` or `CONGRESS_GOV_API_KEY` |
| `regulations_search` | Regulations.gov v4 | `DATA_GOV_API_KEY` or `REGULATIONS_GOV_API_KEY` |
| `pubmed_search` | PubMed E-utilities | none (`PUBMED_EMAIL` recommended) |
| `sec_edgar_search` | SEC EDGAR | `SEC_EDGAR_USER_AGENT` (required by SEC) |
| `wikipedia_search` | Wikipedia / Wikidata | none |
| `fact_check_search` | Google Fact Check | `GOOGLE_FACTCHECK_API_KEY` (optional; off without it) |

## Family editions

Same module. Own keys and limits. The 20% instance usage cap is honored
(`INSTANCE_USAGE_CAP_PCT`, default 20 on Max-e / Maxine). A spent cap
refuses further official search (heavy work).

Maxine never searches or stores Argos Campestre legal or company
details. Matching queries fail closed and return no results.

## Env reference

See `backend/.env.example` (Official-sources search section).
