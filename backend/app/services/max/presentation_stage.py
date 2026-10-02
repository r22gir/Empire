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
    "- The spoken line is plain speech: no markdown, no chart JSON, no emoji, no status badges, "
    "and no client name unless the founder asked who it is.\n"
    "- For revenue, query payments_v2 (amount, payment_date, status, payment_type, stripe_session_id). "
    "Legacy payments has amount and payment_date and no status column. "
    "Stripe deposits live on invoices (amount_paid, paid_at, payment_status, stripe_checkout_session_id).\n"
)

_PRESENT_RE = re.compile(r"\bpresent\b", re.I)
_REVENUE_RE = re.compile(r"\b(revenue|sales|numbers|last month)\b", re.I)
_CHART_RE = re.compile(r"```chart\s*\n([\s\S]*?)```", re.I)
_MERMAID_RE = re.compile(r"```mermaid\s*\n([\s\S]*?)```", re.I)
_FENCE_RE = re.compile(r"```[\s\S]*?```")
_SENTENCE_RE = re.compile(r".+?[.!?…](?=\s|$)")
_FOUNDER_RE = re.compile(r"\brafael\b", re.I)
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002190-\U000021FF"
    "\u2705\u274C\u26A0\u2714\u2716"
    "\uFE0F\u200D"
    "]+"
)
_STATUS_BADGE_RE = re.compile(
    r"(?:(?<=^)|(?<=[.!?]\s)|(?<=\n))\s*(?:status\s*:\s*)?(?:verified|unverified)\b[.!]?",
    re.I,
)
_TRAILING_BADGE_RE = re.compile(
    r"\s+(?:status\s*:\s*)?(?:verified|unverified)\b[.!]?\s*$",
    re.I,
)
_MISSING_COLUMN_RE = re.compile(r"no such column:\s*([A-Za-z_][A-Za-z0-9_]*)", re.I)

REVENUE_SCHEMA_HINT = (
    "Revenue columns: payments_v2 has amount, payment_date, created_at, payment_type, "
    "status, invoice_id, stripe_session_id, payment_method. "
    "Legacy payments has amount, payment_date, created_at, method, invoice_id, reference, notes "
    "and has NO status column and NO paid_at column. "
    "Invoices (Stripe deposits) have amount_paid, total, status, payment_status, paid_at, "
    "stripe_checkout_session_id. Do not select status from legacy payments."
)

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


_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_ASKED_NAME_RE = re.compile(
    r"\b(client name|customer name|who is the client|who is the customer|their name)\b",
    re.I,
)
_NAME_KEYS = {"customer_name", "client_name", "client", "customer"}
_SKIP_NAMES = {"empire workroom", "max", "max ai", "the client"}


def _json_object_end(text: str, start: int) -> int:
    """Index after a balanced {...} object, or start when it is not closed."""
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    return start


def strip_chart_blocks(text: str) -> str:
    """Drop fenced blocks and inline chart/artifact JSON before TTS."""
    cleaned = _FENCE_RE.sub(" ", text or "")
    kept: list[str] = []
    index = 0
    while index < len(cleaned):
        inline = re.match(r"(?:chart|artifact)\s*\{", cleaned[index:], flags=re.I)
        at_boundary = index == 0 or not cleaned[index - 1].isalnum()
        if inline and at_boundary:
            end = _json_object_end(cleaned, index + inline.end() - 1)
            if end > index:
                index = end
                continue
        if cleaned[index] == "{":
            end = _json_object_end(cleaned, index)
            blob = cleaned[index:end]
            if end > index and any(token in blob for token in ('"type"', '"data"', '"labels"', '"title"')):
                index = end
                continue
        kept.append(cleaned[index])
        index += 1
    return "".join(kept)


def strip_spoken_markdown(text: str) -> str:
    """Plain speech. Asterisks, headings, JSON, emoji, and badges are not spoken."""
    cleaned = strip_chart_blocks(text or "")
    cleaned = _MD_LINK_RE.sub(r"\1", cleaned)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"[*_#~]+", " ", cleaned)
    cleaned = _EMOJI_RE.sub(" ", cleaned)
    cleaned = _STATUS_BADGE_RE.sub(" ", cleaned)
    cleaned = _TRAILING_BADGE_RE.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def sql_retry_without_missing_column(query: str, error: str) -> str | None:
    """One rewrite when SQLite reports a missing column. None when nothing changes."""
    match = _MISSING_COLUMN_RE.search(error or "")
    if not match or not query:
        return None
    column = re.escape(match.group(1))
    predicate = rf"(?:[A-Za-z_][A-Za-z0-9_]*\.)?{column}\b(?:\s*(?:=|!=|<>|IS|LIKE|IN)\s*(?:'[^']*'|\([^)]*\)|[^\s()]+))?"
    rewritten = re.sub(rf"\b(?:AND|OR)\s+{predicate}", " ", query, flags=re.I)
    rewritten = re.sub(rf"\bWHERE\s+{predicate}", " WHERE ", rewritten, flags=re.I)
    rewritten = re.sub(r"\bWHERE\s+(AND|OR)\b", "WHERE", rewritten, flags=re.I)
    rewritten = re.sub(r"\bWHERE\s*(?=(GROUP|ORDER|LIMIT|HAVING)\b)", "", rewritten, flags=re.I)
    rewritten = re.sub(r"\bWHERE\s*$", "", rewritten, flags=re.I)
    rewritten = re.sub(r"\s+", " ", rewritten).strip()
    original = re.sub(r"\s+", " ", query).strip()
    if rewritten.lower() == original.lower() or not rewritten.upper().startswith("SELECT"):
        return None
    return rewritten


def client_names_in_tools(tool_results: list | None) -> list[str]:
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in _NAME_KEYS and isinstance(value, str):
                    name = value.strip()
                    if len(name) >= 3 and name.lower() not in _SKIP_NAMES:
                        found.append(name)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(tool_results or [])
    unique: list[str] = []
    for name in sorted(set(found), key=len, reverse=True):
        if name not in unique:
            unique.append(name)
    return unique


def spoken_text(
    text: str | None,
    *,
    limit: int = SPOKEN_LIMIT,
    message: str | None = None,
    tool_results: list | None = None,
) -> str:
    """Two sentences, no chart source and no markdown, for TTS."""
    cleaned = strip_spoken_markdown(_FENCE_RE.sub(" ", text or ""))
    if not cleaned:
        return ""
    if not _ASKED_NAME_RE.search(message or ""):
        user = (message or "").lower()
        for name in client_names_in_tools(tool_results):
            if name.lower() in user:
                continue
            cleaned = re.sub(rf"\b{re.escape(name)}\b", "the client", cleaned, flags=re.I)
    cleaned = re.sub(r"\brafael\b", "the founder", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
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
    if wants_revenue(message):
        # The stage chart is the canonical ledger, not a second query the model wrote.
        artifacts = [item for item in artifacts if item.get("kind") != "chart"]
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
    chart = next((item for item in artifacts if item.get("kind") == "chart"), None)
    if wants_revenue(message) and chart is not None:
        payload = chart.get("payload") or {}
        chart_rows = [] if payload.get("empty") else [
            {"label": str(label), "value": float(value)}
            for label, value in zip(payload.get("labels") or [], payload.get("data") or [])
        ]
        row_spoken = spoken_from_revenue_rows(chart_rows)
        spoken = f"I'll walk through {len(slides)} slides. {row_spoken}" if slides else row_spoken
    elif slides:
        spoken = f"I'll walk through {len(slides)} slides. {slides[0]['narration']}"
    else:
        spoken = spoken_text(response, message=message, tool_results=tool_results)
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


def spoken_from_revenue_rows(rows: list[dict] | None) -> str:
    """One or two sentences from the same rows the chart draws."""
    data = list(rows or [])
    if not data:
        return "I don't have payment rows for that window, so I won't invent a total."
    total = sum(float(row["value"]) for row in data)
    money = f"${total:,.2f}"
    if len(data) == 1:
        return f"Revenue is {money}."
    latest = data[-1]
    return f"Revenue is {money}. {latest['label']} is ${float(latest['value']):,.2f}."


def _table_columns(conn, table: str) -> set[str]:
    try:
        info = conn.execute(f"PRAGMA table_info({table})").fetchall()
    except Exception:
        return set()
    names = set()
    for row in info:
        names.add(row["name"] if hasattr(row, "keys") else row[1])
    return names


def _month_label(value: Any) -> str:
    text = str(value or "")
    return text[:7] if len(text) >= 7 and text[4] == "-" else ""


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _revenue_events(conn) -> list[tuple[str, float]]:
    """payments_v2, then legacy payments, then Stripe invoice deposits not already counted."""
    events: list[tuple[str, float]] = []
    paid_by_invoice: dict[str, float] = {}
    covered_sessions: set[str] = set()

    v2_cols = _table_columns(conn, "payments_v2")
    if "amount" in v2_cols:
        chosen = [name for name in (
            "amount", "payment_date", "created_at", "invoice_id", "stripe_session_id",
            "payment_type", "status",
        ) if name in v2_cols]
        try:
            for row in conn.execute(f"SELECT {', '.join(chosen)} FROM payments_v2").fetchall():
                item = dict(row) if hasattr(row, "keys") else {}
                if not item and not hasattr(row, "keys"):
                    item = dict(zip(chosen, row))
                kind = str(item.get("payment_type") or "payment").lower()
                status = str(item.get("status") or "completed").lower()
                if kind == "refund" or status in {"failed", "cancelled", "refunded"}:
                    continue
                amount = _as_float(item.get("amount"))
                if amount == 0:
                    continue
                month = _month_label(item.get("payment_date") or item.get("created_at"))
                if not month:
                    continue
                events.append((month, amount))
                invoice_id = str(item.get("invoice_id") or "")
                if invoice_id:
                    paid_by_invoice[invoice_id] = paid_by_invoice.get(invoice_id, 0.0) + amount
                session = str(item.get("stripe_session_id") or "")
                if session:
                    covered_sessions.add(session)
        except Exception:
            logger.info("revenue chart: payments_v2 unreadable")

    legacy_cols = _table_columns(conn, "payments")
    if "amount" in legacy_cols:
        chosen = [name for name in ("amount", "payment_date", "created_at", "invoice_id") if name in legacy_cols]
        try:
            for row in conn.execute(f"SELECT {', '.join(chosen)} FROM payments").fetchall():
                item = dict(row) if hasattr(row, "keys") else dict(zip(chosen, row))
                invoice_id = str(item.get("invoice_id") or "")
                if invoice_id and invoice_id in paid_by_invoice:
                    continue
                amount = _as_float(item.get("amount"))
                month = _month_label(item.get("payment_date") or item.get("created_at"))
                if not month or amount == 0:
                    continue
                events.append((month, amount))
                if invoice_id:
                    paid_by_invoice[invoice_id] = paid_by_invoice.get(invoice_id, 0.0) + amount
        except Exception:
            logger.info("revenue chart: legacy payments unreadable")

    invoice_cols = _table_columns(conn, "invoices")
    if "amount_paid" in invoice_cols or "total" in invoice_cols:
        chosen = [name for name in (
            "id", "amount_paid", "total", "status", "payment_status", "paid_at", "created_at",
            "stripe_checkout_session_id",
        ) if name in invoice_cols]
        try:
            for row in conn.execute(f"SELECT {', '.join(chosen)} FROM invoices").fetchall():
                item = dict(row) if hasattr(row, "keys") else dict(zip(chosen, row))
                invoice_id = str(item.get("id") or "")
                session = str(item.get("stripe_checkout_session_id") or "")
                state = str(item.get("payment_status") or item.get("status") or "").lower()
                collected = _as_float(item.get("amount_paid"))
                if collected <= 0 and session and state in {"paid", "partial"}:
                    collected = _as_float(item.get("total"))
                if collected <= 0:
                    continue
                extra = collected - paid_by_invoice.get(invoice_id, 0.0)
                if session and session in covered_sessions and extra <= 0.009:
                    continue
                if extra <= 0.009:
                    continue
                month = _month_label(item.get("paid_at") or item.get("created_at"))
                if not month:
                    continue
                events.append((month, round(extra, 2)))
        except Exception:
            logger.info("revenue chart: invoices unreadable")
    return events


def read_revenue_rows() -> list[dict]:
    """Monthly revenue from one ledger.

    payments_v2 is canonical. Legacy payments and Stripe invoice deposits
    are added only for money that ledger does not already contain.
    Empty when nothing is recorded. Never invented.
    """
    try:
        from app.db.database import get_db

        with get_db() as conn:
            totals: dict[str, float] = {}
            for month, amount in _revenue_events(conn):
                totals[month] = round(totals.get(month, 0.0) + amount, 2)
    except Exception:
        logger.info("revenue chart: payments table unavailable")
        return []
    return [{"label": month, "value": totals[month]} for month in sorted(totals)[-6:]]


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
    return _artifact("chart", "Revenue", spoken_from_revenue_rows(data), chart, 1)


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
