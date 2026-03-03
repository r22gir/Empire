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

IMPORTANT: You will receive web search results with real articles and snippets. Use this data to make your presentation factually accurate and current. Cite actual sources from the search results.

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
- Adapt chart types to the topic:
  - Conflict/war/politics: use sentiment polls, approval ratings, casualty timelines, public opinion data
  - Market/business: use market size, pricing, growth trends
  - Technology: use adoption rates, benchmarks, comparisons
  - If no meaningful data exists for charts, use empty array — don't force generic charts
- Sources MUST come from the web search results provided — use real URLs, not made-up ones
- Include 2-3 image_queries — choose contextually appropriate searches:
  - News/conflict: "Iran conflict 2026 news photo", not generic stock photos
  - Business: "custom drapery showroom professional"
- Include 1-2 video_queries for relevant NEWS clips or explainer videos (search YouTube-style queries like "Iran war update March 2026 news")
- Use CURRENT facts and data from the web search results — do NOT rely on training data for recent events
- For current events: include a timeline or chronology section
- Make content informative, specific, and data-driven"""


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


def _web_research_sync(topic: str) -> str:
    """Synchronous web search — run via asyncio.to_thread."""
    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(topic, max_results=8)
        if not results:
            return ""
        lines = []
        for r in results:
            lines.append(f"**{r['title']}**\n{r['body']}\nURL: {r['href']}\n")
        return "\n".join(lines)
    except Exception as e:
        print(f"[PresentationBuilder] Web research failed: {e}")
        return ""


def _fetch_videos_sync(queries: list[str], max_per_query: int = 2) -> list[dict]:
    """Synchronous video search — run via asyncio.to_thread."""
    videos = []
    try:
        from duckduckgo_search import DDGS
        for query in queries[:2]:
            try:
                raw = DDGS().videos(query, max_results=max_per_query)
                for v in raw:
                    vid = {
                        "title": v.get("title", ""),
                        "url": v.get("content", ""),
                        "thumbnail": v.get("images", {}).get("large", "") or v.get("images", {}).get("medium", ""),
                        "duration": v.get("duration", ""),
                        "publisher": v.get("publisher", ""),
                    }
                    if vid["url"] and vid["title"]:
                        videos.append(vid)
            except Exception:
                continue
    except Exception as e:
        print(f"[PresentationBuilder] Video search failed: {e}")
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
