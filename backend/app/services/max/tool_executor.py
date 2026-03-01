"""MAX Tool Executor — parses tool blocks from AI responses and executes real actions.

Tools give MAX the ability to query real data and take real actions instead of
fabricating responses. Inspired by the OpenClaw skills-augmented agent pattern.
"""
import re
import json
import os
import uuid
import logging
import psutil
import httpx
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
from app.db.database import get_db, dict_row, dict_rows

logger = logging.getLogger("max.tool_executor")

TOOL_BLOCK_RE = re.compile(r"```tool\s*\n(.*?)\n```", re.DOTALL)

QUOTES_DIR = os.path.expanduser("~/Empire/data/quotes")


@dataclass
class ToolResult:
    tool: str
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


def parse_tool_blocks(text: str) -> list[dict]:
    """Extract tool call JSON objects from ```tool ... ``` blocks."""
    results = []
    for match in TOOL_BLOCK_RE.finditer(text):
        try:
            obj = json.loads(match.group(1).strip())
            if isinstance(obj, dict) and "tool" in obj:
                results.append(obj)
        except json.JSONDecodeError as e:
            logger.warning(f"Malformed tool JSON: {e}")
    return results


def strip_tool_blocks(text: str) -> str:
    """Remove tool blocks from visible text."""
    return TOOL_BLOCK_RE.sub("", text).strip()


# ── Tool Dispatcher ────────────────────────────────────────────────

TOOL_REGISTRY = {}


def tool(name: str):
    """Decorator to register a tool handler."""
    def decorator(fn):
        TOOL_REGISTRY[name] = fn
        return fn
    return decorator


def execute_tool(tool_call: dict, desk: Optional[str] = None) -> ToolResult:
    """Dispatch and execute a tool call."""
    tool_name = tool_call.get("tool", "")
    try:
        handler = TOOL_REGISTRY.get(tool_name)
        if handler:
            return handler(tool_call, desk)
        return ToolResult(tool=tool_name, success=False, error=f"Unknown tool: {tool_name}")
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}")
        return ToolResult(tool=tool_name, success=False, error=str(e))


# ── TASK TOOLS ─────────────────────────────────────────────────────

@tool("create_task")
def _create_task(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Create a task in the tasks table."""
    title = params.get("title", "").strip()
    if not title:
        return ToolResult(tool="create_task", success=False, error="Task title is required")

    task_id = str(uuid.uuid4())[:8]
    description = params.get("description", "")
    priority = params.get("priority", "normal")
    due_date = params.get("due_date")
    task_desk = desk or params.get("desk", "operations")

    if priority not in ("urgent", "high", "normal", "low"):
        priority = "normal"

    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO tasks (id, title, description, status, priority, desk, created_by, due_date, tags, metadata, created_at, updated_at)
               VALUES (?, ?, ?, 'todo', ?, ?, 'max', ?, '[]', '{}', ?, ?)""",
            (task_id, title, description, priority, task_desk, due_date, now, now),
        )
        conn.execute(
            """INSERT INTO task_activity (task_id, actor, action, detail, created_at)
               VALUES (?, 'max', 'created', ?, ?)""",
            (task_id, f"Created by MAX via {task_desk} desk chat", now),
        )

    logger.info(f"Task created: {task_id} - {title} (desk={task_desk})")
    return ToolResult(tool="create_task", success=True, result={
        "task_id": task_id, "title": title, "priority": priority,
        "desk": task_desk, "status": "todo",
    })


@tool("get_tasks")
def _get_tasks(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Get real tasks from the database."""
    status_filter = params.get("status")
    desk_filter = params.get("desk") or desk
    limit = min(params.get("limit", 20), 50)

    clauses, args = [], []
    if status_filter:
        clauses.append("status = ?")
        args.append(status_filter)
    if desk_filter:
        clauses.append("desk = ?")
        args.append(desk_filter)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    args.append(limit)

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT id, title, status, priority, desk, due_date, created_at FROM tasks{where} ORDER BY created_at DESC LIMIT ?",
            args,
        ).fetchall()

    tasks = [dict(r) for r in rows] if rows else []
    return ToolResult(tool="get_tasks", success=True, result={
        "tasks": tasks, "count": len(tasks),
    })


@tool("get_desk_status")
def _get_desk_status(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Get real task counts across all desks."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT desk, status, COUNT(*) as cnt FROM tasks WHERE status != 'cancelled' GROUP BY desk, status"
        ).fetchall()

    desks = {}
    for r in rows:
        d = r[0] or "unassigned"
        if d not in desks:
            desks[d] = {"todo": 0, "in_progress": 0, "done": 0, "waiting": 0}
        if r[1] in desks[d]:
            desks[d][r[1]] = r[2]

    return ToolResult(tool="get_desk_status", success=True, result={
        "desks": desks,
        "total_open": sum(d.get("todo", 0) + d.get("in_progress", 0) for d in desks.values()),
        "total_done": sum(d.get("done", 0) for d in desks.values()),
    })


# ── QUOTE TOOLS ────────────────────────────────────────────────────

@tool("search_quotes")
def _search_quotes(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Search quotes by customer name or status."""
    customer = params.get("customer_name", "").lower()
    status = params.get("status")
    limit = min(params.get("limit", 10), 20)

    quotes = []
    if os.path.exists(QUOTES_DIR):
        for fname in os.listdir(QUOTES_DIR):
            if not fname.endswith(".json") or fname.startswith("_"):
                continue
            with open(os.path.join(QUOTES_DIR, fname)) as f:
                q = json.load(f)
            if customer and customer not in q.get("customer_name", "").lower():
                continue
            if status and q.get("status") != status:
                continue
            quotes.append({
                "id": q["id"],
                "quote_number": q.get("quote_number"),
                "customer_name": q.get("customer_name"),
                "total": q.get("total", 0),
                "status": q.get("status"),
                "created_at": q.get("created_at", "")[:10],
                "items_count": len(q.get("line_items", [])),
            })

    quotes.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return ToolResult(tool="search_quotes", success=True, result={
        "quotes": quotes[:limit], "count": len(quotes),
    })


@tool("get_quote")
def _get_quote(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Get full details of a specific quote."""
    quote_id = params.get("quote_id", "")
    path = os.path.join(QUOTES_DIR, f"{quote_id}.json")
    if not os.path.exists(path):
        return ToolResult(tool="get_quote", success=False, error=f"Quote {quote_id} not found")
    with open(path) as f:
        q = json.load(f)
    return ToolResult(tool="get_quote", success=True, result=q)


# ── QUOTE BUILDER TOOL ─────────────────────────────────────────────

@tool("open_quote_builder")
def _open_quote_builder(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Open the inline QuoteBuilder pre-filled with customer info AND quote line items."""
    return ToolResult(tool="open_quote_builder", success=True, result={
        "action": "open_quote_builder",
        "customer_name": params.get("customer_name", ""),
        "customer_email": params.get("customer_email", ""),
        "customer_phone": params.get("customer_phone", ""),
        "customer_address": params.get("customer_address", ""),
        "project_name": params.get("project_name", ""),
        "rooms": params.get("rooms", []),
        "max_analysis": params.get("max_analysis", ""),
    })


# ── QUICK QUOTE TOOL ──────────────────────────────────────────────

@tool("create_quick_quote")
def _create_quick_quote(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Create a quick quote autonomously — no customer info required.
    Defaults to 'Customer 1' if no name provided. Saves JSON + generates PDF.
    """
    quote_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    quote_number = f"EMP-Q-{datetime.utcnow().strftime('%y%m%d')}-{quote_id[:4].upper()}"

    customer_name = params.get("customer_name", "Customer 1") or "Customer 1"
    rooms = params.get("rooms", [])
    max_analysis = params.get("max_analysis", "")

    # Build line items from rooms/windows
    line_items = []
    for room in rooms:
        room_name = room.get("name", "Room")
        for win in room.get("windows", []):
            w = win.get("width", 48)
            h = win.get("height", 60)
            qty = win.get("quantity", 1)
            treatment = win.get("treatmentType", "ripplefold")

            # Simple pricing based on treatment type + dimensions
            sqft = (w * h) / 144.0
            base_rates = {
                "ripplefold": 45, "pinch-pleat": 55, "rod-pocket": 30,
                "grommet": 35, "roman-shade": 50, "roller-shade": 40,
            }
            rate = base_rates.get(treatment, 45)
            price = round(sqft * rate * qty, 2)

            line_items.append({
                "room": room_name,
                "description": f"{treatment.replace('-', ' ').title()} — {w}\"W × {h}\"H",
                "quantity": qty,
                "unit_price": round(price / qty, 2) if qty else price,
                "total": price,
                "treatment_type": treatment,
                "width": w,
                "height": h,
            })
        for uph in room.get("upholstery", []):
            desc = uph.get("description", "Upholstery item")
            price = uph.get("price", 250)
            line_items.append({
                "room": room_name,
                "description": desc,
                "quantity": 1,
                "unit_price": price,
                "total": price,
            })

    total = sum(item["total"] for item in line_items)

    quote_data = {
        "id": quote_id,
        "quote_number": quote_number,
        "customer_name": customer_name,
        "customer_email": params.get("customer_email", ""),
        "customer_phone": params.get("customer_phone", ""),
        "customer_address": params.get("customer_address", ""),
        "project_name": params.get("project_name", "Quick Quote"),
        "rooms": rooms,
        "line_items": line_items,
        "subtotal": total,
        "tax_rate": 0,
        "tax": 0,
        "total": total,
        "status": "draft",
        "max_analysis": max_analysis,
        "created_at": now,
        "updated_at": now,
        "source": "max_quick_quote",
    }

    # Save JSON
    os.makedirs(QUOTES_DIR, exist_ok=True)
    quote_path = os.path.join(QUOTES_DIR, f"{quote_id}.json")
    with open(quote_path, "w") as f:
        json.dump(quote_data, f, indent=2)

    # Generate PDF
    pdf_url = None
    try:
        _run_async(_generate_pdf_for_quote(quote_id))
        pdf_dir = os.path.expanduser("~/Empire/data/quotes/pdf")
        pdf_file = os.path.join(pdf_dir, f"{quote_number}.pdf")
        if os.path.exists(pdf_file):
            pdf_url = f"/api/v1/quotes/{quote_id}/pdf"
    except Exception as e:
        logger.warning(f"Quick quote PDF generation failed: {e}")

    logger.info(f"Quick quote created: {quote_number} for {customer_name} — ${total:,.2f}")
    return ToolResult(tool="create_quick_quote", success=True, result={
        "quote_id": quote_id,
        "quote_number": quote_number,
        "customer_name": customer_name,
        "total": total,
        "items_count": len(line_items),
        "pdf_url": pdf_url,
        "line_items": line_items,
    })


# ── CONTACT TOOLS ──────────────────────────────────────────────────

@tool("search_contacts")
def _search_contacts(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Search contacts (customers, contractors, vendors)."""
    search = params.get("search", "")
    contact_type = params.get("type")
    limit = min(params.get("limit", 20), 50)

    clauses, args = [], []
    if search:
        clauses.append("(name LIKE ? OR email LIKE ? OR phone LIKE ?)")
        q = f"%{search}%"
        args.extend([q, q, q])
    if contact_type:
        clauses.append("type = ?")
        args.append(contact_type)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    args.append(limit)

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT id, name, type, phone, email, address, created_at FROM contacts{where} ORDER BY name LIMIT ?",
            args,
        ).fetchall()

    contacts = [dict(r) for r in rows] if rows else []
    return ToolResult(tool="search_contacts", success=True, result={
        "contacts": contacts, "count": len(contacts),
    })


@tool("create_contact")
def _create_contact(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Create a new contact."""
    name = params.get("name", "").strip()
    if not name:
        return ToolResult(tool="create_contact", success=False, error="Contact name is required")

    contact_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO contacts (id, name, type, phone, email, address, notes, metadata, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, '{}', ?, ?)""",
            (contact_id, name, params.get("type", "client"),
             params.get("phone"), params.get("email"),
             params.get("address"), params.get("notes"), now, now),
        )

    return ToolResult(tool="create_contact", success=True, result={
        "contact_id": contact_id, "name": name, "type": params.get("type", "client"),
    })


# ── SYSTEM TOOLS ───────────────────────────────────────────────────

@tool("get_system_stats")
def _get_system_stats(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Get real system stats — CPU, RAM, disk, temperatures."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    stats = {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "cpu_cores": psutil.cpu_count(),
        "ram_total_gb": round(mem.total / (1024**3), 1),
        "ram_used_gb": round(mem.used / (1024**3), 1),
        "ram_percent": mem.percent,
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "disk_used_gb": round(disk.used / (1024**3), 1),
        "disk_percent": round(disk.percent, 1),
        "uptime_hours": round((datetime.now().timestamp() - psutil.boot_time()) / 3600, 1),
    }

    # Temperature
    try:
        temps = psutil.sensors_temperatures()
        if "k10temp" in temps:
            stats["cpu_temp_c"] = temps["k10temp"][0].current
    except Exception:
        pass

    return ToolResult(tool="get_system_stats", success=True, result=stats)


@tool("get_weather")
def _get_weather(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Get real weather data from Open-Meteo (free, no API key)."""
    city = params.get("city", "Los Angeles")

    # Geocode city to lat/lon
    CITY_COORDS = {
        "los angeles": (34.05, -118.24),
        "la": (34.05, -118.24),
        "new york": (40.71, -74.01),
        "chicago": (41.88, -87.63),
        "houston": (29.76, -95.37),
        "phoenix": (33.45, -112.07),
        "san diego": (32.72, -117.16),
        "dallas": (32.78, -96.80),
        "san francisco": (37.77, -122.42),
        "miami": (25.76, -80.19),
        "atlanta": (33.75, -84.39),
        "seattle": (47.61, -122.33),
    }

    coords = CITY_COORDS.get(city.lower(), (34.05, -118.24))

    try:
        resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": coords[0],
                "longitude": coords[1],
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "auto",
            },
            timeout=5,
        )
        data = resp.json()
        current = data.get("current", {})

        # Weather code to description
        WMO = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
            95: "Thunderstorm", 96: "Thunderstorm with hail",
        }

        return ToolResult(tool="get_weather", success=True, result={
            "city": city,
            "temperature_f": current.get("temperature_2m"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_mph": current.get("wind_speed_10m"),
            "conditions": WMO.get(current.get("weather_code", 0), "Unknown"),
            "source": "Open-Meteo (live)",
        })
    except Exception as e:
        return ToolResult(tool="get_weather", success=False, error=f"Weather fetch failed: {e}")


@tool("get_services_health")
def _get_services_health(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Check which Empire services are running."""
    services = {
        "backend": {"port": 8000, "url": "http://localhost:8000/docs"},
        "founder_dashboard": {"port": 3009, "url": "http://localhost:3009"},
        "workroomforge": {"port": 3001, "url": "http://localhost:3001"},
        "empire_app": {"port": 3000, "url": "http://localhost:3000"},
        "luxeforge": {"port": 3002, "url": "http://localhost:3002"},
        "ollama": {"port": 11434, "url": "http://localhost:11434/"},
        "openclaw": {"port": 7878, "url": "http://localhost:7878/health"},
    }

    results = {}
    for name, svc in services.items():
        try:
            r = httpx.get(svc["url"], timeout=2)
            results[name] = {"status": "online", "port": svc["port"]}
        except Exception:
            results[name] = {"status": "offline", "port": svc["port"]}

    online = sum(1 for s in results.values() if s["status"] == "online")
    return ToolResult(tool="get_services_health", success=True, result={
        "services": results, "online": online, "total": len(results),
    })


def _run_async(coro):
    """Run an async coroutine from sync context (works inside running event loop)."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result(timeout=30)
    except RuntimeError:
        return asyncio.run(coro)


@tool("send_telegram")
def _send_telegram(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Send a text message to the founder via Telegram."""
    message = params.get("message", "")
    if not message:
        return ToolResult(tool="send_telegram", success=False, error="No message provided")
    try:
        from app.services.max.telegram_bot import TelegramBot
        bot = TelegramBot()
        if not bot.is_configured:
            return ToolResult(tool="send_telegram", success=False, error="Telegram not configured")
        sent = _run_async(bot.send_message(message))
        return ToolResult(tool="send_telegram", success=sent, result={"sent": sent})
    except Exception as e:
        return ToolResult(tool="send_telegram", success=False, error=str(e))


@tool("send_quote_telegram")
def _send_quote_telegram(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Generate PDF for a quote and send it to the founder via Telegram."""
    quote_id = params.get("quote_id", "")
    if not quote_id:
        return ToolResult(tool="send_quote_telegram", success=False, error="No quote_id provided")

    # Load quote
    quote_path = os.path.join(QUOTES_DIR, f"{quote_id}.json")
    if not os.path.exists(quote_path):
        return ToolResult(tool="send_quote_telegram", success=False, error=f"Quote {quote_id} not found")

    import json as _json
    with open(quote_path) as f:
        quote = _json.load(f)

    quote_number = quote.get("quote_number", quote_id)
    customer = quote.get("customer_name", "Unknown")
    total = quote.get("total", 0)

    # Generate PDF
    pdf_dir = os.path.expanduser("~/Empire/data/quotes/pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"{quote_number}.pdf")

    try:
        _run_async(_generate_pdf_for_quote(quote["id"]))
        if not os.path.exists(pdf_path):
            return ToolResult(tool="send_quote_telegram", success=False, error="PDF generation failed")
    except Exception as e:
        return ToolResult(tool="send_quote_telegram", success=False, error=f"PDF generation failed: {e}")

    # Send via Telegram
    try:
        from app.services.max.telegram_bot import TelegramBot
        bot = TelegramBot()
        if not bot.is_configured:
            return ToolResult(tool="send_quote_telegram", success=False, error="Telegram not configured")

        caption = (
            f"\U0001f4cb <b>Estimate {quote_number}</b>\n"
            f"\U0001f464 {customer}\n"
            f"\U0001f4b0 Total: ${total:,.2f}"
        )
        sent = _run_async(bot.send_document(pdf_path, caption=caption))
        return ToolResult(tool="send_quote_telegram", success=sent, result={
            "sent": sent, "quote_number": quote_number, "customer": customer, "total": total,
        })
    except Exception as e:
        return ToolResult(tool="send_quote_telegram", success=False, error=f"Telegram send failed: {e}")


async def _generate_pdf_for_quote(quote_id: str):
    """Generate PDF for a quote by ID (reuses quotes router logic)."""
    from app.routers.quotes import generate_pdf as _gen_pdf_endpoint
    await _gen_pdf_endpoint(quote_id)


# ── IMAGE SEARCH TOOL ─────────────────────────────────────────────

@tool("search_images")
def _search_images(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Search Unsplash for relevant images. Returns URLs for MAX to embed in markdown."""
    query = params.get("query", "")
    if not query:
        return ToolResult(tool="search_images", success=False, error="Query is required")

    unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not unsplash_key:
        return ToolResult(tool="search_images", success=False, error="UNSPLASH_ACCESS_KEY not configured")

    try:
        resp = httpx.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": 3, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {unsplash_key}"},
            timeout=10,
        )
        if resp.status_code != 200:
            return ToolResult(tool="search_images", success=False, error=f"Unsplash API error: {resp.status_code}")

        photos = resp.json().get("results", [])
        images = [
            {
                "url": p["urls"]["regular"],
                "alt": p.get("alt_description", query),
                "credit": p["user"]["name"],
            }
            for p in photos[:3]
        ]
        return ToolResult(tool="search_images", success=True, result={"images": images, "query": query})
    except Exception as e:
        return ToolResult(tool="search_images", success=False, error=f"Image search failed: {e}")


# ── DESK DELEGATION TOOL ───────────────────────────────────────────

@tool("run_desk_task")
def _run_desk_task(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Submit a task to the AI desk system for autonomous handling."""
    title = params.get("title", "").strip()
    if not title:
        return ToolResult(tool="run_desk_task", success=False, error="Task title is required")

    try:
        resp = httpx.post(
            "http://localhost:8000/api/v1/max/ai-desks/tasks",
            json={
                "title": title,
                "description": params.get("description", title),
                "priority": params.get("priority", "normal"),
                "customer_name": params.get("customer_name"),
                "source": "max_tool",
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            return ToolResult(tool="run_desk_task", success=True, result=data)
        else:
            return ToolResult(tool="run_desk_task", success=False, error=f"Desk API error: {resp.status_code}")
    except Exception as e:
        return ToolResult(tool="run_desk_task", success=False, error=f"Desk task failed: {e}")


# ── TOOL DOCUMENTATION (for system prompt) ─────────────────────────

TOOLS_DOC = """## Available Tools
You have access to real tools that query live data. Use them instead of making up information.
To call a tool, include a tool block in your response:

```tool
{"tool": "tool_name", "param1": "value1"}
```

### Data Tools
- **search_quotes** — Search quotes by customer or status
  `{"tool": "search_quotes", "customer_name": "...", "status": "draft|sent|accepted"}`
- **get_quote** — Get full quote details by ID
  `{"tool": "get_quote", "quote_id": "..."}`
- **search_contacts** — Search customers, contractors, vendors
  `{"tool": "search_contacts", "search": "name or email", "type": "client|contractor|vendor"}`
- **create_contact** — Add a new contact
  `{"tool": "create_contact", "name": "...", "type": "client", "phone": "...", "email": "..."}`
- **get_tasks** — Get real tasks (filter by desk or status)
  `{"tool": "get_tasks", "desk": "forge|sales|support|...", "status": "todo|in_progress|done"}`
- **get_desk_status** — Get task counts across all desks
  `{"tool": "get_desk_status"}`

### Action Tools
- **create_quick_quote** — Create a quick quote autonomously without opening the UI. Defaults customer to "Customer 1" if unknown. Returns quote_id, PDF URL, and line items. Use this for fast estimates.
  `{"tool": "create_quick_quote", "customer_name": "Customer 1", "rooms": [{"name": "Living Room", "windows": [{"name": "Window 1", "width": 72, "height": 84, "quantity": 1, "treatmentType": "ripplefold"}]}], "max_analysis": "Professional analysis here..."}`
  After creating, you can use send_quote_telegram to deliver the PDF.
- **open_quote_builder** — Open the QuoteBuilder right here in the dashboard (ALWAYS use this instead of linking to WorkroomForge). Pre-fills customer info AND rooms/windows from the conversation.
  `{"tool": "open_quote_builder", "customer_name": "...", "customer_email": "...", "customer_phone": "...", "customer_address": "...", "project_name": "...", "rooms": [{"name": "Living Room", "windows": [{"name": "Window 1", "width": 72, "height": 84, "quantity": 1, "treatmentType": "ripplefold", "liningType": "standard", "hardwareType": "track-ripplefold", "motorization": "none", "mountType": "wall"}], "upholstery": []}]}`
  treatmentType options: ripplefold, pinch-pleat, rod-pocket, grommet, roman-shade, roller-shade
  liningType: standard, blackout, thermal, sheer, none
  hardwareType: track-ripplefold, decorative-rod, tension-rod, hidden-track, none
  motorization: none, basic, smart
  mountType: wall, ceiling, inside
  Also include "max_analysis": "Your professional analysis of the project — recommendations, fabric suggestions, design notes, installation considerations. Write 2-4 sentences that would impress the client on the PDF."
  IMPORTANT: Always include rooms with windows extracted from the conversation. Use reasonable defaults for unspecified fields. Always write a max_analysis with your professional take.
- **create_task** — Create a new task
  `{"tool": "create_task", "title": "...", "description": "...", "priority": "normal", "desk": "forge", "due_date": "YYYY-MM-DD"}`
- **run_desk_task** — Delegate a task to the AI desk system. Task is auto-routed to the best desk (ForgeDesk, MarketDesk, etc.) for autonomous handling.
  `{"tool": "run_desk_task", "title": "Generate mockup for living room windows", "description": "Use AI vision to create design mockup from uploaded photo", "priority": "normal", "customer_name": "..."}`
  ForgeDesk capabilities: quotes, follow-ups, scheduling, measurements, fabric lookup, AI vision (measure, mockup, outline, upholstery)

### Communication Tools
- **send_telegram** — Send a text message to the founder via Telegram
  `{"tool": "send_telegram", "message": "<b>Title</b>\nMessage body here (HTML formatting)"}`
- **send_quote_telegram** — Generate a quote PDF and send it to the founder via Telegram
  `{"tool": "send_quote_telegram", "quote_id": "abc123"}`
  Use this after creating/saving a quote to deliver the PDF directly to Telegram.

### Research Tools
- **search_images** — Search for relevant images (Unsplash) to enhance your response. Embed results in markdown.
  `{"tool": "search_images", "query": "modern ripplefold drapery"}`
  After getting results, use: `![description](url)` to embed images in your response.

### System Tools
- **get_system_stats** — Real CPU, RAM, disk, temperature
  `{"tool": "get_system_stats"}`
- **get_weather** — Live weather data (no API key needed)
  `{"tool": "get_weather", "city": "Los Angeles"}`
- **get_services_health** — Check which Empire services are running
  `{"tool": "get_services_health"}`

IMPORTANT: Always use tools for factual data. NEVER fabricate task lists, weather, system stats, quotes, or customer info. If a tool returns empty results, say so honestly.
When asked to send a quote PDF to Telegram, use send_quote_telegram with the quote_id.
When discussing visual topics (fabrics, designs, installations), use search_images to find relevant reference photos.
"""
