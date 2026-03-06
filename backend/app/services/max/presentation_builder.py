"""
Presentation Builder — generates structured presentation JSON via AI + Unsplash images.
Called by POST /max/present endpoint.
"""

import json
import os
from datetime import datetime
from typing import Optional

import httpx

from app.services.max.ai_router import ai_router, AIMessage, AIModel

PRESENTATION_SYSTEM_PROMPT = """You are a presentation builder. Given a topic, web research results, and optionally source content, create a rich, professional presentation grounded in REAL current data.

CRITICAL RULES — ACCURACY:
1. **NEVER fabricate statistics, percentages, survey results, or numerical data.** If the web search results don't contain specific numbers, DO NOT invent them. Use qualitative descriptions instead.
2. **NEVER fabricate chart data.** Charts MUST use real numbers from the web search results provided. If no real numerical data is available, set "charts" to an empty array []. An empty chart array is ALWAYS better than fake data.
3. **Sources MUST come from the web search results provided** — use the exact URLs given. NEVER fabricate URLs or source names.
4. **Do not present opinions or estimates as facts.** If you're estimating, explicitly say "estimated" or "approximate".

IMPORTANT: You will receive web search results with real articles and snippets. Use this data to make your presentation factually accurate and current.

Return ONLY valid JSON with this exact structure — no markdown fences, no explanation:
{
  "title": "Presentation title",
  "subtitle": "Brief subtitle",
  "sections": [
    {"heading": "Section heading", "content": "Markdown content (use **bold**, bullet lists, etc.)", "type": "text"},
    {"heading": "Key Points", "content": "- Point 1\\n- Point 2\\n- Point 3", "type": "bullets"},
    {"heading": "Important", "content": "A highlighted callout or key stat", "type": "highlight"}
  ],
  "charts": [
    {"title": "Chart title", "type": "bar", "headers": ["Label1", "Label2"], "rows": [["Category", 10, 20]]}
  ],
  "sources": [
    {"title": "Source name", "url": "https://...", "description": "Brief description"}
  ],
  "image_queries": ["search term for relevant image 1", "search term 2"],
  "video_queries": ["YouTube search term for relevant video 1", "search term 2"]
}

Rules:
- Include 4-6 sections with a mix of types (text, bullets, highlight)
- Charts: ONLY include if you have REAL data from the web search results. If the search results contain specific numbers (market sizes, poll results, growth figures), use those exact numbers. Otherwise, use an EMPTY charts array. Never approximate or guess chart values.
- Include 2-3 image_queries — CRITICAL: queries must be SPECIFIC and CONTEXTUALLY CORRECT. Never use single ambiguous words. For software topics, include "software" or "interface" or "screenshot" in the query. Example: "Grasshopper Rhino 3D parametric design software interface", NOT just "grasshopper" (which would return bug photos). Always disambiguate.
- Include 1-2 video_queries for relevant clips or explainer videos — same disambiguation rules apply
- Use CURRENT facts and data from the web search results — do NOT rely on training data for recent events
- For current events: include a timeline or chronology section
- Make content informative, specific, and data-driven — but NEVER invent data points

WINDOW TREATMENT / DRAPERY TOPICS:
When the topic involves window treatments, drapery, curtains, or upholstery:
- Include SPECIFIC pricing per linear/square foot or per panel based on market rates
- Break down costs: fabric ($25-150/yd by grade), lining ($8-14/yd), fabrication ($50/hr), hardware ($15-75/ft), installation ($85-150/window)
- Include a pricing comparison chart with 3 tiers: Essential, Designer, Premium
- Recommend specific fabric types (linen, velvet, silk blend, performance polyester) with trade-offs
- Include a "What's Included" section listing all components
- Include installation timeline and process steps
- Be specific about measurements, fullness ratios (2-2.5x), and stackback calculations
- Image queries should include "luxury drapery interior design" and specific treatment types"""


async def fetch_images(queries: list[str], count_per_query: int = 1) -> list[dict]:
    """Fetch images from Unsplash for the given search queries.

    Returns dicts with Unsplash-compliant attribution:
    - Hotlinked URLs (direct from Unsplash CDN)
    - Photographer name + profile link
    - Unsplash attribution link
    - Download endpoint triggered per Unsplash guidelines
    """
    unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not unsplash_key:
        return []

    images = []
    async with httpx.AsyncClient(timeout=10) as client:
        headers = {"Authorization": f"Client-ID {unsplash_key}"}
        for query in queries[:3]:
            try:
                resp = await client.get(
                    "https://api.unsplash.com/search/photos",
                    params={"query": query, "per_page": count_per_query, "orientation": "landscape"},
                    headers=headers,
                )
                if resp.status_code != 200:
                    continue
                photos = resp.json().get("results", [])
                for p in photos[:count_per_query]:
                    # Trigger download event (Unsplash API guideline)
                    download_url = p.get("links", {}).get("download_location")
                    if download_url:
                        try:
                            await client.get(download_url, headers=headers)
                        except Exception:
                            pass
                    images.append({
                        "url": p["urls"]["regular"],
                        "alt": p.get("alt_description", query),
                        "credit": p["user"]["name"],
                        "credit_url": p["user"]["links"]["html"] + "?utm_source=empirebox&utm_medium=referral",
                        "unsplash_url": p["links"]["html"] + "?utm_source=empirebox&utm_medium=referral",
                    })
            except Exception:
                continue
    return images


def _parse_ddg_results(html: str, max_results: int) -> list:
    """Parse DuckDuckGo HTML search results into structured data."""
    import re
    from urllib.parse import unquote
    results = []
    blocks = re.findall(r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
    for i, (url, title_html) in enumerate(blocks[:max_results]):
        actual_match = re.search(r'uddg=([^&]+)', url)
        actual_url = unquote(actual_match.group(1)) if actual_match else url
        title = re.sub(r'<[^>]+>', '', title_html).strip()
        snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
        if title and actual_url:
            results.append({"title": title, "url": actual_url, "snippet": snippet})
    return results


def _brave_search(query: str, num_results: int = 8) -> list[dict]:
    """Search via Brave Search API (free tier: 2000 queries/month)."""
    brave_key = os.environ.get("BRAVE_API_KEY", "")
    if not brave_key:
        return []
    resp = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": num_results},
        headers={"X-Subscription-Token": brave_key, "Accept": "application/json"},
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    results = []
    for r in data.get("web", {}).get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("description", ""),
        })
    return results[:num_results]


def _web_research_sync(topic: str) -> str:
    """Synchronous web search — DDG HTML endpoint with Brave fallback."""
    results = []

    # Primary: DDG HTML endpoint
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": topic},
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            },
            timeout=10,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            results = _parse_ddg_results(resp.text, 8)
    except Exception as e:
        print(f"[PresentationBuilder] DDG HTML failed: {e}")

    # Fallback: Brave Search API
    if not results:
        try:
            results = _brave_search(topic, 8)
        except Exception as e:
            print(f"[PresentationBuilder] Brave search failed: {e}")

    if not results:
        return ""

    lines = []
    for r in results:
        lines.append(f"**{r['title']}**\n{r['snippet']}\nURL: {r['url']}\n")
    return "\n".join(lines)


def _fetch_videos_sync(queries: list[str], max_per_query: int = 2) -> list[dict]:
    """Synchronous video search via DDG HTML."""
    videos = []
    for query in queries[:2]:
        try:
            resp = httpx.get(
                "https://html.duckduckgo.com/html/",
                params={"q": f"{query} site:youtube.com"},
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                },
                timeout=10,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                continue
            parsed = _parse_ddg_results(resp.text, max_per_query)
            for r in parsed:
                if "youtube.com" in r["url"] or "youtu.be" in r["url"]:
                    videos.append({
                        "title": r["title"],
                        "url": r["url"],
                        "thumbnail": "",
                        "duration": "",
                        "publisher": "",
                    })
        except Exception:
            continue
    return videos


async def build_presentation(
    topic: str,
    source_content: Optional[str] = None,
    image_count: int = 3,
) -> dict:
    """Generate a structured presentation for the given topic.

    Returns a dict with title, subtitle, sections, images, charts, sources, videos, metadata.
    """
    import asyncio
    # Step 1: Web research for current data (run in thread to avoid blocking event loop)
    web_data = await asyncio.to_thread(_web_research_sync, topic)

    # Build the user message
    user_msg = f"Create a presentation about: {topic}"
    if web_data:
        user_msg += f"\n\n--- WEB SEARCH RESULTS (use these for current, accurate data) ---\n{web_data[:4000]}"
    if source_content:
        user_msg += f"\n\n--- ADDITIONAL SOURCE CONTENT ---\n{source_content[:3000]}"

    # Call AI (prefer Grok for web knowledge)
    response = await ai_router.chat(
        messages=[AIMessage(role="user", content=user_msg)],
        system_prompt=PRESENTATION_SYSTEM_PROMPT,
    )

    # Parse JSON response
    raw = response.content.strip()
    # Strip markdown fences if the model wraps them
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: wrap raw text as a single section
        data = {
            "title": topic,
            "subtitle": "Generated presentation",
            "sections": [{"heading": "Overview", "content": raw[:2000], "type": "text"}],
            "charts": [],
            "sources": [],
            "image_queries": [topic],
        }

    # Fetch images from Unsplash using AI-suggested queries
    image_queries = data.pop("image_queries", [topic])
    images = await fetch_images(image_queries, count_per_query=max(1, image_count // len(image_queries) if image_queries else 1))

    # Fetch videos using AI-suggested queries (run in thread)
    video_queries = data.pop("video_queries", [topic])
    videos = await asyncio.to_thread(_fetch_videos_sync, video_queries)

    return {
        "title": data.get("title", topic),
        "subtitle": data.get("subtitle", ""),
        "sections": data.get("sections", []),
        "images": images,
        "videos": videos,
        "charts": data.get("charts", []),
        "sources": data.get("sources", []),
        "model_used": response.model_used,
        "generated_at": datetime.now().isoformat(),
    }
