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
from datetime import datetime, timedelta
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


# ── PRICING TABLES ────────────────────────────────────────────────

# Fabric cost per yard by grade
FABRIC_GRADES = {
    "A": {"label": "Essential", "per_yard": 25},
    "B": {"label": "Designer", "per_yard": 45},
    "C": {"label": "Premium", "per_yard": 75},
    "D": {"label": "Luxury", "per_yard": 120},
}

# Lining cost per yard
LINING_RATES = {
    "none": 0, "standard": 8, "blackout": 14, "thermal": 12, "interlining": 18,
}

# Treatment-specific: fullness multiplier, labor hours per panel, fabric_width (inches)
TREATMENT_SPECS = {
    "ripplefold":   {"fullness": 2.0, "labor_hrs": 2.0,  "fabric_width": 54},
    "pinch-pleat":  {"fullness": 2.5, "labor_hrs": 2.5,  "fabric_width": 54},
    "rod-pocket":   {"fullness": 2.0, "labor_hrs": 1.5,  "fabric_width": 54},
    "grommet":      {"fullness": 1.8, "labor_hrs": 1.5,  "fabric_width": 54},
    "roman-shade":  {"fullness": 1.0, "labor_hrs": 3.0,  "fabric_width": 54},
    "roller-shade": {"fullness": 1.0, "labor_hrs": 0.5,  "fabric_width": 0},  # no fabric calc
}

# Hardware cost per linear foot by type
HARDWARE_RATES = {
    "standard-track": 8, "ripplefold-track": 18, "decorative-rod": 22,
    "traverse-rod": 28, "motorized-track": 65, "cassette": 15,
    "roller-mechanism": 12,
}

# Default hardware per treatment
DEFAULT_HARDWARE = {
    "ripplefold": "ripplefold-track", "pinch-pleat": "decorative-rod",
    "rod-pocket": "decorative-rod", "grommet": "decorative-rod",
    "roman-shade": "cassette", "roller-shade": "roller-mechanism",
}

LABOR_RATE = 50  # $/hr fabrication
INSTALL_PER_WINDOW = 85  # flat rate per window install
DC_TAX_RATE = 0.06


def _calc_window_line_items(room_name: str, win: dict) -> list[dict]:
    """Break one window into detailed line items: fabric, lining, hardware, labor, install."""
    w = win.get("width", 48)
    h = win.get("height", 60)
    qty = win.get("quantity", 1)
    treatment = win.get("treatmentType", "ripplefold")
    fabric_grade = win.get("fabricGrade", "B")
    lining = win.get("liningType", "standard")
    hardware_type = win.get("hardwareType") or DEFAULT_HARDWARE.get(treatment, "standard-track")
    motorized = win.get("motorization", "none") != "none"

    specs = TREATMENT_SPECS.get(treatment, TREATMENT_SPECS["ripplefold"])
    label = treatment.replace("-", " ").title()
    items = []

    # ── Fabric ──
    if specs["fabric_width"] > 0:
        # Widths of fabric needed = (window width × fullness) / fabric width, rounded up
        fabric_w = specs["fabric_width"]
        widths_needed = max(1, -(-int(w * specs["fullness"]) // fabric_w))  # ceil division
        # Cut length = height + 16" allowance (hems + headers)
        cut_length_in = h + 16
        yards_per_width = cut_length_in / 36.0
        total_yards = round(widths_needed * yards_per_width * qty, 1)
        grade_info = FABRIC_GRADES.get(fabric_grade, FABRIC_GRADES["B"])
        fabric_cost = round(total_yards * grade_info["per_yard"], 2)
        items.append({
            "room": room_name,
            "description": f"Fabric — {grade_info['label']} Grade ({total_yards} yds) for {label}",
            "quantity": qty,
            "unit_price": round(fabric_cost / qty, 2),
            "total": fabric_cost,
            "category": "fabric",
            "treatment_type": treatment, "width": w, "height": h,
        })

        # ── Lining ──
        lining_rate = LINING_RATES.get(lining, LINING_RATES["standard"])
        if lining_rate > 0:
            lining_cost = round(total_yards * lining_rate, 2)
            items.append({
                "room": room_name,
                "description": f"Lining — {lining.title()} ({total_yards} yds)",
                "quantity": qty,
                "unit_price": round(lining_cost / qty, 2),
                "total": lining_cost,
                "category": "lining",
            })

        # ── Labor / Fabrication ──
        labor_cost = round(specs["labor_hrs"] * LABOR_RATE * widths_needed * qty, 2)
        items.append({
            "room": room_name,
            "description": f"Fabrication — {label} ({widths_needed} width{'s' if widths_needed > 1 else ''} × {specs['labor_hrs']}hr)",
            "quantity": qty,
            "unit_price": round(labor_cost / qty, 2),
            "total": labor_cost,
            "category": "labor",
        })
    else:
        # Roller shades — flat pricing by size
        sqft = (w * h) / 144.0
        shade_cost = round(sqft * 40 * qty, 2)
        items.append({
            "room": room_name,
            "description": f"{label} — {w}\"W × {h}\"H",
            "quantity": qty,
            "unit_price": round(shade_cost / qty, 2),
            "total": shade_cost,
            "category": "product",
            "treatment_type": treatment, "width": w, "height": h,
        })

    # ── Hardware ──
    hw_rate = HARDWARE_RATES.get(hardware_type, 15)
    if motorized:
        hardware_type = "motorized-track"
        hw_rate = HARDWARE_RATES["motorized-track"]
    hw_feet = max(1, w / 12.0)
    hw_cost = round(hw_rate * hw_feet * qty, 2)
    hw_label = hardware_type.replace("-", " ").title()
    items.append({
        "room": room_name,
        "description": f"Hardware — {hw_label} ({hw_feet:.1f} ft)",
        "quantity": qty,
        "unit_price": round(hw_cost / qty, 2),
        "total": hw_cost,
        "category": "hardware",
    })

    # ── Installation ──
    install_cost = round(INSTALL_PER_WINDOW * qty, 2)
    items.append({
        "room": room_name,
        "description": "Professional Installation",
        "quantity": qty,
        "unit_price": INSTALL_PER_WINDOW,
        "total": install_cost,
        "category": "installation",
    })

    return items


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

    # Build detailed line items from rooms/windows
    line_items = []
    for room in rooms:
        room_name = room.get("name", "Room")
        for win in room.get("windows", []):
            line_items.extend(_calc_window_line_items(room_name, win))
        for uph in room.get("upholstery", []):
            desc = uph.get("description", "Upholstery item")
            price = uph.get("price", 250)
            line_items.append({
                "room": room_name,
                "description": desc,
                "quantity": 1,
                "unit_price": price,
                "total": price,
                "category": "upholstery",
            })

    subtotal = round(sum(item["total"] for item in line_items), 2)
    tax_amount = round(subtotal * DC_TAX_RATE, 2)
    total = round(subtotal + tax_amount, 2)
    deposit_amount = round(subtotal * 0.50, 2)
    expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()

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
        "ai_outlines": params.get("ai_outlines", []),
        "ai_mockups": params.get("ai_mockups", []),
        "subtotal": subtotal,
        "tax_rate": DC_TAX_RATE,
        "tax_amount": tax_amount,
        "total": total,
        "deposit": {"deposit_percent": 50, "deposit_amount": deposit_amount},
        "status": "draft",
        "max_analysis": max_analysis,
        "created_at": now,
        "updated_at": now,
        "expires_at": expires_at,
        "source": "max_quick_quote",
        "terms": "50% deposit required to begin fabrication. Balance due upon installation. All sales final once fabric is cut. Estimate valid for 30 days.",
        "valid_days": 30,
        "business_name": "Empire",
    }

    # Generate AI mockup images for each room's windows
    xai_key = os.environ.get("XAI_API_KEY")
    if xai_key and rooms:
        try:
            ai_mockups = []
            treatment_labels = {
                'ripplefold': 'Ripplefold', 'pinch-pleat': 'Pinch Pleat', 'rod-pocket': 'Rod Pocket',
                'grommet': 'Grommet Top', 'roman-shade': 'Roman Shade', 'roller-shade': 'Roller Shade',
            }
            for room in rooms:
                room_name = room.get("name", "Room")
                windows = room.get("windows", [])
                if not windows:
                    continue
                # Build one mockup entry per room with generated images
                gen_images = []
                for win in windows[:2]:  # Max 2 windows per room
                    treatment = win.get("treatmentType", "ripplefold")
                    label = treatment_labels.get(treatment, treatment.replace('-', ' ').title())
                    w = win.get("width", 48)
                    h = win.get("height", 60)
                    lining = win.get("liningType", "standard").replace('-', ' ')
                    mount = win.get("mountType", "wall")
                    hardware = win.get("hardwareType", "standard").replace('-', ' ')

                    prompt = (
                        f"Professional interior design photo: a {room_name.lower()} with a "
                        f"{w}-inch wide by {h}-inch tall window. "
                        f"Installed: {label} drapery panels in elegant fabric. "
                        f"IMPORTANT: The panels are FULLY OPEN and RETRACTED to each side of the window frame, "
                        f"gathered in neat stackback folds, showing the full window glass and view. "
                        f"The panels hang from {hardware} hardware, {mount}-mounted. "
                        f"{lining} lining visible at panel edges. "
                        f"Clean, bright natural light streaming through the uncovered window. "
                        f"Magazine-quality architectural photography, straight-on view."
                    )
                    try:
                        img_resp = httpx.post(
                            "https://api.x.ai/v1/images/generations",
                            headers={"Content-Type": "application/json", "Authorization": f"Bearer {xai_key}"},
                            json={"model": "grok-imagine-image", "prompt": prompt, "n": 1, "response_format": "url"},
                            timeout=30,
                        )
                        if img_resp.status_code == 200:
                            img_url = img_resp.json().get("data", [{}])[0].get("url")
                            if img_url:
                                gen_images.append({"tier": f"{label} — {win.get('name', 'Window')}", "url": img_url})
                    except Exception as img_err:
                        logger.warning(f"Quick quote image gen failed for {room_name}: {img_err}")

                if gen_images:
                    ai_mockups.append({
                        "roomName": room_name,
                        "generated_images": gen_images,
                        "proposals": [],
                        "generalRecommendations": [],
                    })
            if ai_mockups:
                quote_data["ai_mockups"] = ai_mockups
                logger.info(f"Generated {sum(len(m['generated_images']) for m in ai_mockups)} mockup images for quick quote")
        except Exception as e:
            logger.warning(f"Quick quote mockup generation failed: {e}")

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


# ── EMAIL TOOLS ───────────────────────────────────────────────────

@tool("send_email")
def _send_email(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Send an email with optional file attachments."""
    to = params.get("to", "").strip()
    subject = params.get("subject", "").strip()
    body = params.get("body", "").strip()
    if not to or not subject or not body:
        return ToolResult(tool="send_email", success=False, error="to, subject, and body are required")

    attachments = params.get("attachments", [])
    cc = params.get("cc")

    try:
        from app.services.max.email_service import EmailService
        svc = EmailService()
        if not svc.is_configured:
            return ToolResult(tool="send_email", success=False, error="Email not configured — set SMTP_USER and SMTP_PASSWORD in .env")
        svc.send(to=to, subject=subject, body_html=body, attachments=attachments, cc=cc)
        return ToolResult(tool="send_email", success=True, result={"sent_to": to, "subject": subject})
    except Exception as e:
        return ToolResult(tool="send_email", success=False, error=str(e))


@tool("send_quote_email")
def _send_quote_email(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Generate PDF for a quote and send it to a recipient via email."""
    quote_id = params.get("quote_id", "")
    to = params.get("to", "").strip()
    if not quote_id:
        return ToolResult(tool="send_quote_email", success=False, error="No quote_id provided")
    if not to:
        return ToolResult(tool="send_quote_email", success=False, error="No recipient email (to) provided")

    # Load quote
    quote_path = os.path.join(QUOTES_DIR, f"{quote_id}.json")
    if not os.path.exists(quote_path):
        return ToolResult(tool="send_quote_email", success=False, error=f"Quote {quote_id} not found")

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
            return ToolResult(tool="send_quote_email", success=False, error="PDF generation failed")
    except Exception as e:
        return ToolResult(tool="send_quote_email", success=False, error=f"PDF generation failed: {e}")

    # Send via email
    try:
        from app.services.max.email_service import EmailService
        svc = EmailService()
        if not svc.is_configured:
            return ToolResult(tool="send_quote_email", success=False, error="Email not configured — set SMTP_USER and SMTP_PASSWORD in .env")

        subject = f"Estimate {quote_number} — {customer}"
        body_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h2 style="color: #D4AF37;">Estimate {quote_number}</h2>
            <p>Hi,</p>
            <p>Please find attached your estimate for review.</p>
            <table style="margin: 16px 0; border-collapse: collapse;">
                <tr><td style="padding: 4px 12px 4px 0; font-weight: bold;">Customer:</td><td>{customer}</td></tr>
                <tr><td style="padding: 4px 12px 4px 0; font-weight: bold;">Estimate Total:</td><td>${total:,.2f}</td></tr>
                <tr><td style="padding: 4px 12px 4px 0; font-weight: bold;">Quote #:</td><td>{quote_number}</td></tr>
            </table>
            <p>If you have any questions, please don't hesitate to reach out.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
            <p style="color: #888; font-size: 12px;">Sent via Empire — Powered by MAX AI</p>
        </div>
        """

        svc.send(to=to, subject=subject, body_html=body_html, attachments=[pdf_path])
        return ToolResult(tool="send_quote_email", success=True, result={
            "sent_to": to, "quote_number": quote_number, "customer": customer, "total": total,
        })
    except Exception as e:
        return ToolResult(tool="send_quote_email", success=False, error=f"Email send failed: {e}")


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
        headers = {"Authorization": f"Client-ID {unsplash_key}"}
        resp = httpx.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": 3, "orientation": "landscape"},
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return ToolResult(tool="search_images", success=False, error=f"Unsplash API error: {resp.status_code}")

        photos = resp.json().get("results", [])
        images = []
        for p in photos[:3]:
            # Trigger download event (Unsplash API guideline)
            download_url = p.get("links", {}).get("download_location")
            if download_url:
                try:
                    httpx.get(download_url, headers=headers, timeout=5)
                except Exception:
                    pass
            images.append({
                "url": p["urls"]["regular"],
                "alt": p.get("alt_description", query),
                "credit": p["user"]["name"],
                "credit_url": p["user"]["links"]["html"] + "?utm_source=empirebox&utm_medium=referral",
                "unsplash_url": p["links"]["html"] + "?utm_source=empirebox&utm_medium=referral",
            })
        return ToolResult(tool="search_images", success=True, result={"images": images, "query": query})
    except Exception as e:
        return ToolResult(tool="search_images", success=False, error=f"Image search failed: {e}")


# ── WEB SEARCH TOOL ───────────────────────────────────────────────

@tool("web_search")
def _web_search(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Search the web via DuckDuckGo. Returns titles, URLs, and snippets."""
    query = params.get("query", "").strip()
    if not query:
        return ToolResult(tool="web_search", success=False, error="Query is required")

    num_results = min(int(params.get("num_results", 5)), 10)

    try:
        from duckduckgo_search import DDGS
        raw = DDGS().text(query, max_results=num_results)
        results = [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in raw]
        return ToolResult(tool="web_search", success=True, result={
            "query": query, "results": results, "count": len(results), "source": "DuckDuckGo",
        })
    except Exception as e:
        return ToolResult(tool="web_search", success=False, error=f"Web search failed: {e}")


@tool("web_read")
def _web_read(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Fetch a web page and extract its text content."""
    url = params.get("url", "").strip()
    if not url:
        return ToolResult(tool="web_read", success=False, error="URL is required")

    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; EmpireBot/1.0)"},
            timeout=15,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return ToolResult(tool="web_read", success=False, error=f"HTTP {resp.status_code}")

        content_type = resp.headers.get("content-type", "")
        if "html" in content_type:
            text = _html_to_text(resp.text)
        else:
            text = resp.text

        # Truncate to avoid overwhelming the AI
        max_chars = int(params.get("max_chars", 6000))
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[Truncated — {len(text)} chars total]"

        return ToolResult(tool="web_read", success=True, result={
            "url": url, "content": text, "length": len(text),
        })
    except Exception as e:
        return ToolResult(tool="web_read", success=False, error=f"Web read failed: {e}")


def _html_to_text(html: str) -> str:
    """Extract readable text from HTML, stripping tags, scripts, styles."""
    # Remove script/style blocks
    text = re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove nav/header/footer
    text = re.sub(r'<(nav|header|footer)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Convert common elements to readable text
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</(p|div|h[1-6]|li|tr)>', '\n', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Decode HTML entities
    import html as html_mod
    text = html_mod.unescape(text)
    return text.strip()


# ── PHOTO-TO-QUOTE PIPELINE TOOL ──────────────────────────────────

@tool("photo_to_quote")
def _photo_to_quote(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Create a quote from photo analysis and send the PDF via Telegram in one step."""
    # Step 1: Create the quote (reuses create_quick_quote logic)
    quote_result = _create_quick_quote(params, desk)
    if not quote_result.success:
        return ToolResult(tool="photo_to_quote", success=False,
                         error=f"Quote creation failed: {quote_result.error}")

    quote_id = quote_result.result.get("quote_id", "")
    quote_number = quote_result.result.get("quote_number", "")

    # Step 2: Send via Telegram (reuses send_quote_telegram logic)
    send_result = _send_quote_telegram({"quote_id": quote_id}, desk)

    return ToolResult(tool="photo_to_quote", success=True, result={
        "quote_id": quote_id,
        "quote_number": quote_number,
        "customer_name": quote_result.result.get("customer_name"),
        "total": quote_result.result.get("total"),
        "items_count": quote_result.result.get("items_count"),
        "telegram_sent": send_result.success,
        "telegram_error": send_result.error if not send_result.success else None,
    })


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


# ── PRESENTATION PDF + TELEGRAM TOOL ──────────────────────────────

PRESENTATIONS_DIR = os.path.expanduser("~/Empire/data/presentations")


def _render_presentation_pdf(data: dict) -> str:
    """Render presentation data as a professional PDF. Returns the file path."""
    import re as _re
    from weasyprint import HTML as WeasyHTML

    title = data.get("title", "Presentation")
    subtitle = data.get("subtitle", "")
    sections = data.get("sections", [])
    charts = data.get("charts", [])
    sources = data.get("sources", [])
    images = data.get("images", [])
    model_used = data.get("model_used", "MAX AI")
    generated_at = data.get("generated_at", datetime.utcnow().isoformat())

    # Build sections HTML
    sections_html = ""
    for section in sections:
        heading = section.get("heading", "")
        content = section.get("content", "").replace("\n", "<br>")
        stype = section.get("type", "text")

        if stype == "highlight":
            sections_html += f"""<div style="margin:16px 0;padding:16px 20px;background:linear-gradient(135deg,#fffcf0,#f8f5ff);
                border-left:4px solid #D4AF37;border-radius:0 8px 8px 0">
                <h2 style="color:#D4AF37;margin:0 0 8px;font-size:1.05em">{heading}</h2>
                <div style="font-size:0.88em;color:#333;line-height:1.6">{content}</div></div>"""
        elif stype == "bullets":
            # Convert - items to HTML list
            items = [line.strip().lstrip("- ") for line in section.get("content", "").split("\n") if line.strip()]
            li_html = "".join(f"<li style='margin:3px 0;font-size:0.88em;color:#333'>{item}</li>" for item in items)
            sections_html += f"""<div style="margin:16px 0">
                <h2 style="color:#8B5CF6;margin:0 0 8px;font-size:1.05em">{heading}</h2>
                <ul style="padding-left:20px;margin:0">{li_html}</ul></div>"""
        else:
            sections_html += f"""<div style="margin:16px 0">
                <h2 style="color:#1a1a2e;margin:0 0 8px;font-size:1.05em">{heading}</h2>
                <div style="font-size:0.88em;color:#333;line-height:1.6">{content}</div></div>"""

    # Build charts as HTML tables
    charts_html = ""
    for chart in charts:
        headers = chart.get("headers", [])
        rows = chart.get("rows", [])
        if headers and rows:
            th = "".join(f"<th style='padding:6px 10px;background:#1a1a2e;color:#D4AF37;font-size:0.78em;text-transform:uppercase'>{h}</th>" for h in headers)
            tr = ""
            for row in rows:
                cells = "".join(f"<td style='padding:6px 10px;border-bottom:1px solid #eee;font-size:0.85em'>{c}</td>" for c in row)
                tr += f"<tr>{cells}</tr>"
            charts_html += f"""<div style="margin:16px 0">
                <h3 style="color:#D4AF37;font-size:0.9em;margin:0 0 6px">{chart.get('title', 'Data')}</h3>
                <table style="width:100%;border-collapse:collapse"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>"""

    # Build images HTML (embedded from Unsplash URLs)
    images_html = ""
    if images:
        imgs = ""
        for img in images[:3]:
            credit = img.get("credit", "")
            imgs += f"""<div style="flex:1;min-width:180px">
                <img src="{img['url']}" style="width:100%;height:140px;object-fit:cover;border-radius:6px" />
                <p style="font-size:0.6em;color:#999;margin:2px 0">Photo by {credit} on Unsplash</p></div>"""
        images_html = f'<div style="display:flex;gap:12px;margin:16px 0">{imgs}</div>'

    # Build sources
    sources_html = ""
    if sources:
        items = "".join(
            f"<p style='margin:3px 0;font-size:0.8em;color:#555'>{i+1}. <a href=\"{s.get('url','#')}\" style=\"color:#8B5CF6\">{s.get('title','Source')}</a> — {s.get('description','')}</p>"
            for i, s in enumerate(sources)
        )
        sources_html = f"""<div style="margin:20px 0;padding:12px 16px;background:#fafafa;border-radius:8px;border:1px solid #eee">
            <p style="margin:0 0 6px;font-size:0.72em;text-transform:uppercase;letter-spacing:0.5px;color:#999;font-weight:600">Sources</p>
            {items}</div>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
  @page {{ size: letter; margin: 0.6in 0.7in; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #222; max-width: 800px; margin: 0 auto; padding: 0; font-size: 12.5px; line-height: 1.5; }}
</style></head><body>

<!-- Header -->
<div style="border-bottom:3px solid #D4AF37;padding-bottom:16px;margin-bottom:20px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h1 style="margin:0;color:#1a1a2e;font-size:24px;letter-spacing:-0.5px">{title}</h1>
      <p style="margin:4px 0 0;color:#888;font-size:0.9em">{subtitle}</p>
    </div>
    <div style="text-align:right;padding-top:4px">
      <div style="background:linear-gradient(135deg,#D4AF37,#8B5CF6);color:white;padding:6px 14px;border-radius:6px;font-weight:700;font-size:0.85em;letter-spacing:1px;display:inline-block">PRESENTATION</div>
      <p style="margin:4px 0 0;color:#999;font-size:0.75em">{generated_at[:10]}</p>
    </div>
  </div>
</div>

{sections_html}
{charts_html}
{images_html}
{sources_html}

<!-- Footer -->
<div style="margin-top:28px;padding-top:12px;border-top:1px solid #eee;text-align:center">
  <p style="margin:0;color:#aaa;font-size:0.72em">Empire &middot; Generated by MAX AI ({model_used})</p>
  <p style="margin:2px 0 0;color:#ccc;font-size:0.65em">{generated_at[:10]}</p>
</div>
</body></html>"""

    pdf_bytes = WeasyHTML(string=html).write_pdf()

    os.makedirs(PRESENTATIONS_DIR, exist_ok=True)
    slug = _re.sub(r'[^a-z0-9]+', '-', title.lower())[:40].strip('-')
    ts = datetime.utcnow().strftime("%y%m%d_%H%M")
    filename = f"{ts}_{slug}.pdf"
    pdf_path = os.path.join(PRESENTATIONS_DIR, filename)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    return pdf_path


@tool("present")
def _present(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Generate a presentation on a topic, render as PDF, and send via Telegram."""
    topic = params.get("topic", "").strip()
    if not topic:
        return ToolResult(tool="present", success=False, error="Topic is required")

    source_content = params.get("source_content")

    # Step 1: Generate presentation via AI
    try:
        from app.services.max.presentation_builder import build_presentation
        data = _run_async(build_presentation(topic, source_content))
    except Exception as e:
        return ToolResult(tool="present", success=False, error=f"Presentation generation failed: {e}")

    # Step 2: Render PDF
    try:
        pdf_path = _render_presentation_pdf(data)
    except Exception as e:
        return ToolResult(tool="present", success=False, error=f"PDF rendering failed: {e}")

    # Step 3: Send via Telegram
    telegram_sent = False
    try:
        from app.services.max.telegram_bot import TelegramBot
        bot = TelegramBot()
        if bot.is_configured:
            section_count = len(data.get("sections", []))
            caption = (
                f"\U0001f4ca <b>{data.get('title', topic)}</b>\n"
                f"\U0001f4dd {section_count} sections &middot; {data.get('model_used', 'AI')}\n"
                f"\U0001f4c5 {datetime.utcnow().strftime('%b %d, %Y')}"
            )
            telegram_sent = _run_async(bot.send_document(pdf_path, caption=caption))
    except Exception as e:
        logger.warning(f"Telegram send failed for presentation: {e}")

    return ToolResult(tool="present", success=True, result={
        "title": data.get("title", topic),
        "subtitle": data.get("subtitle", ""),
        "sections": len(data.get("sections", [])),
        "charts": len(data.get("charts", [])),
        "sources": len(data.get("sources", [])),
        "model_used": data.get("model_used", "unknown"),
        "pdf_path": pdf_path,
        "telegram_sent": telegram_sent,
    })


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
- **send_email** — Send an email with optional file attachments
  `{"tool": "send_email", "to": "client@example.com", "subject": "Your Estimate", "body": "<h2>Hello</h2><p>HTML body here</p>", "attachments": ["/path/to/file.pdf"], "cc": "optional@cc.com"}`
- **send_quote_email** — Generate a quote PDF and email it to the recipient
  `{"tool": "send_quote_email", "quote_id": "abc123", "to": "client@example.com"}`
  Use this after creating/saving a quote to email the PDF directly to a client or the founder.

### Research Tools
- **web_search** — Search the web for current information, prices, suppliers, tutorials, or any topic. Returns titles, URLs, and snippets from DuckDuckGo.
  `{"tool": "web_search", "query": "best fabric suppliers for drapery wholesale", "num_results": 5}`
  Use for: research, current pricing, supplier info, industry news, competitor analysis, or any factual question needing live data.
  After getting results, cite sources with markdown links: [Title](url)
- **web_read** — Fetch and read a web page. Returns extracted text content from any URL.
  `{"tool": "web_read", "url": "https://example.com/article", "max_chars": 6000}`
  Use after web_search to read full articles, or when the user shares a URL. Combine with web_search for deep research.
- **search_images** — Search for relevant images (Unsplash) to enhance your response. Embed results in markdown.
  `{"tool": "search_images", "query": "modern ripplefold drapery"}`
  After getting results, use: `![description](url)` to embed images in your response.
- **photo_to_quote** — Create a quote from photo analysis and send the PDF via Telegram in one step. Use this when analyzing a photo of windows/furniture that needs a quote.
  `{"tool": "photo_to_quote", "customer_name": "Customer", "rooms": [{"name": "Room", "windows": [{"name": "Window 1", "width": 72, "height": 84, "quantity": 1, "treatmentType": "ripplefold"}]}], "max_analysis": "Professional analysis..."}`
  This automatically creates the quote, generates the PDF, and sends it via Telegram.

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
When you need current info, pricing, or research — use web_search. Do NOT say "I can't access the web."
When analyzing a photo of windows or furniture, use photo_to_quote to create and deliver the estimate automatically.
When asked to present, brief, or report on a topic — use the present tool to generate a PDF and send via Telegram.

### Presentation Tools
- **present** — Generate a professional presentation/report on any topic and send PDF via Telegram. Use for briefings, research reports, market analysis, or any topic the founder wants presented.
  `{"tool": "present", "topic": "DC custom drapery market trends 2026"}`
  `{"tool": "present", "topic": "Competitor analysis", "source_content": "Optional context..."}`
  Creates a multi-section PDF with data tables, images, and sources — then sends via Telegram automatically.
"""
