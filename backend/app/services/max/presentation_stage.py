"""Presentation-stage artifacts. The spoken line stays short; the screen holds the detail.

Same module for every edition. Nothing here sends mail or messages.
Client-facing artifacts use Empire Workroom branding and drop the founder's name.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Optional

logger = logging.getLogger("max.presentation_stage")

CLIENT_BRAND = "Empire Workroom"
DRAWN_BY = "MAX AI"
SPOKEN_LIMIT = 380

PRESENTATION_DIRECTIVE = (
    "\n\n## CHANNEL: PRESENTATION\n"
    "The founder is looking at Presentation Mode, with the face on one side and a stage on the other.\n"
    "- Speak at most two short sentences. The stage shows the detail.\n"
    "- When you have real numbers, emit a ```chart {\"type\":\"bar|line|pie\",\"title\":\"...\",\"labels\":[...],\"data\":[...]}``` fence.\n"
    "- When a diagram helps, emit a ```mermaid fence.\n"
    "- Use the normal tools for quotes, drawings, documents, and lookups. Do not invent totals.\n"
    "- Never send email, invoices, or client documents. Drafts stay drafts until the founder confirms.\n"
    "- Client-facing quotes, invoices, proposals, and drawings use Empire Workroom branding. "
    "Do not put the founder's name on them.\n"
)

_PRESENT_RE = re.compile(r"\bpresent\b", re.I)
_REVENUE_RE = re.compile(r"\b(revenue|sales|numbers|last month)\b", re.I)
_CHART_RE = re.compile(r"```chart\s*\n([\s\S]*?)```", re.I)
_MERMAID_RE = re.compile(r"```mermaid\s*\n([\s\S]*?)```", re.I)
_FENCE_RE = re.compile(r"```[\s\S]*?```")
_SENTENCE_RE = re.compile(r".+?[.!?…](?=\s|$)")
_FOUNDER_RE = re.compile(r"\brafael\b", re.I)

_QUOTE_TOOLS = {"get_quote", "show_quote_for_review"}
_DRAFT_TOOLS = {"create_quick_quote", "photo_to_quote"}
_LIST_TOOLS = {
    "search_quotes": ("quotes", ("quote_number", "customer_name", "status", "total")),
    "get_tasks": ("tasks", ("title", "status", "desk", "priority")),
    "check_email": ("emails", ("from", "subject", "date")),
    "search_contacts": ("contacts", ("name", "email", "phone", "company")),
    "list_quotes_awaiting_review": ("quotes", ("quote_number", "customer_name", "status", "total")),
}


def is_present_request(message: str | None) -> bool:
    return bool(_PRESENT_RE.search(message or ""))


def wants_revenue(message: str | None) -> bool:
    return bool(_REVENUE_RE.search(message or ""))


def spoken_text(text: str | None, *, limit: int = SPOKEN_LIMIT) -> str:
    """Two sentences, no chart or diagram source, for TTS."""
    cleaned = _FENCE_RE.sub(" ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    parts = [part.strip() for part in _SENTENCE_RE.findall(cleaned) if part.strip()]
    spoken = " ".join(parts[:2]) if parts else cleaned
    if len(spoken) > limit:
        cut = spoken[:limit].rsplit(" ", 1)[0].rstrip(",;:")
        spoken = (cut or spoken[:limit]).rstrip(".") + "."
    return spoken


def scrub_client_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text or _FOUNDER_RE.search(text):
        return ""
    return text


def _public_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.startswith("file:") or "/home/" in text or "\\" in text:
        return ""
    if text.startswith("http://") or text.startswith("https://") or text.startswith("/"):
        return text
    return ""


def _chart_from_obj(obj: Any) -> Optional[dict]:
    if not isinstance(obj, dict):
        return None
    kind = str(obj.get("type") or "").lower()
    if kind not in {"bar", "line", "pie"}:
        return None
    labels = obj.get("labels")
    data = obj.get("data")
    if not isinstance(labels, list) or not isinstance(data, list) or not labels:
        return None
    if len(labels) != len(data):
        return None
    try:
        numbers = [float(item) for item in data]
    except (TypeError, ValueError):
        return None
    return {
        "type": kind,
        "labels": [str(item) for item in labels],
        "data": numbers,
        "title": str(obj.get("title") or "Chart"),
    }


def charts_in_text(text: str | None) -> list[dict]:
    found = []
    for match in _CHART_RE.finditer(text or ""):
        try:
            parsed = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        chart = _chart_from_obj(parsed)
        if chart:
            found.append(chart)
    return found


def diagrams_in_text(text: str | None) -> list[str]:
    return [match.group(1).strip() for match in _MERMAID_RE.finditer(text or "") if match.group(1).strip()]


def _artifact(kind: str, title: str, narration: str, payload: dict, index: int) -> dict:
    return {
        "id": f"{kind}-{index}",
        "kind": kind,
        "title": title[:120],
        "narration": narration[:240],
        "brand": CLIENT_BRAND if kind in {"quote", "quote_draft", "drawing", "document"} else "",
        "payload": payload,
    }


def _quote_payload(result: dict, *, draft: bool) -> dict:
    items = []
    for row in (result.get("line_items") or [])[:12]:
        if not isinstance(row, dict):
            continue
        items.append({
            "description": scrub_client_name(row.get("description") or row.get("name") or "Item") or "Item",
            "amount": row.get("amount", row.get("total")),
        })
    customer = scrub_client_name(result.get("customer_name") or result.get("client") or result.get("client_name"))
    return {
        "quote_id": result.get("quote_id") or result.get("id") or "",
        "quote_number": result.get("quote_number") or "",
        "customer_name": customer,
        "client_brand": CLIENT_BRAND,
        "status": result.get("status") or ("draft" if draft else ""),
        "sent": False if draft else bool(result.get("sent")),
        "total": result.get("total"),
        "line_items": items,
        "missing": result.get("missing") or [],
        "options": result.get("options") or [],
        "latest_transcript": result.get("latest_transcript") or "",
        "drawing": result.get("drawing") if isinstance(result.get("drawing"), dict) else None,
        "pdf_url": _public_url(result.get("pdf_url")),
        "proposal_totals": result.get("proposal_totals"),
        "items_count": result.get("items_count") or len(items),
        "drawn_by": DRAWN_BY,
        "notes": "Draft. Not sent." if draft else "",
    }


def _table_from_rows(rows: list, columns: tuple[str, ...]) -> dict:
    slim = []
    for row in rows[:12]:
        if not isinstance(row, dict):
            continue
        item = {}
        for key in columns:
            value = row.get(key)
            if key in {"customer_name", "client", "name", "from"}:
                value = scrub_client_name(value)
            if value not in (None, ""):
                item[key] = value
        if item:
            slim.append(item)
    return {"columns": list(columns), "rows": slim}


def _from_tool(tool: str, result: Any, index: int) -> list[dict]:
    if not isinstance(result, dict):
        if isinstance(result, list) and tool in _LIST_TOOLS:
            key, columns = _LIST_TOOLS[tool]
            table = _table_from_rows(result, columns)
            if table["rows"]:
                return [_artifact("table", tool.replace("_", " "), "The list is on screen.", table, index)]
        return []
    out: list[dict] = []
    svg = result.get("svg")
    if tool == "sketch_to_drawing" or (isinstance(svg, str) and "<svg" in svg.lower()):
        out.append(_artifact(
            "drawing",
            str(result.get("item_name") or result.get("item_type") or "Drawing"),
            "The drawing is on screen. It follows the bench standard.",
            {
                "svg": svg,
                "svg_url": _public_url(result.get("svg_url")),
                "pdf_url": _public_url(result.get("pdf_url")),
                "item_type": result.get("item_type") or "",
                "item_name": result.get("item_name") or "",
                "business_unit": result.get("business_unit") or "workroom",
                "drawn_by": DRAWN_BY,
                "company": CLIENT_BRAND,
            },
            index,
        ))
        index += 1
    chart = _chart_from_obj(result.get("chart") if isinstance(result.get("chart"), dict) else result)
    if chart and tool == "get_revenue_chart":
        title = str(result.get("title") or chart.get("title") or "Revenue")
        narration = str(result.get("narration") or f"{title} is on screen.")
        out.append(_artifact("chart", title, narration, chart, index))
        return out
    if tool in _DRAFT_TOOLS or (result.get("line_items") and result.get("quote_number") and "missing" in result):
        payload = _quote_payload(result, draft=True)
        number = payload["quote_number"] or "quote"
        out.append(_artifact(
            "quote_draft",
            f"Draft {number}",
            f"Draft {number} is on screen. It has not been sent.",
            payload,
            index,
        ))
        return out
    if tool in _QUOTE_TOOLS or (result.get("quote_number") and (result.get("line_items") or result.get("total") is not None)):
        payload = _quote_payload(result, draft=str(result.get("status") or "") == "draft")
        number = payload["quote_number"] or "Quote"
        out.append(_artifact(
            "quote",
            str(number),
            f"{number} is on screen. Nothing has been sent.",
            payload,
            index,
        ))
        index += 1
    if tool in _LIST_TOOLS:
        key, columns = _LIST_TOOLS[tool]
        rows = result.get(key) or result.get("results") or result.get("quotes") or []
        if isinstance(rows, list):
            table = _table_from_rows(rows, columns)
            if table["rows"]:
                out.append(_artifact("table", tool.replace("_", " "), "The list is on screen.", table, index))
                index += 1
    pdf = _public_url(result.get("pdf_url") or result.get("url"))
    if pdf and not any(item["kind"] in {"quote", "quote_draft", "drawing"} for item in out):
        out.append(_artifact(
            "document",
            str(result.get("title") or result.get("quote_number") or "Document"),
            "The document is on screen. It has not been sent.",
            {"url": pdf, "company": CLIENT_BRAND, "drawn_by": DRAWN_BY},
            index,
        ))
        index += 1
    images = []
    if result.get("image_url"):
        images.append(result["image_url"])
    for url in result.get("image_urls") or []:
        images.append(url)
    images = [_public_url(url) for url in images if _public_url(url)]
    if images:
        out.append(_artifact("image", "Image", "The image is on screen.", {"urls": images[:4]}, index))
        index += 1
    if chart and tool != "get_revenue_chart":
        out.append(_artifact("chart", chart["title"], f"{chart['title']} is on screen.", chart, index))
    mermaid = result.get("mermaid")
    if isinstance(mermaid, str) and mermaid.strip():
        out.append(_artifact("diagram", "Diagram", "The diagram is on screen.", {"source": mermaid.strip()}, index + 1))
    return out


def artifacts_from_turn(
    message: str | None,
    response: str | None,
    tool_results: list | None,
    *,
    revenue_rows: list[dict] | None = None,
) -> list[dict]:
    artifacts: list[dict] = []
    for entry in tool_results or []:
        if not isinstance(entry, dict) or entry.get("success") is False:
            continue
        tool = str(entry.get("tool") or "")
        artifacts.extend(_from_tool(tool, entry.get("result"), len(artifacts) + 1))
    for chart in charts_in_text(response):
        artifacts.append(_artifact("chart", chart["title"], f"{chart['title']} is on screen.", chart, len(artifacts) + 1))
    for source in diagrams_in_text(response):
        artifacts.append(_artifact("diagram", "Diagram", "The diagram is on screen.", {"source": source}, len(artifacts) + 1))
    if wants_revenue(message) and not any(item["kind"] == "chart" for item in artifacts):
        artifacts.append(revenue_artifact(list(revenue_rows or [])))
    return artifacts[:8]


def slides_from_artifacts(message: str | None, artifacts: list[dict]) -> list[dict]:
    if not is_present_request(message) or not artifacts:
        return []
    slides = []
    for artifact in artifacts[:6]:
        slides.append({
            "id": artifact["id"],
            "narration": artifact.get("narration") or "Next slide.",
            "artifact": artifact,
        })
    return slides


def package_turn(
    message: str | None,
    response: str | None,
    tool_results: list | None,
    *,
    revenue_reader: Optional[Callable[[], list]] = None,
) -> dict[str, Any]:
    """Spoken line plus stage artifacts. Does not send anything."""
    rows = None
    if wants_revenue(message):
        rows = revenue_reader() if revenue_reader is not None else read_revenue_rows()
    artifacts = artifacts_from_turn(message, response, tool_results, revenue_rows=rows)
    slides = slides_from_artifacts(message, artifacts)
    if slides:
        spoken = f"I'll walk through {len(slides)} slides. {slides[0]['narration']}"
    else:
        spoken = spoken_text(response)
        if not spoken and artifacts:
            spoken = artifacts[0].get("narration") or "It's on screen."
        elif not spoken:
            spoken = "I don't have anything new to put on screen."
    return {
        "spoken": spoken[:SPOKEN_LIMIT],
        "artifacts": artifacts,
        "slides": slides,
        "tool_results": list(tool_results or []),
    }


def read_revenue_rows() -> list[dict]:
    """Real payment totals by month. Empty when the table is missing. Never invented."""
    try:
        from app.db.database import get_db

        with get_db() as conn:
            rows = conn.execute(
                """SELECT substr(COALESCE(paid_at, created_at, ''), 1, 7) AS month,
                          COALESCE(SUM(amount), 0) AS total
                   FROM payments
                   GROUP BY month
                   HAVING month != ''
                   ORDER BY month DESC
                   LIMIT 6"""
            ).fetchall()
    except Exception:
        logger.info("revenue chart: payments table unavailable")
        return []
    parsed = []
    for row in reversed(list(rows)):
        if hasattr(row, "keys"):
            label, total = row["month"], row["total"]
        else:
            label, total = row[0], row[1]
        if not label:
            continue
        try:
            amount = float(total or 0)
        except (TypeError, ValueError):
            continue
        parsed.append({"label": str(label), "value": amount})
    return parsed


def revenue_artifact(rows: list[dict] | None = None) -> dict:
    data = list(rows if rows is not None else read_revenue_rows())
    if not data:
        return _artifact(
            "chart",
            "Revenue",
            "I don't have payment rows for that window, so I won't invent a chart.",
            {"type": "bar", "title": "Revenue", "labels": [], "data": [], "empty": True},
            1,
        )
    chart = {
        "type": "bar",
        "title": "Revenue",
        "labels": [row["label"] for row in data],
        "data": [row["value"] for row in data],
        "empty": False,
    }
    return _artifact("chart", "Revenue", "Revenue is on screen.", chart, 1)


def revenue_tool_result() -> dict[str, Any]:
    artifact = revenue_artifact()
    payload = dict(artifact["payload"])
    payload["title"] = artifact["title"]
    payload["narration"] = artifact["narration"]
    return {"success": True, "tool": "get_revenue_chart", "result": payload}


def stage_event(tool_name: str, data: dict | None, user_text: str = "") -> dict[str, Any]:
    """Payload added to a live-voice tool event. Read-only; nothing is sent."""
    entry = {
        "tool": tool_name,
        "success": bool((data or {}).get("success")),
        "result": (data or {}).get("result"),
    }
    artifacts = artifacts_from_turn(user_text, "", [entry], revenue_rows=[])
    return {
        "artifacts": artifacts,
        "slides": slides_from_artifacts(user_text, artifacts),
    }
