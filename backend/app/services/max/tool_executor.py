"""MAX Tool Executor — parses tool blocks from AI responses and executes real actions.

Tools give MAX the ability to query real data and take real actions instead of
fabricating responses. Inspired by the OpenClaw skills-augmented agent pattern.
"""
import re
import json
import os
import uuid
import logging
import asyncio
import psutil
import httpx
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.config.business_config import biz
from app.db.database import get_db, dict_row, dict_rows
from app.services.max.inpaint_service import inpaint_service

try:
    from app.services.max.access_control import access_controller
except ImportError:
    access_controller = None

# QIS — Quote Intelligence System (real pricing engine)
try:
    from app.services.quote_engine import (
        assemble_quote as qis_assemble_quote,
        analyze_photo_items_sync as qis_analyze_photo,
        generate_all_item_mockups as qis_generate_mockups,
        manual_item as qis_manual_item,
    )
    QIS_AVAILABLE = True
except ImportError:
    QIS_AVAILABLE = False

logger = logging.getLogger("max.tool_executor")

# ── Dangerous Tool PIN Gate ───────────────────────────────────────
DANGEROUS_TOOLS = {"shell_execute", "env_set", "db_query"}
FOUNDER_PIN = os.getenv("FOUNDER_PIN", "7777")

TOOL_BLOCK_RE = re.compile(r"```tool\s*\n(.*?)\n```", re.DOTALL)

QUOTES_DIR = os.path.expanduser("~/empire-repo/backend/data/quotes")


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


def execute_tool(tool_call: dict, desk: Optional[str] = None, access_context: Optional[dict] = None, founder: bool = False) -> ToolResult:
    """Dispatch and execute a tool call (with tier gating and access control).

    Args:
        founder: If True, skip all PIN/access checks. The caller (router) has
                 already verified this is the founder via is_founder_message().
    """
    tool_name = tool_call.get("tool", "")
    try:
        # ── FOUNDER BYPASS: CC / Telegram founder = full access, no PIN ──
        if founder:
            logger.info(f"Founder auto-auth — executing '{tool_name}' without PIN/access check")
            tool_call["_founder"] = True  # pass founder flag to tool handlers
        else:
            # Access control check (non-founder users)
            if access_context and access_controller:
                user = access_context.get("user")
                if user:
                    level = int(access_controller.classify_tool(tool_name))
                    action, _ = access_controller.check_permission(user, tool_name, desk)
                    if action == "deny":
                        access_controller.audit_log(user.get("id", ""), tool_name, level, "denied", channel=user.get("channel", ""))
                        return ToolResult(tool=tool_name, success=False, error="Access denied: insufficient permissions")
                    if action == "locked":
                        return ToolResult(tool=tool_name, success=False, error="Account locked due to failed PIN attempts. Try again in 15 minutes.")
                    if action == "confirm":
                        session_id = access_controller.create_pending_session(
                            user.get("id", ""), tool_name, tool_call, desk,
                            user.get("channel", ""), user.get("chat_id", ""), level
                        )
                        summary = f"Tool '{tool_name}' requires confirmation"
                        access_controller.audit_log(user.get("id", ""), tool_name, level, "pending_confirm", channel=user.get("channel", ""))
                        return ToolResult(tool=tool_name, success=False, error=f"__ACCESS_PENDING__confirm__{session_id}__{summary}")
                    if action == "pin":
                        session_id = access_controller.create_pending_session(
                            user.get("id", ""), tool_name, tool_call, desk,
                            user.get("channel", ""), user.get("chat_id", ""), level
                        )
                        summary = f"Tool '{tool_name}' requires PIN authorization"
                        access_controller.audit_log(user.get("id", ""), tool_name, level, "pending_pin", channel=user.get("channel", ""))
                        return ToolResult(tool=tool_name, success=False, error=f"__ACCESS_PENDING__pin__{session_id}__{summary}")

            # Dangerous tool PIN gate (legacy — only for non-founder)
            if tool_name in DANGEROUS_TOOLS:
                pin = (access_context or {}).get("pin")
                if not pin:
                    return ToolResult(
                        tool=tool_name, success=False,
                        error=f"⚠️ Tool '{tool_name}' is restricted. Please provide your founder PIN to proceed."
                    )
                if str(pin) != FOUNDER_PIN:
                    logger.warning(f"Invalid PIN attempt for dangerous tool '{tool_name}'")
                    return ToolResult(
                        tool=tool_name, success=False,
                        error="❌ Invalid PIN. Access denied."
                    )
                logger.info(f"PIN verified — executing dangerous tool '{tool_name}'")

        # Tier check
        from app.middleware.tier_middleware import require_tool
        tier_error = require_tool(tool_name)
        if tier_error:
            return ToolResult(tool=tool_name, success=False, error=tier_error)

        # ── Auto-correct common tool name mistakes ──
        TOOL_CORRECTIONS = {
            "run_command": "shell_execute",
            "execute_command": "shell_execute",
            "run_shell": "shell_execute",
            "exec": "shell_execute",
            "command": "shell_execute",
            "bash": "shell_execute",
            "terminal": "shell_execute",
            "draw": "sketch_to_drawing",
            "generate_drawing": "sketch_to_drawing",
            "create_drawing": "sketch_to_drawing",
            "analyze_furniture": "sketch_to_drawing",
            "furniture_analyzer": "sketch_to_drawing",
            "analyze_photo": "sketch_to_drawing",
            "queue_task": "queue_openclaw_task",
            "openclaw_task": "queue_openclaw_task",
            "create_openclaw_task": "queue_openclaw_task",
            "openclaw": "dispatch_to_openclaw",
            "send_mail": "send_email",
            "email": "send_email",
            "check_mail": "check_email",
            "check_inbox": "check_email",
            "gmail": "check_email",
            "read_email": "check_email",
            "inbox": "check_email",
            "find_quotes": "search_quotes",
            "list_quotes": "search_quotes",
            "search_quote": "search_quotes",
            "get_quotes": "search_quotes",
            "find_contacts": "search_contacts",
            "list_contacts": "search_contacts",
            "find_customer": "search_contacts",
            "search_customer": "search_contacts",
            "read_file": "file_read",
            "write_file": "file_write",
            "edit_file": "file_edit",
            "append_file": "file_append",
            "create_quote": "create_quick_quote",
            "make_quote": "create_quick_quote",
            "send_message": "send_telegram",
            "git": "git_ops",
            "telegram": "send_telegram",
            "desk_task": "run_desk_task",
            "reset": "reset_max_state",
        }
        if tool_name not in TOOL_REGISTRY and tool_name in TOOL_CORRECTIONS:
            corrected = TOOL_CORRECTIONS[tool_name]
            logger.info(f"Auto-corrected tool '{tool_name}' → '{corrected}'")
            tool_name = corrected
            tool_call["tool"] = corrected

        handler = TOOL_REGISTRY.get(tool_name)
        if handler:
            return handler(tool_call, desk)

        available = ", ".join(sorted(TOOL_REGISTRY.keys()))
        return ToolResult(tool=tool_name, success=False,
                          error=f"Unknown tool: {tool_name}. Available tools: {available}")
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

    # Also queue to OpenClaw for autonomous execution
    openclaw_queued = False
    try:
        import httpx as _oc_httpx
        _oc_resp = _oc_httpx.post(
            "http://localhost:8000/api/v1/openclaw/tasks",
            json={
                "title": title,
                "description": description or title,
                "desk": task_desk,
                "priority": {"urgent": 1, "high": 3, "normal": 5, "low": 7}.get(priority, 5),
                "source": "create_task",
                "parent_task_id": task_id,
            },
            timeout=5,
        )
        openclaw_queued = _oc_resp.status_code == 200
    except Exception:
        pass

    # Immediate execution: fire desk_manager.submit_task in background
    auto_executing = False
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_auto_execute_new_task(task_id, title, description or title, priority, task_desk))
        auto_executing = True
    except RuntimeError:
        pass  # No event loop — background worker will pick it up in ≤30s

    return ToolResult(tool="create_task", success=True, result={
        "task_id": task_id, "title": title, "priority": priority,
        "desk": task_desk, "status": "todo", "openclaw_queued": openclaw_queued,
        "auto_executing": auto_executing,
    })


async def _auto_execute_new_task(task_id: str, title: str, description: str, priority: str, desk: str):
    """Background coroutine: immediately execute a newly created task via desk system."""
    try:
        from app.services.max.desks.desk_manager import desk_manager
        desk_manager.initialize()

        # Mark in_progress
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = 'in_progress', updated_at = datetime('now') WHERE id = ? AND status = 'todo'",
                (task_id,),
            )

        result = await asyncio.wait_for(
            desk_manager.submit_task(
                title=title,
                description=description,
                priority=priority,
                source="auto_execute",
                db_task_id=task_id,
            ),
            timeout=60.0,
        )

        state = result.state.value if hasattr(result.state, "value") else str(result.state)
        logger.info(f"Auto-executed task {task_id}: {title} → {state}")

        # Telegram notification
        try:
            from app.services.max.telegram_bot import telegram_bot
            if telegram_bot.is_configured:
                emoji = "✅" if state == "completed" else "❌" if state == "failed" else "⏳"
                summary = (result.result or "")[:200]
                await telegram_bot.send_message(
                    f"{emoji} <b>Task Auto-Executed</b>\n<b>{title}</b>\nStatus: {state}\n{summary}",
                )
        except Exception:
            pass

    except asyncio.TimeoutError:
        logger.warning(f"Auto-execute timed out for task {task_id}: {title}")
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = 'todo', updated_at = datetime('now') WHERE id = ?",
                (task_id,),
            )
    except Exception as e:
        logger.error(f"Auto-execute failed for task {task_id}: {e}")


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
    """Search quotes by customer name or status. Searches BOTH Workroom and CraftForge quotes."""
    customer = params.get("customer_name", "").lower()
    status = params.get("status")
    source_filter = params.get("source", "").lower()  # "workroom", "craftforge", or "" for both
    limit = min(params.get("limit", 10), 20)

    quotes = []

    # ── Search Workroom quotes ──
    if source_filter in ("", "workroom", "all"):
        if os.path.exists(QUOTES_DIR):
            for fname in os.listdir(QUOTES_DIR):
                if not fname.endswith(".json") or fname.startswith("_") or "_verification" in fname:
                    continue
                try:
                    with open(os.path.join(QUOTES_DIR, fname)) as f:
                        q = json.load(f)
                    if "id" not in q:
                        continue
                except (json.JSONDecodeError, OSError):
                    continue
                if customer and customer not in q.get("customer_name", "").lower():
                    continue
                if status and q.get("status") != status:
                    continue
                # Resolve total: flat field → tiers.A → tiers.B → tiers.C
                total = q.get("total") or 0
                if not total:
                    tiers = q.get("tiers") or {}
                    for t in ("A", "B", "C"):
                        tier = tiers.get(t)
                        if tier and tier.get("subtotal"):
                            total = tier["subtotal"]
                            break
                # Resolve items count: flat line_items → tiers items → rooms
                items_count = len(q.get("line_items") or [])
                if not items_count:
                    tiers = q.get("tiers") or {}
                    tier_a = tiers.get("A") or {}
                    items_count = len(tier_a.get("items") or [])
                if not items_count:
                    items_count = sum(len(r.get("items") or r.get("windows") or []) for r in (q.get("rooms") or []))
                quotes.append({
                    "id": q["id"],
                    "quote_number": q.get("quote_number"),
                    "customer_name": q.get("customer_name"),
                    "total": total,
                    "status": q.get("status"),
                    "created_at": q.get("created_at", "")[:10],
                    "items_count": items_count,
                    "source": "workroom",
                })

    # ── Search CraftForge quotes ──
    cf_dir = os.path.expanduser("~/empire-repo/backend/data/craftforge/designs")
    if source_filter in ("", "craftforge", "all"):
        if os.path.exists(cf_dir):
            for fname in os.listdir(cf_dir):
                if not fname.endswith(".json") or fname.startswith("_"):
                    continue
                try:
                    with open(os.path.join(cf_dir, fname)) as f:
                        q = json.load(f)
                    if "id" not in q:
                        continue
                except (json.JSONDecodeError, OSError):
                    continue
                if customer and customer not in q.get("customer_name", "").lower():
                    continue
                if status and q.get("status") != status:
                    continue
                total = q.get("total") or q.get("subtotal") or 0
                items_count = len(q.get("line_items") or q.get("materials") or [])
                quotes.append({
                    "id": q["id"],
                    "quote_number": q.get("design_number") or q.get("quote_number"),
                    "customer_name": q.get("customer_name"),
                    "total": total,
                    "status": q.get("status"),
                    "created_at": q.get("created_at", "")[:10],
                    "items_count": items_count,
                    "source": "craftforge",
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
    customer_name = params.get("customer_name", "")
    quote_number = _next_quote_number(customer_name) if customer_name else ""
    return ToolResult(tool="open_quote_builder", success=True, result={
        "action": "open_quote_builder",
        "quote_number": quote_number,
        "customer_name": customer_name,
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

LABOR_RATE = biz.labor_rate
INSTALL_PER_WINDOW = biz.install_rate_per_window
DC_TAX_RATE = biz.tax_rate


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
    fabric_color = win.get("fabricColor", "")
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
        color_note = f" in {fabric_color}" if fabric_color else ""
        items.append({
            "room": room_name,
            "description": f"Fabric — {grade_info['label']} Grade{color_note} ({total_yards} yds) for {label}",
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


# ── QUOTE NUMBERING ──────────────────────────────────────────────

COUNTER_FILE = os.path.join(QUOTES_DIR, "_counter.json")


def _next_quote_number(customer_name: str = "") -> str:
    """Generate sequential quote number: EST-YYYY-NNN.

    Uses the same global counter as the quotes router so all quotes
    are numbered sequentially regardless of creation method.
    """
    year = datetime.utcnow().year
    counter = {"year": year, "seq": 0}
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE) as f:
                counter = json.load(f)
            if counter.get("year") != year:
                counter = {"year": year, "seq": 0}
        except Exception:
            counter = {"year": year, "seq": 0}
    counter["seq"] += 1
    with open(COUNTER_FILE, "w") as f:
        json.dump(counter, f)
    return f"EST-{year}-{counter['seq']:03d}"


# ── QUICK QUOTE TOOL ──────────────────────────────────────────────

# ── QIS HELPERS ─────────────────────────────────────────────────
# Map MAX tool treatmentType strings to QIS item_analyzer types
_TREATMENT_TO_QIS_TYPE = {
    "ripplefold": "drapery_panel",
    "pinch-pleat": "drapery_panel",
    "rod-pocket": "drapery_panel",
    "grommet": "drapery_panel",
    "roman-shade": "roman_shade",
    "roller-shade": "roller_shade",
    "valance": "valance",
    "cornice": "cornice",
    "swag": "swag",
}


def _rooms_to_qis_items(rooms: list) -> list:
    """Convert MAX rooms/windows format to QIS analyzed_items format."""
    items = []
    for room in rooms:
        room_name = room.get("name", "Room")
        for win in room.get("windows", []):
            treatment = win.get("treatmentType", "ripplefold")
            qis_type = _TREATMENT_TO_QIS_TYPE.get(treatment, "drapery_panel")
            name = win.get("name", "Window")
            items.append({
                "name": f"{room_name} — {name}",
                "type": qis_type,
                "quantity": win.get("quantity", 1),
                "dimensions": {
                    "width": win.get("width", 48),
                    "height": win.get("height", 60),
                },
                "construction": "plain",
                "condition": "new_construction",
                "special_features": [],
                "cushion_count": 0,
            })
        for uph in room.get("upholstery", []):
            uph_type = uph.get("type", "accent_chair")
            items.append({
                "name": f"{room_name} — {uph.get('description', 'Upholstery')}",
                "type": uph_type,
                "quantity": uph.get("quantity", 1),
                "dimensions": {
                    "width": uph.get("width", 36),
                    "height": uph.get("height", 36),
                    "depth": uph.get("depth", 24),
                },
                "construction": uph.get("construction", "plain"),
                "condition": uph.get("condition", "good"),
                "special_features": uph.get("special_features", []),
                "cushion_count": uph.get("cushion_count", 0),
            })
    return items


def _qis_tiers_to_design_proposals(qis_tiers: dict, rooms: list) -> list:
    """Convert QIS tier output to the design_proposals format used by the quote JSON."""
    proposals = []
    tier_labels = {
        "A": "Option A — Essential",
        "B": "Option B — Designer",
        "C": "Option C — Premium",
    }
    lining_map = {"A": "standard", "B": "standard", "C": "blackout"}

    for key in ("A", "B", "C"):
        tier = qis_tiers.get(key, {})
        # Convert QIS line items to tool executor format
        line_items = []
        for tier_item in tier.get("items", []):
            for li in tier_item.get("line_items", []):
                line_items.append({
                    "room": tier_item.get("name", "").split(" — ")[0] if " — " in tier_item.get("name", "") else "Room",
                    "description": li.get("description", ""),
                    "quantity": li.get("quantity", 1),
                    "unit_price": li.get("unit_price", li.get("amount", 0)),
                    "total": li.get("amount", 0),
                    "category": li.get("category", "other"),
                })

        proposals.append({
            "label": tier_labels.get(key, f"Option {key}"),
            "fabric_grade": key,
            "lining_type": lining_map.get(key, "standard"),
            "line_items": line_items,
            "subtotal": tier.get("subtotal", 0),
            "tax_amount": tier.get("tax", 0),
            "total": tier.get("total", 0),
            "ai_comment": "",
            "selected": False,
        })
    return proposals


@tool("create_quick_quote")
def _create_quick_quote(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Create a quick quote autonomously — no customer info required.
    Defaults to 'Customer 1' if no name provided. Saves JSON + generates PDF.
    Uses global sequential EST-YYYY-NNN numbering and supports stacked design proposals.
    """
    quote_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    customer_name = params.get("customer_name", "Customer 1") or "Customer 1"
    quote_number = _next_quote_number(customer_name)
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

    # Build stacked design proposals (3 options: A, B, C) if rooms have windows
    scope = params.get("scope", "full")  # full | fabric-only | hardware-upgrade
    SCOPE_CATEGORIES = {
        "full": None,  # None = include all
        "fabric-only": {"fabric", "lining"},
        "hardware-upgrade": {"hardware"},
    }
    scope_filter = SCOPE_CATEGORIES.get(scope)

    design_proposals = params.get("design_proposals", [])
    qis_quote_data = None  # Will hold QIS result if successful
    if not design_proposals and rooms:
        # ── Try QIS pricing engine first ──
        if QIS_AVAILABLE:
            try:
                qis_items = _rooms_to_qis_items(rooms)
                if qis_items:
                    location = params.get("location", "DC")
                    lining = params.get("lining", "standard")
                    qis_quote_data = qis_assemble_quote(
                        analyzed_items=qis_items,
                        customer_name=customer_name,
                        location=location,
                        lining=lining,
                    )
                    # Save to disk (assemble_quote no longer auto-saves)
                    import os, json as _json
                    _qdir = os.path.expanduser("~/empire-repo/backend/data/quotes")
                    os.makedirs(_qdir, exist_ok=True)
                    with open(os.path.join(_qdir, f"{qis_quote_data['id']}.json"), "w") as _qf:
                        _json.dump(qis_quote_data, _qf, indent=2, default=str)
                    qis_tiers = qis_quote_data.get("tiers", {})
                    if qis_tiers:
                        design_proposals = _qis_tiers_to_design_proposals(qis_tiers, rooms)
                        logger.info("QIS pricing engine generated %d design proposals", len(design_proposals))
            except Exception as qis_err:
                logger.warning("QIS pricing engine failed, falling back to legacy pricing: %s", qis_err)
                design_proposals = []  # Reset so legacy path runs

        # ── Legacy fallback: hardcoded tier pricing ──
        if not design_proposals:
            tier_configs = [
                {"label": "Option A — Essential", "grade": "A", "lining": "standard"},
                {"label": "Option B — Designer", "grade": "B", "lining": "standard"},
                {"label": "Option C — Premium", "grade": "C", "lining": "blackout"},
            ]
            for tier in tier_configs:
                tier_items = []
                for room in rooms:
                    room_name = room.get("name", "Room")
                    for win in room.get("windows", []):
                        win_copy = dict(win)
                        win_copy["fabricGrade"] = tier["grade"]
                        win_copy["liningType"] = tier["lining"]
                        all_items = _calc_window_line_items(room_name, win_copy)
                        # Apply scope filter
                        if scope_filter is not None:
                            all_items = [it for it in all_items if it.get("category") in scope_filter]
                        tier_items.extend(all_items)
                    for uph in room.get("upholstery", []):
                        desc = uph.get("description", "Upholstery item")
                        price = uph.get("price", 250)
                        tier_items.append({
                            "room": room_name, "description": desc,
                            "quantity": 1, "unit_price": price, "total": price, "category": "upholstery",
                        })
                tier_subtotal = round(sum(item["total"] for item in tier_items), 2)
                tier_tax = round(tier_subtotal * DC_TAX_RATE, 2)
                tier_total = round(tier_subtotal + tier_tax, 2)
                design_proposals.append({
                    "label": tier["label"],
                    "fabric_grade": tier["grade"],
                    "lining_type": tier["lining"],
                    "line_items": tier_items,
                    "subtotal": tier_subtotal,
                    "tax_amount": tier_tax,
                    "total": tier_total,
                    "ai_comment": "",
                    "selected": False,
                })

    # ── Generate AI commentary for each design tier ──
    xai_key_for_tiers = os.environ.get("XAI_API_KEY")
    if xai_key_for_tiers and design_proposals and rooms:
        try:
            project_lines = []
            for room in rooms:
                rn = room.get("name", "Room")
                for win in room.get("windows", []):
                    w = win.get("width", 48)
                    h = win.get("height", 60)
                    tt = win.get("treatmentType", "ripplefold").replace("-", " ").title()
                    project_lines.append(f"  {rn}: {win.get('name', 'Window')} ({w}\"W x {h}\"H) — {tt}")
                for uph in room.get("upholstery", []):
                    project_lines.append(f"  {rn}: {uph.get('description', 'Upholstery')}")

            tier_prompt = (
                "You are a luxury window treatment designer writing for a client proposal. "
                f"Customer: {customer_name}\n"
                f"Project items:\n" + "\n".join(project_lines) + "\n\n"
                "Write a brief, compelling 2-3 sentence description for each design tier. "
                "Cover fabric quality, recommended style, and why a client would choose this option.\n\n"
                f"Option A — Essential (${design_proposals[0]['total']:,.0f}): "
                "Grade A fabrics (quality basics), standard lining\n"
                f"Option B — Designer (${design_proposals[1]['total']:,.0f}): "
                "Grade B fabrics (mid-range designer), standard lining\n"
                f"Option C — Premium (${design_proposals[2]['total']:,.0f}): "
                "Grade C fabrics (luxury), blackout lining\n\n"
                'Respond ONLY in JSON: {"A": "...", "B": "...", "C": "..."}'
            )
            tier_resp = httpx.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {xai_key_for_tiers}", "Content-Type": "application/json"},
                json={
                    "model": "grok-3-mini-fast",
                    "messages": [
                        {"role": "system", "content": "You are a luxury interior design consultant. Respond only in valid JSON."},
                        {"role": "user", "content": tier_prompt},
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
                timeout=20,
            )
            if tier_resp.status_code == 200:
                ai_text = tier_resp.json()["choices"][0]["message"]["content"]
                # Parse JSON robustly
                import re as _re
                _match = _re.search(r'\{.*\}', ai_text, _re.DOTALL)
                if _match:
                    comments = json.loads(_match.group())
                    for i, key in enumerate(["A", "B", "C"]):
                        if i < len(design_proposals) and key in comments:
                            design_proposals[i]["ai_comment"] = comments[key]
                    logger.info("Generated AI commentary for 3 design tiers")
        except Exception as e:
            logger.warning(f"AI tier commentary generation failed: {e}")

    # Collect photo references (original images that were uploaded with this quote)
    photo_refs = params.get("photos", [])
    image_filename = params.get("image_filename")
    if image_filename:
        uploads_dir = os.path.expanduser("~/empire-repo/backend/data/uploads/images")
        img_path = os.path.join(uploads_dir, image_filename)
        if os.path.exists(img_path):
            # Store base64 of original photo for PDF embedding
            try:
                import base64 as _b64
                with open(img_path, "rb") as _f:
                    _img_data = _b64.b64encode(_f.read()).decode()
                ext = image_filename.rsplit(".", 1)[-1].lower()
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/jpeg")
                data_uri = f"data:{mime};base64,{_img_data}"
                photo_refs.append({"filename": image_filename, "path": img_path, "type": "original", "data_uri": data_uri})
                # Link photo to first window item for inline display in PDF
                if rooms:
                    first_room = rooms[0]
                    if first_room.get("windows"):
                        first_room["windows"][0]["sourcePhoto"] = data_uri
                    if first_room.get("upholstery"):
                        first_room["upholstery"][0]["sourcePhoto"] = data_uri
                        # Call upholstery vision API to get structured AI analysis for diagrams
                        try:
                            uph_resp = httpx.post(
                                "http://localhost:3001/api/upholstery",
                                json={"image": data_uri},
                                timeout=45,
                            )
                            if uph_resp.status_code == 200:
                                uph_analysis = uph_resp.json()
                                first_uph = first_room["upholstery"][0]
                                first_uph["aiAnalysis"] = uph_analysis
                                # Populate dimensions and details from AI analysis
                                dims = uph_analysis.get("estimated_dimensions", {})
                                if dims.get("width"):
                                    first_uph.setdefault("width", dims["width"])
                                if dims.get("depth"):
                                    first_uph.setdefault("depth", dims["depth"])
                                if dims.get("height"):
                                    first_uph.setdefault("height", dims["height"])
                                if uph_analysis.get("furniture_type"):
                                    first_uph.setdefault("furnitureType", uph_analysis["furniture_type"])
                                if uph_analysis.get("fabric_yards_plain"):
                                    first_uph.setdefault("fabricYards", uph_analysis["fabric_yards_plain"])
                                cushions = uph_analysis.get("cushion_count", {})
                                if cushions.get("seat"):
                                    first_uph.setdefault("cushionCount", cushions["seat"])
                                logger.info(f"Upholstery AI analysis populated: {uph_analysis.get('furniture_type', 'unknown')}")
                        except Exception as uph_err:
                            logger.warning(f"Upholstery vision API call failed: {uph_err}")
            except Exception:
                photo_refs.append({"filename": image_filename, "path": img_path, "type": "original"})

    # Inject per-window price from the mid-tier (B) proposal line items for display
    if design_proposals and len(design_proposals) > 1:
        mid_tier = design_proposals[1]  # Designer tier (B)
        for room in rooms:
            room_name = room.get("name", "Room")
            for win in room.get("windows", []):
                # Sum line items for this window's room
                win_total = sum(
                    item["total"] for item in mid_tier.get("line_items", [])
                    if item.get("room") == room_name
                )
                # Divide by number of windows in that room if multiple
                n_windows = len(room.get("windows", []))
                win["price"] = round(win_total / max(n_windows, 1), 2)

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
        "design_proposals": design_proposals,
        "selected_proposal": None,  # Index of selected proposal (0, 1, 2) — null until chosen
        "photos": photo_refs,
        "ai_outlines": params.get("ai_outlines", []),
        "ai_mockups": params.get("ai_mockups", []),
        "subtotal": 0.0,  # Zero until a proposal is selected
        "tax_rate": DC_TAX_RATE,
        "tax_amount": 0.0,
        "total": 0.0,  # Zero until a proposal is selected
        "proposal_totals": {
            "A": design_proposals[0]["total"] if len(design_proposals) > 0 else 0,
            "B": design_proposals[1]["total"] if len(design_proposals) > 1 else 0,
            "C": design_proposals[2]["total"] if len(design_proposals) > 2 else 0,
        },
        "deposit": {"deposit_percent": 50, "deposit_amount": 0},
        "status": "proposal",  # New status: proposal → draft → sent → accepted
        "scope": scope,
        "style": params.get("style", ""),
        "max_analysis": max_analysis,
        "created_at": now,
        "updated_at": now,
        "expires_at": expires_at,
        "source": "max_quick_quote",
        "pricing_engine": "qis" if qis_quote_data else "legacy",
        "qis_quote_id": qis_quote_data.get("id") if qis_quote_data else None,
        "qis_quote_number": qis_quote_data.get("quote_number") if qis_quote_data else None,
        "terms": "50% deposit required to begin fabrication. Balance due upon installation. All sales final once fabric is cut. Estimate valid for 30 days.",
        "valid_days": 30,
        "business_name": "Empire",
    }

    # Generate per-tier mockup images via InpaintService (Stability AI + Grok fallback)
    style = params.get("style", "")
    photo_b64 = None
    if photo_refs:
        # Prefer the data_uri from the first photo reference
        for pr in photo_refs:
            if pr.get("data_uri"):
                photo_b64 = pr["data_uri"]
                break
            elif pr.get("path") and os.path.exists(pr["path"]):
                import base64 as _b64mod
                with open(pr["path"], "rb") as _pf:
                    photo_b64 = _b64mod.b64encode(_pf.read()).decode()
                break

    if photo_b64 and rooms and design_proposals:
        try:
            mockup_result = _run_async(inpaint_service.generate_all_mockups(
                photo_b64=photo_b64,
                rooms=rooms,
                style=style,
            ))
            # Attach mockup URLs to each design proposal tier
            window_mockups = mockup_result.get("window_mockups", {})
            furniture_mockups = mockup_result.get("furniture_mockups", {})
            first_room_name = rooms[0].get("name", "Room") if rooms else "Room"

            ai_mockups = []
            gen_images = []
            for i, dp in enumerate(design_proposals[:3]):
                grade = dp.get("fabric_grade", chr(65 + i))
                wm = window_mockups.get(grade, {})
                fm = furniture_mockups.get(grade, {})

                # Attach to design proposal
                if wm.get("inpainted_url"):
                    dp["mockup_image"] = wm["inpainted_url"]
                    dp["inpainted_image_url"] = wm["inpainted_url"]
                    dp["inpainted_thumb"] = wm.get("inpainted_thumb", "")
                    gen_images.append({"tier": dp.get("label", f"Option {grade}"), "url": wm["inpainted_url"], "type": "inpainted"})
                if wm.get("clean_url"):
                    dp["clean_mockup_url"] = wm["clean_url"]
                    dp["clean_thumb"] = wm.get("clean_thumb", "")
                    gen_images.append({"tier": dp.get("label", f"Option {grade}"), "url": wm["clean_url"], "type": "clean"})
                if fm.get("inpainted_url"):
                    dp["furniture_inpainted_url"] = fm["inpainted_url"]
                if fm.get("clean_url"):
                    dp["furniture_clean_url"] = fm["clean_url"]

                dp["mockup_provider"] = wm.get("provider") or fm.get("provider") or mockup_result.get("provider", "none")

            # Store mockup metadata on quote
            quote_data["mockup_provider"] = mockup_result.get("provider", "none")
            quote_data["mockup_cost"] = mockup_result.get("total_cost", 0)
            quote_data["mockup_count"] = mockup_result.get("images_generated", 0)

            if gen_images:
                ai_mockups.append({
                    "roomName": first_room_name,
                    "generated_images": gen_images,
                    "proposals": [],
                    "generalRecommendations": [],
                })
                quote_data["ai_mockups"] = ai_mockups
                quote_data["design_proposals"] = design_proposals
                logger.info(f"InpaintService generated {mockup_result.get('images_generated', 0)} mockup images via {mockup_result.get('provider', 'none')}")

        except Exception as inpaint_err:
            logger.warning(f"InpaintService mockup generation failed: {inpaint_err}")

    # Save JSON
    os.makedirs(QUOTES_DIR, exist_ok=True)
    quote_path = os.path.join(QUOTES_DIR, f"{quote_id}.json")
    with open(quote_path, "w") as f:
        json.dump(quote_data, f, indent=2)

    # Generate PDF
    pdf_url = None
    pdf_path = None
    try:
        _run_async(_generate_pdf_for_quote(quote_id))
        pdf_dir = os.path.expanduser("~/empire-repo/backend/data/quotes/pdf")
        pdf_file = os.path.join(pdf_dir, f"{quote_number}.pdf")
        if os.path.exists(pdf_file):
            pdf_url = f"/api/v1/quotes/{quote_id}/pdf"
            pdf_path = pdf_file
    except Exception as e:
        logger.warning(f"Quick quote PDF generation failed: {e}")

    # Build caption with proposal options
    proposal_summary = ""
    for i, dp in enumerate(design_proposals[:3]):
        letter = chr(65 + i)  # A, B, C
        proposal_summary += f"\n  {letter}. {dp['label']}: ${dp['total']:,.2f}"

    caption = (
        f"\U0001f4cb <b>{quote_number}</b>\n"
        f"\U0001f464 {customer_name}\n"
        f"\U0001f4b0 3 Design Options:{proposal_summary}\n"
        f"\n\u2139\ufe0f Total: $0 — select an option to finalize"
    )

    logger.info(f"Quick quote created: {quote_number} for {customer_name} — 3 proposals")
    return ToolResult(tool="create_quick_quote", success=True, result={
        "quote_id": quote_id,
        "quote_number": quote_number,
        "customer_name": customer_name,
        "total": 0,  # Zero until proposal selected
        "proposal_totals": quote_data["proposal_totals"],
        "items_count": len(line_items),
        "pdf_url": pdf_url,
        "pdf_path": pdf_path,
        "caption": caption,
        "line_items": line_items,
        "design_proposals_count": len(design_proposals),
        "mockup_provider": quote_data.get("mockup_provider", "none"),
        "mockup_cost": quote_data.get("mockup_cost", 0),
        "mockup_count": quote_data.get("mockup_count", 0),
    })


# ── PROPOSAL SELECTION TOOL ─────────────────────────────────────────

@tool("select_proposal")
def _select_proposal(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Select a design proposal (A/B/C) on a quote, finalizing the total.
    Converts the quote from 'proposal' status to 'draft' with real totals.
    """
    quote_id = params.get("quote_id", "")
    option = params.get("option", "").upper()  # A, B, or C

    if not quote_id:
        return ToolResult(tool="select_proposal", success=False, error="quote_id required")
    if option not in ("A", "B", "C"):
        return ToolResult(tool="select_proposal", success=False, error="option must be A, B, or C")

    quote_path = os.path.join(QUOTES_DIR, f"{quote_id}.json")
    if not os.path.exists(quote_path):
        return ToolResult(tool="select_proposal", success=False, error=f"Quote {quote_id} not found")

    with open(quote_path) as f:
        quote = json.load(f)

    proposals = quote.get("design_proposals", [])
    idx = ord(option) - 65  # A=0, B=1, C=2
    if idx >= len(proposals):
        return ToolResult(tool="select_proposal", success=False, error=f"Proposal {option} not found")

    selected = proposals[idx]

    # Update quote with selected proposal's totals
    quote["selected_proposal"] = idx
    quote["line_items"] = selected["line_items"]
    quote["subtotal"] = selected["subtotal"]
    quote["tax_amount"] = selected["tax_amount"]
    quote["total"] = selected["total"]
    quote["deposit"]["deposit_amount"] = round(selected["subtotal"] * 0.50, 2)
    quote["status"] = "draft"  # Upgrade from proposal to draft
    quote["updated_at"] = datetime.utcnow().isoformat()

    with open(quote_path, "w") as f:
        json.dump(quote, f, indent=2)

    # Regenerate PDF with finalized totals
    pdf_path = None
    try:
        _run_async(_generate_pdf_for_quote(quote_id))
        pdf_dir = os.path.expanduser("~/empire-repo/backend/data/quotes/pdf")
        pdf_file = os.path.join(pdf_dir, f"{quote['quote_number']}.pdf")
        if os.path.exists(pdf_file):
            pdf_path = pdf_file
    except Exception as e:
        logger.warning(f"PDF regen after proposal select failed: {e}")

    return ToolResult(tool="select_proposal", success=True, result={
        "quote_id": quote_id,
        "quote_number": quote["quote_number"],
        "selected_option": option,
        "selected_label": selected["label"],
        "total": selected["total"],
        "status": "draft",
        "pdf_path": pdf_path,
        "caption": f"\u2705 <b>{quote['quote_number']}</b>\nOption {option} selected: {selected['label']}\nTotal: ${selected['total']:,.2f}",
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
    """Check which Empire services are running using systemd + port checks."""
    import socket

    # Systemd services — check via systemctl first
    systemd_services = {
        "backend": {"port": 8000, "systemd": "empire-backend", "description": "FastAPI Backend API"},
        "command_center": {"port": 3005, "systemd": "empire-cc", "description": "Command Center (Next.js)"},
        "openclaw": {"port": 7878, "systemd": "empire-openclaw", "description": "OpenClaw AI Server"},
    }
    # Port-only services
    port_services = {
        "ollama": {"port": 11434, "description": "Ollama LLM Server"},
        "recoveryforge": {"port": 3077, "description": "RecoveryForge"},
        "relistapp": {"port": 3007, "description": "RelistApp"},
    }

    results = {}

    # Backend is always online if this code is executing
    results["backend"] = {"status": "online", "port": 8000, "description": "FastAPI Backend API", "type": "systemd"}

    # Other systemd services
    for name, svc in systemd_services.items():
        if name == "backend":
            continue
        try:
            import subprocess as _sp
            r = _sp.run(["systemctl", "is-active", svc["systemd"]], capture_output=True, text=True, timeout=5)
            is_active = r.stdout.strip() == "active"
            results[name] = {"status": "online" if is_active else "offline", "port": svc["port"], "description": svc["description"], "type": "systemd"}
        except Exception:
            # Fallback to port check
            try:
                with socket.create_connection(("127.0.0.1", svc["port"]), timeout=2):
                    results[name] = {"status": "online", "port": svc["port"], "description": svc["description"], "type": "port"}
            except Exception:
                results[name] = {"status": "offline", "port": svc["port"], "description": svc["description"]}

    # Port-only services
    for name, svc in port_services.items():
        try:
            with socket.create_connection(("127.0.0.1", svc["port"]), timeout=2):
                results[name] = {"status": "online", "port": svc["port"], "description": svc["description"], "type": "port"}
        except Exception:
            results[name] = {"status": "offline", "port": svc["port"], "description": svc["description"]}

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
    pdf_dir = os.path.expanduser("~/empire-repo/backend/data/quotes/pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"{quote_number}.pdf")

    try:
        _run_async(_generate_pdf_for_quote(quote["id"]))
        if not os.path.exists(pdf_path):
            return ToolResult(tool="send_quote_telegram", success=False, error="PDF generation failed")
    except Exception as e:
        return ToolResult(tool="send_quote_telegram", success=False, error=f"PDF generation failed: {e}")

    caption = (
        f"\U0001f4cb <b>Estimate {quote_number}</b>\n"
        f"\U0001f464 {customer}\n"
        f"\U0001f4b0 Total: ${total:,.2f}"
    )

    # Send directly to Telegram
    try:
        from app.services.max.telegram_bot import telegram_bot
        if telegram_bot.is_configured:
            _run_async(telegram_bot.send_document(pdf_path, caption=caption))
    except Exception as tg_err:
        logger.warning(f"Telegram document send failed: {tg_err}")

    return ToolResult(tool="send_quote_telegram", success=True, result={
        "quote_number": quote_number, "customer": customer, "total": total,
        "pdf_path": pdf_path,
        "caption": caption,
    })


async def _generate_pdf_for_quote(quote_id: str):
    """Generate PDF for a quote by ID (reuses quotes router logic).

    AI-generated quotes (source=max_quick_quote) skip verification
    since they use a different data structure than QIS quotes.
    """
    from app.routers.quotes import generate_pdf as _gen_pdf_endpoint, _load_quote
    quote = _load_quote(quote_id)
    skip = quote.get("source", "").startswith("max_")
    await _gen_pdf_endpoint(quote_id, skip_verification=skip)


# ── EMAIL TOOLS ───────────────────────────────────────────────────

@tool("check_email")
def _check_email(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Check Gmail inbox via OAuth2. Read-only — no delete, no move."""
    limit = min(int(params.get("limit", 10)), 20)
    unread_only = params.get("unread_only", True)
    filter_to = params.get("filter_to", None)

    try:
        from app.services.max.gmail_reader import check_inbox
        result = check_inbox(limit=limit, unread_only=unread_only, filter_to=filter_to)
        if not result.get("success"):
            return ToolResult(tool="check_email", success=False, error=result.get("error", "Gmail check failed"))
        return ToolResult(tool="check_email", success=True, result=result)
    except Exception as e:
        return ToolResult(tool="check_email", success=False, error=str(e))


@tool("send_email")
def _send_email(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Send an email with optional file attachments."""
    to = params.get("to", "").strip()
    subject = params.get("subject", "").strip()
    body = params.get("body", "").strip()

    # Resolve founder aliases to FOUNDER_EMAIL from .env
    if not to or to.lower() in ("me", "owner", "founder", "my email", "myself"):
        to = os.getenv("FOUNDER_EMAIL", "empirebox2026@gmail.com")

    if not subject or not body:
        return ToolResult(tool="send_email", success=False, error="subject and body are required")

    attachments = params.get("attachments", [])
    cc = params.get("cc")

    # Auto-convert SVG attachments to PDF via WeasyPrint
    converted_attachments = []
    for att in attachments:
        att_path = Path(att) if isinstance(att, str) else None
        if att_path and att_path.suffix.lower() == ".svg" and att_path.exists():
            try:
                pdf_out = att_path.with_suffix(".pdf")
                svg_content = att_path.read_text()
                html_wrap = f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>@page{{size:letter;margin:0.5in}}body{{margin:0}}</style></head><body>{svg_content}</body></html>'
                from weasyprint import HTML as WeasyHTML
                WeasyHTML(string=html_wrap).write_pdf(str(pdf_out))
                converted_attachments.append(str(pdf_out))
                logger.info(f"Auto-converted SVG to PDF: {att} -> {pdf_out}")
            except Exception as e:
                logger.warning(f"SVG to PDF conversion failed for {att}: {e}, attaching original")
                converted_attachments.append(att)
        else:
            converted_attachments.append(att)

    try:
        from app.services.max.email_service import EmailService
        svc = EmailService()
        if not svc.is_configured:
            return ToolResult(tool="send_email", success=False, error="Email not configured — set SENDGRID_API_KEY or SMTP_USER/SMTP_PASSWORD in .env")
        logger.info(f"send_email: to={to}, subject={subject}, attachments={converted_attachments}")
        svc.send(to=to, subject=subject, body_html=body, attachments=converted_attachments, cc=cc)
        return ToolResult(tool="send_email", success=True, result={
            "sent_to": to, "subject": subject,
            "attachments_sent": len(converted_attachments),
            "attachment_files": [os.path.basename(a) for a in converted_attachments],
        })
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
    pdf_dir = os.path.expanduser("~/empire-repo/backend/data/quotes/pdf")
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


# ── SVG TO PDF TOOL ──────────────────────────────────────────────

@tool("svg_to_pdf")
def _svg_to_pdf(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Convert SVG content or file to PDF using WeasyPrint. Returns the PDF path."""
    svg_content = params.get("svg_content", "")
    svg_path = params.get("svg_path", "")
    output_path = params.get("output_path", "")

    if not svg_content and not svg_path:
        return ToolResult(tool="svg_to_pdf", success=False, error="Provide svg_content (raw SVG string) or svg_path (file path)")

    try:
        # Read SVG from file if path provided
        if svg_path and not svg_content:
            p = Path(svg_path)
            if not p.exists():
                return ToolResult(tool="svg_to_pdf", success=False, error=f"SVG file not found: {svg_path}")
            svg_content = p.read_text()

        # Default output path
        if not output_path:
            output_dir = os.path.expanduser("~/empire-repo/uploads")
            os.makedirs(output_dir, exist_ok=True)
            import uuid
            output_path = os.path.join(output_dir, f"drawing_{uuid.uuid4().hex[:8]}.pdf")

        # Wrap SVG in HTML and render via WeasyPrint
        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page {{ size: letter; margin: 0; }}
  body {{ margin: 0; padding: 0; display: flex; align-items: center; justify-content: center; min-height: 100vh; background: white; }}
  svg {{ max-width: 100%; max-height: 100vh; }}
</style></head>
<body>{svg_content}</body></html>"""

        from weasyprint import HTML as WeasyHTML
        WeasyHTML(string=html_content).write_pdf(output_path)

        size = os.path.getsize(output_path)
        logger.info(f"SVG to PDF: {output_path} ({size} bytes)")
        return ToolResult(tool="svg_to_pdf", success=True, result={
            "pdf_path": output_path,
            "size_bytes": size,
        })
    except Exception as e:
        logger.error(f"SVG to PDF failed: {e}")
        return ToolResult(tool="svg_to_pdf", success=False, error=str(e))


# ── SKETCH TO DRAWING TOOL ────────────────────────────────────────

def _auto_email_pdf(pdf_path: str, email_to: str, drawing_name: str) -> dict | None:
    """Auto-email a PDF drawing. Returns email info dict or None on failure."""
    try:
        from app.services.max.email_service import EmailService
        svc = EmailService()
        if not svc.is_configured:
            logger.warning("Auto-email: email not configured")
            return {"emailed": False, "error": "Email not configured"}
        subject = f"Drawing: {drawing_name}"
        body = f"""<h2>Professional Drawing</h2>
<p>Please find attached the drawing for <strong>{drawing_name}</strong>.</p>
<p style="color:#888;font-size:12px">Generated by MAX — Empire AI</p>"""
        svc.send(to=email_to, subject=subject, body_html=body, attachments=[pdf_path])
        logger.info(f"Auto-emailed drawing PDF to {email_to}: {pdf_path}")
        return {"emailed": True, "sent_to": email_to}
    except Exception as e:
        logger.error(f"Auto-email failed: {e}")
        return {"emailed": False, "error": str(e)}


@tool("sketch_to_drawing")
def _sketch_to_drawing(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Generate professional architectural drawings (PDF) for any item type.

    Auto-classifies input to determine what to draw: bench, window treatment,
    pillow, upholstery, table, or generic measurement diagram.

    Accepts either:
    - quote_id: generate drawings for all areas in a quote
    - shape + lf + name: generate a single bench drawing (bench items only)
    - name + description + dimensions: generate a measurement diagram for any item type
    - item_type: override auto-classification (bench, window, pillow, upholstery, table, generic)
    """
    try:
        from app.services.vision.drawing_service import classify_input, render_measurement_diagram
        from app.services.vision.bench_renderer import (
            render_straight, render_l_shape, render_u_shape,
            render_quote_drawings, drawings_to_pdf,
        )

        quote_id = params.get("quote_id", "")
        output_path = params.get("output_path", "")
        name = params.get("name", "Drawing")
        description = params.get("description", "")

        # Auto-email: if email_to is provided, send the PDF after generating
        email_to = params.get("email_to", "").strip()
        if email_to and email_to.lower() in ("me", "owner", "founder", "my email", "myself"):
            email_to = os.getenv("FOUNDER_EMAIL", "empirebox2026@gmail.com")

        # ── Smart classifier (10 item types) ──
        from app.services.vision.drawing_service import classify_item
        explicit_type = params.get("item_type", "")
        if explicit_type:
            classification = classify_item(user_text=explicit_type, item_name=name)
            item_type = classification["type"]
            # If explicit type didn't match any category, use it directly
            if item_type == "generic" and explicit_type not in ("generic", ""):
                item_type = explicit_type.lower()
        else:
            classify_text = f"{name} {description} {params.get('shape', '')}"
            classification = classify_item(user_text=classify_text, item_name=name,
                                           description=description)
            item_type = classification["type"]
        logger.info(f"sketch_to_drawing: classified as '{item_type}' (confidence={classification.get('confidence','?')}) from input")

        if quote_id:
            # Generate from quote data — quotes are always bench/seating
            quote_path = os.path.join(QUOTES_DIR, f"{quote_id}.json")
            if not os.path.exists(quote_path):
                return ToolResult(tool="sketch_to_drawing", success=False, error=f"Quote {quote_id} not found")

            import json as _json
            with open(quote_path) as f:
                quote = _json.load(f)

            quote_num = quote.get("quote_number", quote_id)
            line_items = quote.get("line_items", [])
            if not line_items:
                return ToolResult(tool="sketch_to_drawing", success=False, error="Quote has no line items")

            drawings = render_quote_drawings(line_items, quote_num)
            if not output_path:
                out_dir = os.path.expanduser("~/empire-repo/uploads/arch_drawings")
                os.makedirs(out_dir, exist_ok=True)
                output_path = os.path.join(out_dir, f"{quote_num}_drawings.pdf")

            drawings_to_pdf(drawings, output_path)
            size = os.path.getsize(output_path)
            result = {
                "pdf_path": output_path,
                "pages": len(drawings),
                "size_bytes": size,
                "item_type": "bench",
                "areas": [d["name"] for d in drawings],
            }
            if email_to:
                result["email"] = _auto_email_pdf(output_path, email_to, name)
            return ToolResult(tool="sketch_to_drawing", success=True, result=result)

        # ── Bench items → professional 4-quadrant renderer (bench_renderer.py) ──
        if item_type == "bench":
            shape = params.get("shape", "straight").lower()
            lf = float(params.get("lf", params.get("length_ft", 10)))
            if not name or name == "Drawing":
                name = f"{shape.title()} Bench"

            width_in = lf * 12
            # Parse optional dimensions
            seat_depth = float(params.get("seat_depth", params.get("depth", 18)))
            seat_height = float(params.get("seat_height", 18))
            back_height = float(params.get("back_height", 34))
            if params.get("dimensions"):
                for k, v in params["dimensions"].items():
                    try:
                        val = float(str(v).replace('"', '').replace("'", '').strip())
                        if "depth" in k.lower() or "seat_d" in k.lower():
                            seat_depth = val
                        elif "seat_h" in k.lower():
                            seat_height = val
                        elif "back" in k.lower():
                            back_height = val
                        elif "width" in k.lower() or "length" in k.lower():
                            width_in = val
                    except (ValueError, TypeError):
                        pass

            # Always use bench_renderer.py — produces 4-quadrant professional layout
            # (Plan View + Isometric + Front Elevation + Title Block, 1200x850)
            from app.services.vision.bench_renderer import (
                render_straight, render_l_shape, render_u_shape,
            )
            quote_num = params.get("quote_num", "")
            cushion_width = float(params.get("cushion_width", 24))
            panel_style = params.get("panel_style", "vertical_channels")
            channel_count = int(params.get("channel_count", 6))
            client = params.get("client", "")
            project = params.get("project", "")

            style_kw = dict(cushion_width=cushion_width, panel_style=panel_style,
                            channel_count=channel_count, client=client, project=project)

            if "u" in shape:
                mult = int(params.get("multiplier", 1))
                svg = render_u_shape(name, width_in, depth_in=seat_depth,
                                     seat_h_in=seat_height, back_h_in=back_height,
                                     multiplier=mult, quote_num=quote_num, **style_kw)
            elif "l" in shape:
                svg = render_l_shape(name, width_in, depth_in=seat_depth,
                                     seat_h_in=seat_height, back_h_in=back_height,
                                     quote_num=quote_num, **style_kw)
            else:
                svg = render_straight(name, width_in, depth_in=seat_depth,
                                      seat_h_in=seat_height, back_h_in=back_height,
                                      quote_num=quote_num, **style_kw)
            logger.info(f"sketch_to_drawing: bench '{shape}' rendered via bench_renderer.py (4-quadrant, 1200x850)")

            if not output_path:
                out_dir = os.path.expanduser("~/empire-repo/uploads/arch_drawings")
                os.makedirs(out_dir, exist_ok=True)
                import uuid as _uuid
                output_path = os.path.join(out_dir, f"drawing_{_uuid.uuid4().hex[:8]}.pdf")

            drawings_to_pdf([{"name": name, "svg": svg, "lf": lf}], output_path)
            size = os.path.getsize(output_path)

            # Save SVG file next to PDF for inline display
            svg_path = output_path.replace('.pdf', '.svg')
            with open(svg_path, 'w') as f:
                f.write(svg)

            from app.services.vision.renderer_registry import get_business_unit
            filename = os.path.basename(output_path)
            svg_filename = filename.replace('.pdf', '.svg')
            result = {
                "pdf_path": output_path,
                "pages": 1,
                "size_bytes": size,
                "item_type": "bench",
                "svg": svg,
                "svg_url": f'/api/v1/drawings/files/{svg_filename}',
                "pdf_url": f'/api/v1/drawings/files/{filename}',
                "canvas_mode": "drawing",
                "item_name": name,
                "business_unit": get_business_unit("bench"),
            }
            if email_to:
                result["email"] = _auto_email_pdf(output_path, email_to, name)
            return ToolResult(tool="sketch_to_drawing", success=True, result=result)

        # ── All other item types → type-specific renderer ──
        dimensions = params.get("dimensions", {})
        if not dimensions:
            for key in ("width", "height", "depth", "drop", "length", "diameter"):
                val = params.get(key)
                if val:
                    dimensions[key.title()] = f'{val}"'

        notes = params.get("notes", description)
        render_params = {"name": name, "dimensions": dimensions, "notes": notes}
        # Pass through raw dimension values for renderers that use them
        for k in ("width", "height", "depth", "drop", "seat_height", "treatment_type", "mount_type"):
            if params.get(k):
                render_params[k] = params[k]

        svg = render_measurement_diagram(
            name=name,
            item_type=item_type,
            dimensions=dimensions,
            notes=notes,
        )

        if not output_path:
            out_dir = os.path.expanduser("~/empire-repo/uploads/arch_drawings")
            os.makedirs(out_dir, exist_ok=True)
            import uuid as _uuid
            output_path = os.path.join(out_dir, f"drawing_{_uuid.uuid4().hex[:8]}.pdf")

        drawings_to_pdf([{"name": name, "svg": svg, "lf": 0}], output_path)
        size = os.path.getsize(output_path)

        # Save SVG file next to PDF for inline display
        svg_path = output_path.replace('.pdf', '.svg')
        with open(svg_path, 'w') as f:
            f.write(svg)

        from app.services.vision.renderer_registry import get_business_unit
        filename = os.path.basename(output_path)
        svg_filename = filename.replace('.pdf', '.svg')
        result = {
            "pdf_path": output_path,
            "pages": 1,
            "size_bytes": size,
            "item_type": item_type,
            "svg": svg,
            "svg_url": f'/api/v1/drawings/files/{svg_filename}',
            "pdf_url": f'/api/v1/drawings/files/{filename}',
            "canvas_mode": "drawing",
            "item_name": name,
            "business_unit": get_business_unit(item_type),
        }
        if email_to:
            result["email"] = _auto_email_pdf(output_path, email_to, name)
        return ToolResult(tool="sketch_to_drawing", success=True, result=result)

    except Exception as e:
        logger.error(f"sketch_to_drawing failed: {e}")
        return ToolResult(tool="sketch_to_drawing", success=False, error=str(e))


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

def _parse_ddg_results(html: str, max_results: int) -> list:
    """Parse DuckDuckGo HTML search results into structured data."""
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


def _brave_search(query: str, num_results: int = 5) -> list[dict]:
    """Search via Brave Search API (free tier: 2000 queries/month)."""
    brave_key = os.getenv("BRAVE_API_KEY", "")
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


@tool("web_search")
def _web_search(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Search the web via DuckDuckGo HTML with Brave Search API fallback."""
    query = params.get("query", "").strip()
    logger.info(f"[web_search] called with query='{query}'")
    if not query:
        return ToolResult(tool="web_search", success=False, error="Query is required")

    num_results = min(int(params.get("num_results", 5)), 10)
    source = "DuckDuckGo"
    results = []

    # Primary: DDG HTML endpoint (same method that worked on Beelink)
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            },
            timeout=10,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            results = _parse_ddg_results(resp.text, num_results)
    except Exception as e:
        logger.warning(f"[web_search] DDG HTML failed: {e}")

    # Fallback: Brave Search API
    if not results:
        try:
            logger.info(f"[web_search] DDG returned 0, falling back to Brave Search")
            results = _brave_search(query, num_results)
            if results:
                source = "Brave"
        except Exception as e:
            logger.warning(f"[web_search] Brave also failed: {type(e).__name__}: {e}")

    logger.info(f"[web_search] query='{query}' returned {len(results)} results via {source}")
    return ToolResult(tool="web_search", success=True, result={
        "query": query, "results": results, "count": len(results), "source": source,
    })


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
    """Extract readable text from HTML, preserving heading structure."""
    import html as html_mod
    # Remove script/style/noscript blocks
    text = re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove nav/header/footer (boilerplate)
    text = re.sub(r'<(nav|header|footer|aside)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Preserve headings as markdown-style markers (helps AI understand page structure)
    text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n### \1\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<h[3-6][^>]*>(.*?)</h[3-6]>', r'\n# \1\n', text, flags=re.DOTALL | re.IGNORECASE)
    # Convert common elements to readable text
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</(p|div|li|tr)>', '\n', text)
    text = re.sub(r'<li[^>]*>', '- ', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Decode HTML entities
    text = html_mod.unescape(text)
    return text.strip()


# ── PHOTO-TO-QUOTE PIPELINE TOOL ──────────────────────────────────

@tool("photo_to_quote")
def _photo_to_quote(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Create a quote from photo analysis and send the PDF via Telegram in one step.

    When QIS is available and an image is provided, uses the full QIS pipeline:
    1. analyze_photo_items() — AI vision extracts structured items from photo
    2. assemble_quote() — real pricing engine with 3-tier pricing
    3. generate_all_item_mockups() — per-item AI mockups (optional)
    Falls back to create_quick_quote legacy path if QIS fails.
    """
    image_data = params.get("image_data") or params.get("image_b64")
    customer_name = params.get("customer_name", "Customer 1") or "Customer 1"
    customer_notes = params.get("customer_notes", params.get("max_analysis", ""))
    qis_used = False

    # ── Try full QIS pipeline if we have a photo and QIS is available ──
    if QIS_AVAILABLE and image_data:
        try:
            # Step 1: AI vision analysis — extract structured items from photo
            logger.info("QIS photo_to_quote: analyzing photo for %s", customer_name)
            analysis = qis_analyze_photo(image_data, customer_notes)
            qis_items = analysis.get("items", [])

            if qis_items:
                # Step 2: Assemble quote with real pricing engine
                location = params.get("location", "DC")
                lining = params.get("lining", "standard")
                qis_quote = qis_assemble_quote(
                    analyzed_items=qis_items,
                    customer_name=customer_name,
                    location=location,
                    lining=lining,
                )
                # Save to disk (assemble_quote no longer auto-saves)
                import os, json as _json
                _qdir = os.path.expanduser("~/empire-repo/backend/data/quotes")
                os.makedirs(_qdir, exist_ok=True)
                with open(os.path.join(_qdir, f"{qis_quote['id']}.json"), "w") as _qf:
                    _json.dump(qis_quote, _qf, indent=2, default=str)
                qis_tiers = qis_quote.get("tiers", {})

                if qis_tiers:
                    # Step 3: Generate per-item mockups (best-effort, non-blocking)
                    mockup_results = {}
                    try:
                        mockup_results = _run_async(qis_generate_mockups(
                            items=qis_items,
                            original_photo_b64=image_data,
                            fabric_grade="B",
                            fabric_color=params.get("fabric_color", ""),
                            style=analysis.get("style", params.get("style", "")),
                        ))
                        logger.info("QIS generated %d item mockups", len(mockup_results))
                    except Exception as mockup_err:
                        logger.warning("QIS mockup generation failed (non-fatal): %s", mockup_err)

                    # Convert QIS tiers to design_proposals format
                    design_proposals = _qis_tiers_to_design_proposals(qis_tiers, params.get("rooms", []))

                    # Build the quote in the standard MAX format for compatibility
                    quote_id = qis_quote.get("id", str(uuid.uuid4())[:8])
                    quote_number = qis_quote.get("quote_number", _next_quote_number(customer_name))
                    now = datetime.utcnow().isoformat()
                    expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()

                    # Build rooms from analysis if not provided
                    rooms = params.get("rooms", [])
                    if not rooms:
                        rooms = [{
                            "name": analysis.get("room_type", "Room").replace("_", " ").title(),
                            "windows": [],
                            "upholstery": [],
                        }]

                    # Build line items from mid-tier (B) for default display
                    mid_tier = design_proposals[1] if len(design_proposals) > 1 else design_proposals[0]
                    line_items = mid_tier.get("line_items", [])

                    quote_data = {
                        "id": quote_id,
                        "quote_number": quote_number,
                        "customer_name": customer_name,
                        "customer_email": params.get("customer_email", ""),
                        "customer_phone": params.get("customer_phone", ""),
                        "customer_address": params.get("customer_address", ""),
                        "project_name": params.get("project_name", f"Photo Quote for {customer_name}"),
                        "rooms": rooms,
                        "line_items": line_items,
                        "design_proposals": design_proposals,
                        "selected_proposal": None,
                        "photos": [],
                        "ai_outlines": [],
                        "ai_mockups": [],
                        "subtotal": 0.0,
                        "tax_rate": DC_TAX_RATE,
                        "tax_amount": 0.0,
                        "total": 0.0,
                        "proposal_totals": {
                            "A": design_proposals[0]["total"] if len(design_proposals) > 0 else 0,
                            "B": design_proposals[1]["total"] if len(design_proposals) > 1 else 0,
                            "C": design_proposals[2]["total"] if len(design_proposals) > 2 else 0,
                        },
                        "deposit": {"deposit_percent": 50, "deposit_amount": 0},
                        "status": "proposal",
                        "scope": params.get("scope", "full"),
                        "style": analysis.get("style", params.get("style", "")),
                        "max_analysis": customer_notes,
                        "pricing_engine": "qis",
                        "qis_quote_id": qis_quote.get("id"),
                        "qis_quote_number": qis_quote.get("quote_number"),
                        "qis_analysis": {
                            "room_type": analysis.get("room_type"),
                            "style": analysis.get("style"),
                            "items_detected": len(qis_items),
                            "overall_notes": analysis.get("overall_notes"),
                            "questions": analysis.get("questions", []),
                        },
                        "created_at": now,
                        "updated_at": now,
                        "expires_at": expires_at,
                        "source": "max_photo_to_quote_qis",
                        "terms": "50% deposit required to begin fabrication. Balance due upon installation. All sales final once fabric is cut. Estimate valid for 30 days.",
                        "valid_days": 30,
                        "business_name": "Empire",
                    }

                    # Save JSON
                    os.makedirs(QUOTES_DIR, exist_ok=True)
                    quote_path = os.path.join(QUOTES_DIR, f"{quote_id}.json")
                    with open(quote_path, "w") as f:
                        json.dump(quote_data, f, indent=2, default=str)

                    # Generate PDF
                    pdf_url = None
                    try:
                        _run_async(_generate_pdf_for_quote(quote_id))
                        pdf_dir = os.path.expanduser("~/empire-repo/backend/data/quotes/pdf")
                        pdf_file = os.path.join(pdf_dir, f"{quote_number}.pdf")
                        if os.path.exists(pdf_file):
                            pdf_url = f"/api/v1/quotes/{quote_id}/pdf"
                    except Exception as pdf_err:
                        logger.warning("QIS photo_to_quote PDF generation failed: %s", pdf_err)

                    # Send via Telegram
                    send_result = _send_quote_telegram({"quote_id": quote_id}, desk)

                    # Build caption
                    proposal_summary = ""
                    for i, dp in enumerate(design_proposals[:3]):
                        letter = chr(65 + i)
                        proposal_summary += f"\n  {letter}. {dp['label']}: ${dp['total']:,.2f}"

                    caption = (
                        f"\U0001f4cb <b>{quote_number}</b> (QIS)\n"
                        f"\U0001f464 {customer_name}\n"
                        f"\U0001f50d {len(qis_items)} items detected from photo\n"
                        f"\U0001f4b0 3 Design Options:{proposal_summary}\n"
                        f"\n\u2139\ufe0f Total: $0 — select an option to finalize"
                    )

                    qis_used = True
                    logger.info("QIS photo_to_quote complete: %s — %d items, 3 tiers", quote_number, len(qis_items))

                    return ToolResult(tool="photo_to_quote", success=True, result={
                        "quote_id": quote_id,
                        "quote_number": quote_number,
                        "customer_name": customer_name,
                        "total": 0,
                        "proposal_totals": quote_data["proposal_totals"],
                        "items_count": len(qis_items),
                        "items_detected": len(qis_items),
                        "pricing_engine": "qis",
                        "mockups_generated": len(mockup_results),
                        "room_type": analysis.get("room_type"),
                        "style": analysis.get("style"),
                        "questions": analysis.get("questions", []),
                        "telegram_sent": send_result.success,
                        "telegram_error": send_result.error if not send_result.success else None,
                        "pdf_url": pdf_url,
                        "pdf_path": send_result.result.get("pdf_path") if send_result.result else None,
                        "caption": caption,
                        "design_proposals_count": len(design_proposals),
                    })

        except Exception as qis_err:
            logger.warning("QIS photo_to_quote pipeline failed, falling back to legacy: %s", qis_err)

    # ── Fallback: legacy create_quick_quote path ──
    if not qis_used:
        quote_result = _create_quick_quote(params, desk)
        if not quote_result.success:
            return ToolResult(tool="photo_to_quote", success=False,
                             error=f"Quote creation failed: {quote_result.error}")

        quote_id = quote_result.result.get("quote_id", "")
        quote_number = quote_result.result.get("quote_number", "")

        # Send via Telegram
        send_result = _send_quote_telegram({"quote_id": quote_id}, desk)

        return ToolResult(tool="photo_to_quote", success=True, result={
            "quote_id": quote_id,
            "quote_number": quote_number,
            "customer_name": quote_result.result.get("customer_name"),
            "total": quote_result.result.get("total"),
            "items_count": quote_result.result.get("items_count"),
            "pricing_engine": "legacy",
            "telegram_sent": send_result.success,
            "telegram_error": send_result.error if not send_result.success else None,
            "pdf_path": send_result.result.get("pdf_path") if send_result.result else None,
            "caption": send_result.result.get("caption") if send_result.result else None,
        })


# ── DESK DELEGATION TOOL ───────────────────────────────────────────

@tool("run_desk_task")
def _run_desk_task(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Submit a task to the AI desk system for autonomous handling.

    Calls desk_manager directly (no HTTP loopback) to avoid deadlocking
    when called from within the same uvicorn process.
    """
    title = params.get("title", "").strip()
    if not title:
        return ToolResult(tool="run_desk_task", success=False, error="Task title is required")

    # Check if caller wants async (non-blocking) mode
    async_mode = params.get("async", False)

    try:
        import asyncio
        import concurrent.futures

        async def _submit():
            from app.services.max.desks.desk_manager import desk_manager
            desk_manager.initialize()
            task = await desk_manager.submit_task(
                title=title,
                description=params.get("description", title),
                priority=params.get("priority", "normal"),
                source="max_tool",
            )
            return {
                "id": task.id,
                "title": task.title,
                "state": task.state.value if hasattr(task.state, "value") else str(task.state),
                "result": task.result,
                "desk": getattr(task, "desk_id", None) or "auto",
            }

        if async_mode:
            # Async mode: submit to background, return immediately
            task_id = uuid.uuid4().hex[:8]
            _log_async_task(task_id, title, "delegated")
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_run_atlas_background(task_id, title, params))
            except RuntimeError:
                # No running loop — fall through to sync
                pass
            return ToolResult(tool="run_desk_task", success=True, result={
                "task_id": task_id,
                "title": title,
                "status": "delegated",
                "message": f"Task #{task_id} delegated to Atlas. Working in background. I'll notify you when it's done.",
            })

        # Sync mode: block until complete (original behavior)
        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                data = pool.submit(asyncio.run, _submit()).result(timeout=90)
        except RuntimeError:
            data = asyncio.run(_submit())

        if data.get("state") == "completed":
            return ToolResult(tool="run_desk_task", success=True, result=data)
        else:
            # Desk task didn't complete — also queue for OpenClaw as backup
            try:
                import httpx as _q_httpx
                _q_httpx.post(
                    "http://localhost:8000/api/v1/openclaw/tasks",
                    json={
                        "title": title,
                        "description": params.get("description", title),
                        "desk": data.get("desk", "general"),
                        "priority": {"urgent": 1, "high": 3, "normal": 5, "low": 7}.get(
                            params.get("priority", "normal"), 5
                        ),
                        "source": "desk_fallback",
                    },
                    timeout=5,
                )
                data["openclaw_queued"] = True
            except Exception:
                data["openclaw_queued"] = False
            return ToolResult(tool="run_desk_task", success=False,
                            result=data, error=data.get("result", "Task did not complete — queued for OpenClaw"))
    except Exception as e:
        return ToolResult(tool="run_desk_task", success=False, error=f"Desk task failed: {e}")


async def _run_atlas_background(task_id: str, title: str, params: dict):
    """Background: Atlas executes task, updates status, notifies founder."""
    try:
        from app.services.max.desks.desk_manager import desk_manager
        desk_manager.initialize()
        task = await desk_manager.submit_task(
            title=title,
            description=params.get("description", title),
            priority=params.get("priority", "normal"),
            source="atlas_async",
        )
        state = task.state.value if hasattr(task.state, "value") else str(task.state)
        _log_async_task(task_id, title, state, result=task.result)

        # Notify founder on completion/failure
        _notify = f"Atlas task #{task_id} {state}: {title}"
        if task.result:
            _notify += f"\n{str(task.result)[:200]}"
        try:
            from app.services.max.telegram_bot import telegram_bot
            if telegram_bot and telegram_bot.is_configured:
                import asyncio
                await telegram_bot.send_message(_notify)
        except Exception:
            pass
        logger.info(f"Atlas background task #{task_id} {state}: {title}")
    except Exception as e:
        _log_async_task(task_id, title, "failed", error=str(e))
        logger.error(f"Atlas background task #{task_id} failed: {e}")
        try:
            from app.services.max.telegram_bot import telegram_bot
            if telegram_bot and telegram_bot.is_configured:
                await telegram_bot.send_message(f"Atlas task #{task_id} FAILED: {str(e)[:150]}")
        except Exception:
            pass


def _log_async_task(task_id: str, title: str, status: str, result=None, error=None):
    """Log async task status to DB."""
    try:
        import sqlite3
        db_path = os.path.expanduser("~/empire-repo/backend/data/empire.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS atlas_tasks (
                id TEXT PRIMARY KEY,
                title TEXT,
                status TEXT,
                result TEXT,
                error TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute(
            "INSERT OR REPLACE INTO atlas_tasks (id, title, status, result, error, updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (task_id, title, status, str(result)[:2000] if result else None, error)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"Atlas task log failed: {e}")


@tool("delegate_to_atlas")
def _delegate_to_atlas(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Delegate a code task to Atlas (Opus). Returns IMMEDIATELY.
    Atlas runs in background. MAX is free for the next question.
    """
    title = params.get("title", params.get("task", "")).strip()
    if not title:
        return ToolResult(tool="delegate_to_atlas", success=False, error="Task title/description is required")

    # Use run_desk_task in async mode
    return _run_desk_task({
        "title": title,
        "description": params.get("description", title),
        "priority": params.get("priority", "normal"),
        "async": True,
    }, desk=desk)


# ── PRESENTATION PDF + TELEGRAM TOOL ──────────────────────────────

PRESENTATIONS_DIR = os.path.expanduser("~/empire-repo/backend/data/presentations")


def _md_to_html(text: str) -> str:
    """Convert basic markdown to HTML: **bold**, *italic*, - bullets, newlines."""
    import re as _re
    text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = _re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = text.replace("\n", "<br>")
    return text


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
        content = _md_to_html(section.get("content", ""))
        stype = section.get("type", "text")

        if stype == "highlight":
            sections_html += f"""<div style="margin:16px 0;padding:16px 20px;background:linear-gradient(135deg,#fffcf0,#f8f5ff);
                border-left:4px solid #D4AF37;border-radius:0 8px 8px 0">
                <h2 style="color:#D4AF37;margin:0 0 8px;font-size:1.05em">{heading}</h2>
                <div style="font-size:0.88em;color:#333;line-height:1.6">{content}</div></div>"""
        elif stype == "bullets":
            # Convert - items to HTML list with markdown
            items = [_md_to_html(line.strip().lstrip("- ")) for line in section.get("content", "").split("\n") if line.strip()]
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

    # Return pdf_path — the Telegram handler detects it and sends via send_document.
    # We do NOT send directly here to avoid sync/async issues and duplicate delivery.
    section_count = len(data.get("sections", []))
    caption = (
        f"\U0001f4ca <b>{data.get('title', topic)}</b>\n"
        f"\U0001f4dd {section_count} sections &middot; {data.get('model_used', 'AI')}\n"
        f"\U0001f4c5 {datetime.utcnow().strftime('%b %d, %Y')}"
    )

    return ToolResult(tool="present", success=True, result={
        "title": data.get("title", topic),
        "subtitle": data.get("subtitle", ""),
        "sections": section_count,
        "charts": len(data.get("charts", [])),
        "sources": len(data.get("sources", [])),
        "model_used": data.get("model_used", "unknown"),
        "pdf_path": pdf_path,
        "caption": caption,
    })


# ── SHELL EXECUTE (safe, allowlisted) ─────────────────────────────

# Level 1 — auto-execute (read-only + safe operations)
ALLOWED_COMMANDS = [
    # Filesystem read
    "ls", "cat", "head", "tail", "wc", "df", "du", "free",
    "find", "grep", "rg", "tree", "file", "stat",
    # System info
    "ps", "uptime", "date", "whoami", "pwd", "hostname", "id",
    "env", "printenv", "uname", "lsb_release", "top -bn1", "pgrep",
    # Shell basics
    "echo", "sort", "uniq", "tee", "touch", "mkdir", "cp", "mv",
    "which", "type", "command -v",
    # Programming
    "python3", "node -e", "sqlite3", "pytest", "python3 scripts/",
    # Git
    "git status", "git log", "git diff", "git branch", "git show",
    "git add", "git commit", "git push", "git pull", "git stash",
    "git checkout", "git merge", "git fetch", "git remote", "git tag",
    # Network
    "curl", "wget", "dig", "ping", "ss", "netstat",
    # Package managers
    "pip", "pip3", "npm", "npx", "npm run",
    # Service management
    "sudo systemctl", "systemctl status", "systemctl restart",
    "systemctl is-active", "systemctl start", "systemctl stop",
    "journalctl",
    # Tools
    "ollama list", "ollama ps", "ollama run",
    "docker ps", "docker images", "docker logs",
    "chmod 600",
]

# Hard-blocked — NEVER allow, even for founder
BLOCKED_PATTERNS = [
    "rm -rf /", "rm -r /", "rm -rf ~", "rm -r ~",
    "pkill -9", "kill -9", "killall",
    "dd if=", "mkfs", "fdisk", "shutdown", "reboot", "init 0",
    "sudo rm -rf", "chmod 777", "chown root",
    "> /dev/sda", ":(){ :|:& };:",
    "sensors-detect",  # CRITICAL: crashes EmpireDell
]


@tool("shell_execute")
def _shell_execute(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Execute a shell command. Founder channels bypass allowlist.
    Blocked patterns (rm -rf, sensors-detect, etc.) always enforced for safety.
    """
    import subprocess

    command = params.get("command", "").strip()
    if not command:
        return ToolResult(tool="shell_execute", success=False, error="No command provided")

    # Safety checks — block dangerous patterns (always enforced, even for founder)
    for blocked in BLOCKED_PATTERNS:
        if blocked in command:
            return ToolResult(
                tool="shell_execute", success=False,
                error=f"Blocked command pattern: {blocked}",
            )

    # Founder bypasses allowlist; non-founder must match allowed prefixes
    founder = params.get("_founder", False)
    if not founder:
        allowed = any(command.startswith(cmd) for cmd in ALLOWED_COMMANDS)
        if not allowed:
            return ToolResult(
                tool="shell_execute", success=False,
                error=f"Command not in allowlist. Allowed: {', '.join(ALLOWED_COMMANDS[:10])}...",
            )

    # Execute with timeout
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=30, cwd=os.path.expanduser("~/empire-repo"),
        )
        return ToolResult(
            tool="shell_execute", success=True,
            result={
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:500],
                "returncode": result.returncode,
            },
        )
    except subprocess.TimeoutExpired:
        return ToolResult(tool="shell_execute", success=False, error="Command timed out (30s limit)")
    except Exception as e:
        return ToolResult(tool="shell_execute", success=False, error=str(e))


# ── OPENCLAW DISPATCH ──────────────────────────────────────────────

@tool("dispatch_to_openclaw")
def _dispatch_to_openclaw(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Send a task to OpenClaw for autonomous execution."""
    import httpx as _httpx

    title = params.get("title", "").strip()
    description = params.get("description", "").strip()
    if not title or not description:
        return ToolResult(tool="dispatch_to_openclaw", success=False, error="Both title and description are required")

    priority = params.get("priority", "normal")
    skills = params.get("skills_needed", [])
    wait = params.get("wait_for_result", True)
    endpoint = "dispatch" if wait else "dispatch-async"

    try:
        resp = _httpx.post(
            f"http://localhost:8000/api/v1/openclaw/{endpoint}",
            json={
                "title": title,
                "description": description,
                "priority": priority,
                "desk": desk,
                "skills_needed": skills,
            },
            timeout=300,
        )
        if resp.status_code == 200:
            data = resp.json()
            return ToolResult(tool="dispatch_to_openclaw", success=True, result=data)
        return ToolResult(tool="dispatch_to_openclaw", success=False, error=f"OpenClaw returned {resp.status_code}: {resp.text[:200]}")
    except _httpx.ConnectError:
        return ToolResult(tool="dispatch_to_openclaw", success=False, error="OpenClaw not running on port 7878")
    except _httpx.ReadTimeout:
        return ToolResult(tool="dispatch_to_openclaw", success=False, error="OpenClaw task timed out")
    except Exception as e:
        return ToolResult(tool="dispatch_to_openclaw", success=False, error=str(e))


# ── QUEUE OPENCLAW TASK ─────────────────────────────────────────────

@tool("queue_openclaw_task")
def _queue_openclaw_task(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Queue a task for autonomous OpenClaw execution (non-blocking).

    Unlike dispatch_to_openclaw which waits for a result, this queues the task
    in the persistent DB and returns immediately. The background worker picks
    it up automatically.
    """
    import httpx as _httpx

    title = params.get("title", "").strip()
    description = params.get("description", "").strip()
    if not title:
        return ToolResult(tool="queue_openclaw_task", success=False, error="Task title is required")
    if not description:
        description = title

    task_desk = params.get("desk", desk or "general")
    priority = params.get("priority", 5)
    if isinstance(priority, str):
        priority = {"critical": 1, "high": 3, "normal": 5, "low": 7}.get(priority, 5)

    try:
        resp = _httpx.post(
            "http://localhost:8000/api/v1/openclaw/tasks",
            json={
                "title": title,
                "description": description,
                "desk": task_desk,
                "priority": priority,
                "source": "max",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return ToolResult(tool="queue_openclaw_task", success=True, result={
                "task_id": data.get("id"),
                "title": title,
                "desk": task_desk,
                "status": "queued",
                "message": f"Task #{data.get('id')} queued for OpenClaw. Worker will pick it up within 30 seconds.",
            })
        return ToolResult(tool="queue_openclaw_task", success=False,
                         error=f"Queue API returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return ToolResult(tool="queue_openclaw_task", success=False, error=str(e))


# ── RESET MAX STATE ────────────────────────────────────────────────

@tool("reset_max_state")
def _reset_max_state(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Reset MAX's conversation state, clear caches, reload config.
    FOUNDER ONLY — triggered by 'MAX reset', 'reset yourself', 'clear cache', etc.
    """
    results = []

    # 1. Reload .env
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.expanduser("~/empire-repo/backend/.env"), override=True)
        founder_email = os.getenv("FOUNDER_EMAIL", "empirebox2026@gmail.com")
        results.append(f"Environment reloaded — FOUNDER_EMAIL: {founder_email}")
    except Exception as e:
        results.append(f"Environment reload failed: {e}")

    # 2. Clear system prompt cache
    try:
        from app.services.max.system_prompt import _prompt_cache
        _prompt_cache["prompt"] = None
        _prompt_cache["expires"] = 0
        _prompt_cache.pop("_brain_ctx", None)
        _prompt_cache.pop("_brain_expires", None)
        results.append("System prompt cache cleared")
    except Exception as e:
        results.append(f"Cache clear failed: {e}")

    # 3. Check OpenClaw
    import httpx as _hx
    openclaw_url = os.getenv("OPENCLAW_URL", "http://localhost:7878")
    try:
        resp = _hx.get(f"{openclaw_url}/health", timeout=5)
        if resp.status_code == 200:
            results.append(f"OpenClaw: UP ({openclaw_url})")
        else:
            results.append(f"OpenClaw: responded {resp.status_code} ({openclaw_url})")
    except Exception:
        results.append(f"OpenClaw: DOWN ({openclaw_url})")

    # 4. Report
    results.append("MAX state reset complete. All caches cleared. Ready for commands.")

    return ToolResult(tool="reset_max_state", success=True, result={"actions": results})


# ── TOOL DOCUMENTATION (for system prompt) ─────────────────────────

TOOLS_DOC = """## Available Tools (42 total)
You have access to real tools that query live data. Use them instead of making up information.
To call a tool, include a tool block in your response:

```tool
{"tool": "tool_name", "param1": "value1"}
```

IMPORTANT — EXACT TOOL NAMES ONLY. There is NO tool called "run_command", "execute_command", or "run_shell".
To run shell commands, use "shell_execute". To generate drawings, use "sketch_to_drawing".
If a tool call fails with "Unknown tool", check the name against this list.

### Data Tools
- **search_quotes** — Search quotes by customer or status. Searches BOTH Workroom and CraftForge quotes.
  `{"tool": "search_quotes", "customer_name": "...", "status": "proposal|draft|sent|accepted"}`
  Optional: `source` filter: "workroom", "craftforge", or omit for both. Results include `source` field.
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
- **search_conversations** — Search conversation history across all channels (Telegram, Web, CC). Searches brain memories, conversation summaries, and chat backups.
  `{"tool": "search_conversations", "query": "keyword or phrase", "channel": "telegram|web|cc"}`

### Action Tools
- **create_quick_quote** — Create a quick quote with 3 stacked design proposals (Essential/Designer/Premium). Uses QT-CUSTOMER-DATE-NNN numbering. Total starts at $0 until a proposal is selected.
  `{"tool": "create_quick_quote", "customer_name": "Newman", "rooms": [{"name": "Living Room", "windows": [{"name": "Window 1", "width": 72, "height": 84, "quantity": 1, "treatmentType": "roman-shade", "fabricColor": "navy blue"}]}], "max_analysis": "Professional analysis here..."}`
  CRITICAL: Set treatmentType to EXACTLY what the customer requested (roman-shade, pinch-pleat, ripplefold, grommet, rod-pocket, roller-shade). NEVER default to ripplefold if the customer asked for something else. Include fabricColor if the customer mentioned a color preference.
  Returns 3 options (A: Essential, B: Designer, C: Premium) with different fabric grades and pricing. Founder selects one to finalize.
- **select_proposal** — Select a design proposal (A/B/C) on a quote to finalize the total and convert to a formal estimate.
  `{"tool": "select_proposal", "quote_id": "abc123", "option": "B"}`
  After selection, the quote gets real totals and can be sent via Telegram or email.
- **open_quote_builder** — Open the QuoteBuilder right here in the dashboard (ALWAYS use this instead of linking to WorkroomForge). Pre-fills customer info AND rooms/windows from the conversation.
  `{"tool": "open_quote_builder", "customer_name": "...", "customer_email": "...", "customer_phone": "...", "customer_address": "...", "project_name": "...", "rooms": [{"name": "Living Room", "windows": [{"name": "Window 1", "width": 72, "height": 84, "quantity": 1, "treatmentType": "roman-shade", "fabricColor": "ivory", "liningType": "standard", "hardwareType": "cassette", "motorization": "none", "mountType": "wall"}], "upholstery": []}]}`
  treatmentType options: ripplefold, pinch-pleat, rod-pocket, grommet, roman-shade, roller-shade — USE THE ONE THE CUSTOMER ASKED FOR
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
- **delegate_to_atlas** — Delegate a CODE task to Atlas (Opus). Returns IMMEDIATELY — Atlas works in background while you stay free for the next question. Atlas notifies the founder via Telegram when done or if it fails.
  `{"tool": "delegate_to_atlas", "title": "Add cushion depth shading to bench renderer", "description": "Detailed task description..."}`
  Use this for code changes, file edits, and development tasks. Do NOT use run_desk_task for code — use this instead. You get a task ID back immediately.

### Communication Tools
- **send_telegram** — Send a text message to the founder via Telegram
  `{"tool": "send_telegram", "message": "<b>Title</b>\nMessage body here (HTML formatting)"}`
- **send_quote_telegram** — Generate a quote PDF and send it to the founder via Telegram
  `{"tool": "send_quote_telegram", "quote_id": "abc123"}`
  Use this after creating/saving a quote to deliver the PDF directly to Telegram.
- **send_email** — Send an email with optional file attachments
  `{"tool": "send_email", "to": "client@example.com", "subject": "Your Estimate", "body": "<h2>Hello</h2><p>HTML body here</p>", "attachments": ["/path/to/file.pdf"], "cc": "optional@cc.com"}`
  IMPORTANT: When sending a PDF, you MUST include the file path in the "attachments" array. Without it, the email arrives with no attachment.
- **send_quote_email** — Generate a quote PDF and email it to the recipient
  `{"tool": "send_quote_email", "quote_id": "abc123", "to": "client@example.com"}`
  Use this after creating/saving a quote to email the PDF directly to a client or the founder.
- **svg_to_pdf** — Convert SVG content or file to a PDF. Use this instead of writing Python scripts. Returns the PDF file path.
  `{"tool": "svg_to_pdf", "svg_content": "<svg>...</svg>", "output_path": "/home/rg/empire-repo/uploads/drawing.pdf"}`
  Or from file: `{"tool": "svg_to_pdf", "svg_path": "/path/to/drawing.svg"}`
  IMPORTANT: Always use this tool to convert SVG drawings to PDF. Do NOT write conversion scripts.
- **sketch_to_drawing** — Generate professional architectural drawings for ANY item type. Auto-classifies input and routes to the correct renderer. Returns a PDF file path.
  **Bench drawings** produce a 4-QUADRANT layout: Plan View + Isometric View + Front Elevation + Empire Workroom Title Block.
  Bench (straight): `{"tool": "sketch_to_drawing", "shape": "straight", "lf": 10, "name": "Main Dining Bench", "seat_depth": 18, "seat_height": 18, "back_height": 34}`
  Bench (L-shape): `{"tool": "sketch_to_drawing", "shape": "l_shape", "lf": 12, "name": "Corner Booth"}`
  Bench (U-shape): `{"tool": "sketch_to_drawing", "shape": "u_shape", "lf": 15, "name": "U Booth", "multiplier": 2}`
  **Style params** (optional, owner decides): `"cushion_width": 24` (default 24"), `"panel_style": "vertical_channels"` (or horizontal_channels/tufted/button_tufted/flat), `"channel_count": 6`
  **Client/Project**: `"client": "John Smith", "project": "Restaurant Renovation"`
  From quote: `{"tool": "sketch_to_drawing", "quote_id": "30ad17d4"}`
  Window: `{"tool": "sketch_to_drawing", "name": "Office Windows", "item_type": "window", "dimensions": {"Width": "72\"", "Height": "48\"", "Drop": "84\""}}`
  Generic: `{"tool": "sketch_to_drawing", "name": "Ottoman", "description": "round ottoman", "dimensions": {"Diameter": "36\"", "Height": "18\""}}`
  **AUTO-EMAIL**: Add `"email_to": "me"` (or any email address) to automatically email the PDF as an attachment in a single tool call.
  Example: `{"tool": "sketch_to_drawing", "shape": "straight", "lf": 10, "name": "Main Bench", "email_to": "me"}`
  "me"/"owner"/"founder" resolves to the founder's email. This is the PREFERRED way to draw + email in one step.
  Shapes: "straight", "l-shape", "u-shape". For U-shaped, add "multiplier": 2 if there are multiple booths.

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
  `{"tool": "photo_to_quote", "customer_name": "Customer", "rooms": [{"name": "Room", "windows": [{"name": "Window 1", "width": 72, "height": 84, "quantity": 1, "treatmentType": "pinch-pleat", "fabricColor": "cream"}]}], "max_analysis": "Professional analysis..."}`
  IMPORTANT: Use the correct treatmentType from the customer's request or your photo analysis. Include fabricColor if known.
  This automatically creates the quote, generates the PDF, and sends it via Telegram.

### System Tools
- **get_system_stats** — Real CPU, RAM, disk, temperature
  `{"tool": "get_system_stats"}`
- **get_weather** — Live weather data (no API key needed)
  `{"tool": "get_weather", "city": "Los Angeles"}`
- **get_services_health** — Check which Empire services are running
  `{"tool": "get_services_health"}`
- **ollama_toggle** — Turn Ollama on or off. When off, MAX is faster. When on, RecoveryForge can classify images.
  To toggle: use shell_execute with `curl -X POST http://localhost:8000/api/v1/system/ollama/toggle`
  To check status: use shell_execute with `curl http://localhost:8000/api/v1/system/ollama/status`
  When founder says "turn on/off Ollama", "start/stop RecoveryForge", or "Ollama status" — use these.

IMPORTANT: Always use tools for factual data. NEVER fabricate task lists, weather, system stats, quotes, or customer info. If a tool returns empty results, say so honestly.
When asked to send a quote PDF to Telegram, use send_quote_telegram with the quote_id.
When discussing visual topics (fabrics, designs, installations), use search_images to find relevant reference photos.
When you need current info, pricing, or research — use web_search. Do NOT say "I can't access the web."
When analyzing a photo of windows or furniture, use photo_to_quote to create and deliver the estimate automatically.

### Presentation Tools
- **present** — Generate a professional presentation/report on a topic and send PDF via Telegram.
  `{"tool": "present", "topic": "DC custom drapery market trends 2026"}`
  `{"tool": "present", "topic": "Competitor analysis", "source_content": "Optional context..."}`
  ⚠️ ONLY use this tool when the founder EXPLICITLY asks for a "presentation", "report", "briefing", or "research document". Do NOT auto-generate presentations for casual conversation topics, analogies, or keywords mentioned in passing. If unsure, ask: "Would you like me to create a presentation about X?"

### Shell Execution
- **shell_execute** — Execute a safe, allowlisted shell command. Blocked patterns are rejected.
  `{"tool": "shell_execute", "command": "git status"}`
  `{"tool": "shell_execute", "command": "df -h"}`
  Allowed commands: ls, cat, head, tail, wc, echo, sort, uniq, tee, touch, mkdir, cp, mv, df, du, free, ps, uptime, date, whoami, hostname, pwd, find, grep, python3, sqlite3, git (all operations), curl, wget, pip, pip3, npm, npx, sudo systemctl, systemctl (status/restart/start/stop/is-active), journalctl, ollama list/ps, docker ps/images, chmod 600.
  BLOCKED: rm -rf, rm -r, pkill -f, kill -9, killall, dd, mkfs, fdisk, sudo rm, chmod 777, sensors-detect, eval, exec, pipe to sh/bash.

### Autonomous Execution
- **dispatch_to_openclaw** — Send a task to OpenClaw for autonomous execution. Returns results (blocking).
  `{"tool": "dispatch_to_openclaw", "title": "Health check", "description": "Run full API health check"}`
  `{"tool": "dispatch_to_openclaw", "title": "Disk report", "description": "check disk usage", "wait_for_result": true}`
  Optional: `priority` (low/normal/high/critical), `skills_needed` (list of skill names), `wait_for_result` (true/false)
- **queue_openclaw_task** — Queue a task for OpenClaw (non-blocking). Worker picks it up within 30s. Use this when you want to fire-and-forget.
  `{"tool": "queue_openclaw_task", "title": "Check disk usage", "description": "Run disk usage report", "desk": "ITDesk", "priority": 5}`
  Optional: `desk` (CodeForge/ITDesk/ForgeDesk/etc.), `priority` (1=critical, 5=normal, 10=low)

### System Reset
- **reset_max_state** — Reset MAX: clear caches, reload .env, verify OpenClaw. FOUNDER ONLY.
  `{"tool": "reset_max_state"}`
  Triggers: "MAX reset", "reset yourself", "clear your cache", "reload config", "refresh yourself", "start fresh"

### TOOL DISCIPLINE — READ BEFORE EVERY RESPONSE
- NEVER fabricate data. All statistics, charts, and numbers must come from real tool results.
- NEVER call a tool unless the user's request clearly needs it.
- NEVER treat casual analogies or examples as topics to research. If someone says "like Grasshopper" they mean the concept, not the software.
- For most conversational responses, you don't need ANY tools — just answer directly from your knowledge.
- When you DO use tools, verify the results make sense before presenting them.

### CRITICAL REMINDER — Tool blocks are the ONLY way to act
If the user asks you to "send a PDF", "create a quote", "search the web", or do ANYTHING:
1. You MUST include a ```tool ... ``` block in your response
2. Writing "I sent the PDF" WITHOUT a tool block means NOTHING was sent — the user receives NOTHING
3. The tool block is what triggers execution. Text alone is just words with no effect.

Example — user says "send me the latest quote PDF":
```tool
{{"tool": "search_quotes", "status": "proposal"}}
```
Then after seeing results, use the quote_id:
```tool
{{"tool": "send_quote_telegram", "quote_id": "THE_ACTUAL_ID"}}
```

### Development Tools (Atlas / Orion)
- **file_read** — Read a file with optional line range. `{{"tool": "file_read", "path": "backend/app/main.py", "line_start": 1, "line_end": 50}}`
- **file_write** — Write content to a file. Auto-backups existing files. `{{"tool": "file_write", "path": "backend/app/routers/new.py", "content": "..."}}`
- **file_edit** — Replace a string in a file. Supports exact match, fuzzy whitespace match, and line_number mode. Use `old_str: "__APPEND__"` to append instead.
  `{{"tool": "file_edit", "path": "backend/app/main.py", "old_str": "old code", "new_str": "new code"}}`
  Line number mode: `{{"tool": "file_edit", "path": "file.py", "line_number": 42, "new_str": "replacement line"}}`
- **file_append** — Append content to end of a file (never truncates). Safe for .env files. `{{"tool": "file_append", "path": "backend/.env", "content": "NEW_KEY=value"}}`
- **env_get** — List .env variable names (not values) or check if a specific variable exists.
  `{{"tool": "env_get"}}` or `{{"tool": "env_get", "name": "ANTHROPIC_API_KEY"}}`
- **env_set** — Add or update an env variable in .env. `{{"tool": "env_set", "name": "MY_KEY", "value": "my_value"}}`
- **db_query** — Run a read-only SQLite query on empire.db (SELECT only).
  `{{"tool": "db_query", "query": "SELECT COUNT(*) as cnt FROM customers"}}`
- **git_ops** — Git operations. `{{"tool": "git_ops", "command": "status|diff|add|commit|push|log", "args": "optional args"}}`
- **service_manager** — Manage Empire services. `{{"tool": "service_manager", "command": "status|restart|logs|start|stop", "service": "backend|cc|openclaw|ollama|recoveryforge|relistapp|all"}}`
- **package_manager** — Install packages or build. `{{"tool": "package_manager", "command": "pip_install|npm_install|npm_build|pip_list|npm_list", "package": "...", "project_dir": "..."}}`
- **test_runner** — Run tests and health checks. `{{"tool": "test_runner", "command": "endpoint|all|build|health", "url": "...", "method": "GET"}}`
- **project_scaffold** — Create new files from templates. `{{"tool": "project_scaffold", "command": "router|component|desk|page", "name": "..."}}`

### TOOL USAGE PRIORITY
For simple single-tool tasks, use the tool DIRECTLY — do NOT delegate to a desk:
- File reads/writes → file_read, file_write, file_edit, file_append
- Shell commands → shell_execute
- Service checks → get_services_health or service_manager
- Git operations → git_ops
- Database queries → db_query
- .env management → env_get, env_set
Only delegate to a desk (run_desk_task) for complex multi-step tasks that require AI reasoning.
"""


# ── DEV TOOLS (Atlas/Orion) ─────────────────────────────────────────

from app.services.max.tool_safety import validate_path, validate_command, is_critical_file
from app.services.max.tool_audit import log_execution
import subprocess
import time as _time


@tool("file_read")
def _file_read(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Read a file with optional line range."""
    start = _time.time()
    path = params.get("path", "")
    if not path:
        return ToolResult(tool="file_read", success=False, error="path is required")

    # Expand relative paths to empire-repo
    if not os.path.isabs(path):
        path = os.path.join(os.path.expanduser("~/empire-repo"), path)

    ok, reason = validate_path(path)
    if not ok:
        log_execution("file_read", params, reason, desk=desk, success=False)
        return ToolResult(tool="file_read", success=False, error=reason)

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        line_start = params.get("line_start")
        line_end = params.get("line_end")
        total = len(lines)

        if line_start or line_end:
            s = max(1, line_start or 1) - 1
            e = min(total, line_end or total)
            selected = lines[s:e]
            content = "".join(f"{i+s+1:4d} | {l}" for i, l in enumerate(selected))
        else:
            # Cap at 500 lines for safety
            if total > 500:
                selected = lines[:500]
                content = "".join(f"{i+1:4d} | {l}" for i, l in enumerate(selected))
                content += f"\n... ({total - 500} more lines truncated)"
            else:
                content = "".join(f"{i+1:4d} | {l}" for i, l in enumerate(lines))

        duration = int((_time.time() - start) * 1000)
        log_execution("file_read", params, {"lines": total}, desk=desk, success=True, duration_ms=duration)
        return ToolResult(tool="file_read", success=True, result={
            "content": content, "lines": total, "path": path,
        })
    except FileNotFoundError:
        log_execution("file_read", params, "not found", desk=desk, success=False)
        return ToolResult(tool="file_read", success=False, error=f"File not found: {path}")
    except Exception as e:
        log_execution("file_read", params, str(e), desk=desk, success=False)
        return ToolResult(tool="file_read", success=False, error=str(e))


@tool("file_write")
def _file_write(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Write content to a file."""
    start = _time.time()
    path = params.get("path", "")
    content = params.get("content", "")
    if not path:
        return ToolResult(tool="file_write", success=False, error="path is required")

    if not os.path.isabs(path):
        path = os.path.join(os.path.expanduser("~/empire-repo"), path)

    ok, reason = validate_path(path)
    if not ok:
        log_execution("file_write", params, reason, desk=desk, success=False)
        return ToolResult(tool="file_write", success=False, error=reason)

    # Block file_write to critical system files — use file_edit instead
    if is_critical_file(path):
        log_execution("file_write", params, "critical file blocked", desk=desk, success=False)
        return ToolResult(
            tool="file_write",
            success=False,
            error=f"BLOCKED: {os.path.basename(path)} is a critical system file. Use file_edit for modifications.",
        )

    # Safety: prevent accidental truncation of existing files
    if os.path.exists(path):
        import shutil
        old_size = os.path.getsize(path)
        new_size = len(content.encode('utf-8'))

        # Always backup before overwrite
        backup_path = f"{path}.bak-{int(_time.time())}"
        shutil.copy2(path, backup_path)

        # Critical files: block if < 30% of original (likely truncation)
        basename = os.path.basename(path)
        critical_basenames = ["main.py", "ai_router.py", "system_prompt.py", ".env"]
        if basename in critical_basenames and old_size > 500 and new_size < (old_size * 0.3):
            log_execution("file_write", params, "critical truncation blocked", desk=desk, success=False)
            return ToolResult(
                tool="file_write",
                success=False,
                error=f"BLOCKED: New content ({new_size} bytes) is less than 30% of critical file ({old_size} bytes). Use file_edit for partial changes.",
            )

        # Normal files: block only if < 10% (obviously corrupted)
        if old_size > 1000 and new_size < (old_size * 0.1):
            log_execution("file_write", params, "truncation blocked", desk=desk, success=False)
            return ToolResult(
                tool="file_write",
                success=False,
                error=f"BLOCKED: New content ({new_size} bytes) is less than 10% of existing file ({old_size} bytes). This looks like accidental truncation. Use file_edit for partial changes.",
            )

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        nbytes = len(content.encode("utf-8"))
        duration = int((_time.time() - start) * 1000)
        log_execution("file_write", params, {"lines": lines, "bytes": nbytes}, access_level=2, desk=desk, success=True, duration_ms=duration)
        return ToolResult(tool="file_write", success=True, result={
            "path": path, "lines": lines, "bytes": nbytes,
        })
    except Exception as e:
        log_execution("file_write", params, str(e), desk=desk, success=False)
        return ToolResult(tool="file_write", success=False, error=str(e))


@tool("file_edit")
def _file_edit(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Replace first occurrence of old_str with new_str in a file.
    Special: if old_str is empty or '__APPEND__', appends new_str instead."""
    start = _time.time()
    path = params.get("path", "")
    old_str = params.get("old_str", "")
    new_str = params.get("new_str", "")

    # __APPEND__ mode: delegate to file_append logic
    if not old_str or old_str == "__APPEND__":
        if not path or not new_str:
            return ToolResult(tool="file_edit", success=False, error="path and new_str are required for append mode")
        return _file_append({"path": path, "content": new_str}, desk=desk)

    if not path:
        return ToolResult(tool="file_edit", success=False, error="path and old_str are required")

    if not os.path.isabs(path):
        path = os.path.join(os.path.expanduser("~/empire-repo"), path)

    ok, reason = validate_path(path)
    if not ok:
        log_execution("file_edit", params, reason, desk=desk, success=False)
        return ToolResult(tool="file_edit", success=False, error=reason)

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Line number mode: edit by line number instead of string match
        line_number = params.get("line_number")
        if line_number is not None:
            lines = content.split("\n")
            ln = int(line_number)
            if ln < 1 or ln > len(lines):
                return ToolResult(tool="file_edit", success=False, error=f"Line {ln} out of range (file has {len(lines)} lines)")
            old_line = lines[ln - 1]
            lines[ln - 1] = new_str
            new_content = "\n".join(lines)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            duration = int((_time.time() - start) * 1000)
            log_execution("file_edit", params, {"line": ln, "mode": "line_number"}, access_level=2, desk=desk, success=True, duration_ms=duration)
            return ToolResult(tool="file_edit", success=True, result={
                "path": path, "mode": "line_number", "line": ln,
                "diff_preview": f"-{old_line[:80]}\n+{new_str[:80]}",
            })

        # Standard string match mode
        if old_str in content:
            new_content = content.replace(old_str, new_str, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            old_lines = old_str.strip().split("\n")
            new_lines = new_str.strip().split("\n")
            preview = f"-{old_lines[0][:80]}\n+{new_lines[0][:80]}"
            duration = int((_time.time() - start) * 1000)
            log_execution("file_edit", params, {"replacements": 1}, access_level=2, desk=desk, success=True, duration_ms=duration)
            return ToolResult(tool="file_edit", success=True, result={
                "path": path, "replacements": 1, "diff_preview": preview,
            })

        # Fuzzy match: try stripping whitespace
        content_lines = content.split("\n")
        old_stripped = old_str.strip()
        for i, line in enumerate(content_lines):
            if line.strip() == old_stripped:
                content_lines[i] = content_lines[i].replace(line.strip(), new_str.strip())
                new_content = "\n".join(content_lines)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                duration = int((_time.time() - start) * 1000)
                log_execution("file_edit", params, {"mode": "fuzzy_whitespace", "line": i + 1}, access_level=2, desk=desk, success=True, duration_ms=duration)
                return ToolResult(tool="file_edit", success=True, result={
                    "path": path, "replacements": 1, "mode": "fuzzy_whitespace",
                    "diff_preview": f"-{line[:80]}\n+{new_str.strip()[:80]}",
                    "note": f"Fuzzy matched at line {i + 1} (whitespace difference)",
                })

        # Multi-line fuzzy: try matching stripped multi-line blocks
        old_lines_stripped = [l.strip() for l in old_str.strip().split("\n") if l.strip()]
        if len(old_lines_stripped) > 1:
            for i in range(len(content_lines) - len(old_lines_stripped) + 1):
                window = [content_lines[i + j].strip() for j in range(len(old_lines_stripped))]
                if window == old_lines_stripped:
                    for j in range(len(old_lines_stripped)):
                        content_lines[i + j] = ""  # Clear matched lines
                    content_lines[i] = new_str  # Insert replacement at first line
                    # Remove the emptied lines
                    new_content = "\n".join(l for idx, l in enumerate(content_lines) if not (i < idx < i + len(old_lines_stripped) and l == ""))
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    duration = int((_time.time() - start) * 1000)
                    log_execution("file_edit", params, {"mode": "fuzzy_multiline", "line": i + 1}, access_level=2, desk=desk, success=True, duration_ms=duration)
                    return ToolResult(tool="file_edit", success=True, result={
                        "path": path, "replacements": 1, "mode": "fuzzy_multiline",
                        "note": f"Fuzzy matched {len(old_lines_stripped)} lines starting at line {i + 1}",
                    })

        # No match found — return nearby lines to help retry
        from difflib import SequenceMatcher
        best_ratio = 0
        best_line_num = 0
        best_line = ""
        search_first_line = old_str.strip().split("\n")[0].strip()
        for i, line in enumerate(content_lines):
            ratio = SequenceMatcher(None, search_first_line, line.strip()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_line_num = i + 1
                best_line = line

        hint = ""
        if best_ratio > 0.5:
            hint = f" Closest match at line {best_line_num} ({int(best_ratio*100)}% similar): '{best_line.strip()[:100]}'"

        log_execution("file_edit", params, "old_str not found", desk=desk, success=False)
        return ToolResult(tool="file_edit", success=False, error=f"old_str not found in file.{hint} Try using line_number mode instead.")
    except Exception as e:
        log_execution("file_edit", params, str(e), desk=desk, success=False)
        return ToolResult(tool="file_edit", success=False, error=str(e))


@tool("file_append")
def _file_append(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Append content to a file. Never truncates or overwrites existing content."""
    start = _time.time()
    path = params.get("path", "")
    content = params.get("content", "")
    if not path:
        return ToolResult(tool="file_append", success=False, error="path is required")
    if not content:
        return ToolResult(tool="file_append", success=False, error="content is required")

    if not os.path.isabs(path):
        path = os.path.join(os.path.expanduser("~/empire-repo"), path)

    ok, reason = validate_path(path)
    if not ok:
        log_execution("file_append", params, reason, desk=desk, success=False)
        return ToolResult(tool="file_append", success=False, error=reason)

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content if content.endswith("\n") else content + "\n")

        nbytes = len(content.encode("utf-8"))
        duration = int((_time.time() - start) * 1000)
        log_execution("file_append", params, {"bytes": nbytes}, access_level=2, desk=desk, success=True, duration_ms=duration)
        return ToolResult(tool="file_append", success=True, result={
            "path": path, "bytes_appended": nbytes,
        })
    except Exception as e:
        log_execution("file_append", params, str(e), desk=desk, success=False)
        return ToolResult(tool="file_append", success=False, error=str(e))


@tool("env_get")
def _env_get(params: dict, desk: Optional[str] = None) -> ToolResult:
    """List .env variable names (not values) or check if a specific variable exists."""
    env_path = os.path.expanduser("~/empire-repo/backend/.env")
    var_name = params.get("name", "").strip()

    try:
        with open(env_path, "r") as f:
            lines = f.readlines()

        env_vars = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                name = line.split("=", 1)[0].strip()
                has_value = bool(line.split("=", 1)[1].strip())
                env_vars.append({"name": name, "set": has_value})

        if var_name:
            found = next((v for v in env_vars if v["name"] == var_name), None)
            if found:
                return ToolResult(tool="env_get", success=True, result={"name": var_name, "exists": True, "set": found["set"]})
            return ToolResult(tool="env_get", success=True, result={"name": var_name, "exists": False})

        return ToolResult(tool="env_get", success=True, result={"variables": env_vars, "count": len(env_vars)})
    except Exception as e:
        return ToolResult(tool="env_get", success=False, error=str(e))


@tool("env_set")
def _env_set(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Add or update an env variable in .env file. Level 2 — logged."""
    env_path = os.path.expanduser("~/empire-repo/backend/.env")
    var_name = params.get("name", "").strip()
    var_value = params.get("value", "").strip()

    if not var_name:
        return ToolResult(tool="env_set", success=False, error="Variable name is required")
    if not var_value:
        return ToolResult(tool="env_set", success=False, error="Variable value is required")

    try:
        lines = []
        replaced = False
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                if line.strip().startswith(f"{var_name}="):
                    lines[i] = f"{var_name}={var_value}\n"
                    replaced = True
                    break

        if not replaced:
            lines.append(f"{var_name}={var_value}\n")

        with open(env_path, "w") as f:
            f.writelines(lines)

        os.chmod(env_path, 0o600)
        log_execution("env_set", {"name": var_name}, "set", access_level=2, desk=desk, success=True)
        return ToolResult(tool="env_set", success=True, result={
            "name": var_name, "action": "replaced" if replaced else "added",
        })
    except Exception as e:
        return ToolResult(tool="env_set", success=False, error=str(e))


@tool("db_query")
def _db_query(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Run a read-only SQLite query on empire.db. Only SELECT statements allowed."""
    import sqlite3
    query = params.get("query", "").strip()
    if not query:
        return ToolResult(tool="db_query", success=False, error="query is required")

    # Safety: only allow SELECT
    if not query.upper().startswith("SELECT"):
        return ToolResult(tool="db_query", success=False, error="Only SELECT queries are allowed")

    # Block dangerous patterns
    dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "ATTACH", "DETACH"]
    query_upper = query.upper()
    for d in dangerous:
        if d in query_upper:
            return ToolResult(tool="db_query", success=False, error=f"Query contains blocked keyword: {d}")

    db_path = os.path.expanduser("~/empire-repo/backend/data/empire.db")
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        data = [dict(r) for r in rows[:100]]  # Cap at 100 rows
        conn.close()

        log_execution("db_query", {"query": query[:200]}, {"rows": len(data)}, desk=desk, success=True)
        return ToolResult(tool="db_query", success=True, result={
            "columns": columns, "rows": data, "count": len(data),
            "note": f"Showing {len(data)} of {len(rows)} rows" if len(rows) > 100 else None,
        })
    except Exception as e:
        return ToolResult(tool="db_query", success=False, error=str(e))


@tool("git_ops")
def _git_ops(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Run git operations in ~/empire-repo."""
    start = _time.time()
    command = params.get("command", "")
    args = params.get("args", "")

    allowed_commands = {"status", "diff", "add", "commit", "push", "log", "branch"}
    if command not in allowed_commands:
        return ToolResult(tool="git_ops", success=False, error=f"Unknown git command: {command}. Allowed: {', '.join(allowed_commands)}")

    # Determine access level
    if command in ("status", "diff", "log", "branch"):
        level = 1
    elif command in ("add", "commit"):
        level = 2
    else:  # push
        level = 3

    repo = os.path.expanduser("~/empire-repo")
    cmd_parts = ["git", command]
    if args:
        cmd_parts.extend(args.split())

    full_cmd = " ".join(cmd_parts)
    ok, reason = validate_command(full_cmd)
    if not ok:
        log_execution("git_ops", params, reason, access_level=level, desk=desk, success=False)
        return ToolResult(tool="git_ops", success=False, error=reason)

    try:
        result = subprocess.run(
            cmd_parts, cwd=repo,
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout + result.stderr
        duration = int((_time.time() - start) * 1000)
        success = result.returncode == 0
        log_execution("git_ops", params, {"exit_code": result.returncode}, access_level=level, desk=desk, success=success, duration_ms=duration)
        return ToolResult(tool="git_ops", success=success, result={
            "command": full_cmd, "output": output[:3000], "exit_code": result.returncode,
        })
    except subprocess.TimeoutExpired:
        log_execution("git_ops", params, "timeout", access_level=level, desk=desk, success=False)
        return ToolResult(tool="git_ops", success=False, error="Git command timed out")
    except Exception as e:
        log_execution("git_ops", params, str(e), access_level=level, desk=desk, success=False)
        return ToolResult(tool="git_ops", success=False, error=str(e))


SERVICE_MAP = {
    "backend": {"port": 8000, "systemd": "empire-backend", "log": "/tmp/backend.log"},
    "cc": {"port": 3005, "systemd": "empire-portal", "log_dir": os.path.expanduser("~/empire-repo/logs")},
    "openclaw": {"port": 7878, "systemd": "empire-openclaw", "log": "/tmp/openclaw.log"},
    "ollama": {"port": 11434, "systemd": "ollama", "log": None},
    "recoveryforge": {"port": 3077, "systemd": None, "log_dir": os.path.expanduser("~/empire-repo/logs")},
    "relistapp": {"port": 3007, "systemd": None, "log_dir": os.path.expanduser("~/empire-repo/logs")},
}

# Systemd service names for monitored services
SYSTEMD_SERVICES = ["empire-backend", "empire-portal", "empire-openclaw"]


def _systemctl_cmd(systemd_unit: str, *args: str) -> list[str]:
    """Use the user service manager for Empire units, system manager otherwise."""
    base = ["systemctl"]
    if systemd_unit.startswith("empire-"):
        base.append("--user")
    return base + list(args) + [systemd_unit]


def _should_retry_systemctl_with_sudo(systemd_unit: str, stderr: str) -> bool:
    if systemd_unit.startswith("empire-"):
        return False
    lower_stderr = (stderr or "").lower()
    return "access denied" in lower_stderr or "authentication required" in lower_stderr


@tool("service_manager")
def _service_manager(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Manage Empire services via systemd: status, restart, logs, start, stop."""
    start = _time.time()
    command = params.get("command", "status")
    service = params.get("service", "all")

    if command not in ("status", "restart", "logs", "start", "stop"):
        return ToolResult(tool="service_manager", success=False, error=f"Unknown command: {command}")

    level = 1 if command in ("status", "logs") else 3

    services_to_check = SERVICE_MAP.keys() if service == "all" else [service]
    results = []

    for svc_name in services_to_check:
        svc = SERVICE_MAP.get(svc_name)
        if not svc:
            results.append({"name": svc_name, "error": "Unknown service"})
            continue

        port = svc["port"]
        systemd_unit = svc.get("systemd")

        if command == "status":
            state = "unknown"
            pid = None
            uptime = None

            # Try systemd first
            if systemd_unit:
                try:
                    r = subprocess.run(
                        _systemctl_cmd(systemd_unit, "is-active", "--quiet"),
                        capture_output=True, text=True, timeout=5,
                    )
                    state = "active" if r.returncode == 0 else "inactive"
                except Exception:
                    pass

                # Get PID and uptime from systemd show
                if state == "active":
                    try:
                        r = subprocess.run(
                            _systemctl_cmd(systemd_unit, "show", "--property=MainPID,ActiveEnterTimestamp", "--no-pager"),
                            capture_output=True, text=True, timeout=5,
                        )
                        for line in r.stdout.strip().split("\n"):
                            if line.startswith("MainPID="):
                                pid_str = line.split("=", 1)[1].strip()
                                if pid_str and pid_str != "0":
                                    pid = int(pid_str)
                            elif line.startswith("ActiveEnterTimestamp="):
                                uptime = line.split("=", 1)[1].strip()
                    except Exception:
                        pass

            # Fallback: port check for services without systemd units
            if state == "unknown":
                import socket
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=2):
                        state = "active"
                except (ConnectionRefusedError, TimeoutError, OSError):
                    state = "inactive"

                # Try to find PID via fuser
                if state == "active":
                    try:
                        r = subprocess.run(
                            ["fuser", f"{port}/tcp"],
                            capture_output=True, text=True, timeout=5,
                        )
                        if r.stdout.strip():
                            pid = int(r.stdout.strip().split()[-1])
                    except Exception:
                        pass

            results.append({
                "name": svc_name, "port": port, "state": state,
                "running": state == "active", "pid": pid, "uptime": uptime,
                "systemd_unit": systemd_unit,
            })

        elif command in ("restart", "start", "stop") and systemd_unit:
            try:
                # Try without sudo first, fallback to sudo
                r = subprocess.run(
                    _systemctl_cmd(systemd_unit, command),
                    capture_output=True, text=True, timeout=30,
                )
                if r.returncode != 0 and _should_retry_systemctl_with_sudo(systemd_unit, r.stderr):
                    # Retry with sudo
                    r = subprocess.run(
                        ["sudo", "systemctl", command, systemd_unit],
                        capture_output=True, text=True, timeout=30,
                    )
                success = r.returncode == 0
                results.append({
                    "name": svc_name, "action": command, "success": success,
                    "output": (r.stdout + r.stderr)[:500],
                })
            except Exception as e:
                results.append({"name": svc_name, "action": command, "success": False, "error": str(e)})

        elif command == "logs":
            # Try journalctl for systemd services first
            if systemd_unit:
                try:
                    r = subprocess.run(
                        ["journalctl", "-u", systemd_unit, "--no-pager", "-n", "50"],
                        capture_output=True, text=True, timeout=10,
                    )
                    if r.stdout.strip():
                        results.append({"name": svc_name, "log": r.stdout[:5000]})
                        continue
                except Exception:
                    pass

            # Fallback to log files
            log_path = svc.get("log")
            if not log_path and svc.get("log_dir"):
                log_dir = svc["log_dir"]
                try:
                    files = sorted(
                        [f for f in os.listdir(log_dir) if svc_name in f.lower() or (svc_name == "cc" and "command_center" in f.lower())],
                        reverse=True,
                    )
                    if files:
                        log_path = os.path.join(log_dir, files[0])
                except Exception:
                    pass

            if log_path and os.path.exists(log_path):
                try:
                    with open(log_path, "r") as f:
                        lines = f.readlines()
                    tail = "".join(lines[-50:])
                    results.append({"name": svc_name, "log": tail[:5000]})
                except Exception as e:
                    results.append({"name": svc_name, "error": str(e)})
            else:
                results.append({"name": svc_name, "error": "No log file found"})

    duration = int((_time.time() - start) * 1000)
    log_execution("service_manager", params, {"services": len(results)}, access_level=level, desk=desk, success=True, duration_ms=duration)
    return ToolResult(tool="service_manager", success=True, result={"services": results})


@tool("package_manager")
def _package_manager(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Install packages or build projects."""
    start = _time.time()
    command = params.get("command", "")
    package = params.get("package", "")
    project_dir = params.get("project_dir", "")

    level = 1 if command in ("pip_list", "npm_list", "npm_build") else 2

    try:
        if command == "pip_install":
            if not package:
                return ToolResult(tool="package_manager", success=False, error="package is required")
            venv_pip = os.path.expanduser("~/empire-repo/backend/venv/bin/pip3")
            r = subprocess.run(
                [venv_pip, "install", package],
                capture_output=True, text=True, timeout=120,
            )
        elif command == "pip_list":
            venv_pip = os.path.expanduser("~/empire-repo/backend/venv/bin/pip3")
            search = package or ""
            r = subprocess.run(
                [venv_pip, "list"], capture_output=True, text=True, timeout=30,
            )
            if search:
                lines = [l for l in r.stdout.split("\n") if search.lower() in l.lower()]
                r = type(r)(args=r.args, returncode=0, stdout="\n".join(lines), stderr="")
        elif command == "npm_install":
            pdir = project_dir or os.path.expanduser("~/empire-repo/empire-command-center")
            if not os.path.isabs(pdir):
                pdir = os.path.join(os.path.expanduser("~/empire-repo"), pdir)
            r = subprocess.run(
                ["npm", "install"] + ([package] if package else []),
                cwd=pdir, capture_output=True, text=True, timeout=120,
            )
        elif command == "npm_build":
            pdir = project_dir or os.path.expanduser("~/empire-repo/empire-command-center")
            if not os.path.isabs(pdir):
                pdir = os.path.join(os.path.expanduser("~/empire-repo"), pdir)
            r = subprocess.run(
                ["npx", "next", "build"],
                cwd=pdir, capture_output=True, text=True, timeout=300,
            )
        elif command == "npm_list":
            pdir = project_dir or os.path.expanduser("~/empire-repo/empire-command-center")
            if not os.path.isabs(pdir):
                pdir = os.path.join(os.path.expanduser("~/empire-repo"), pdir)
            r = subprocess.run(
                ["npm", "list", "--depth=0"],
                cwd=pdir, capture_output=True, text=True, timeout=30,
            )
        else:
            return ToolResult(tool="package_manager", success=False, error=f"Unknown command: {command}")

        duration = int((_time.time() - start) * 1000)
        success = r.returncode == 0
        output = (r.stdout + r.stderr)[:5000]
        log_execution("package_manager", params, {"exit_code": r.returncode}, access_level=level, desk=desk, success=success, duration_ms=duration)
        return ToolResult(tool="package_manager", success=success, result={
            "output": output, "success": success,
        })
    except subprocess.TimeoutExpired:
        log_execution("package_manager", params, "timeout", access_level=level, desk=desk, success=False)
        return ToolResult(tool="package_manager", success=False, error="Command timed out")
    except Exception as e:
        log_execution("package_manager", params, str(e), access_level=level, desk=desk, success=False)
        return ToolResult(tool="package_manager", success=False, error=str(e))


CRITICAL_ENDPOINTS = [
    ("GET", "/health", "Backend Health"),
    ("GET", "/api/v1/max/ai-desks/status", "Desk Status"),
    ("GET", "/api/v1/system/stats", "System Stats"),
    ("GET", "/api/v1/costs/summary", "Cost Summary"),
    ("GET", "/api/v1/finance/dashboard", "Finance Dashboard"),
    ("GET", "/api/v1/inventory/items", "Inventory"),
    ("GET", "/api/v1/crm/customers", "CRM Customers"),
    ("GET", "/api/v1/tasks", "Tasks"),
    ("GET", "/api/v1/chats/conversations", "Chat History"),
    ("GET", "/api/v1/files/", "Files"),
    ("GET", "/api/v1/notifications/", "Notifications"),
    ("GET", "/api/v1/quotes/", "Quotes"),
    ("GET", "/api/v1/tickets/", "Tickets"),
    ("GET", "/api/v1/inbox/", "Inbox"),
    ("GET", "/api/v1/contacts/", "Contacts"),
]


@tool("test_runner")
def _test_runner(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Run endpoint tests and health checks."""
    start = _time.time()
    command = params.get("command", "health")
    url = params.get("url", "")
    method = params.get("method", "GET")

    results = []
    passed = 0
    failed = 0

    if command == "endpoint" and url:
        try:
            r = httpx.request(method, url if url.startswith("http") else f"http://localhost:8000{url}", timeout=10)
            ok = 200 <= r.status_code < 500
            results.append({
                "url": url, "status": r.status_code, "ok": ok,
                "time_ms": int(r.elapsed.total_seconds() * 1000),
                "body_preview": r.text[:200],
            })
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            results.append({"url": url, "error": str(e), "ok": False})
            failed += 1

    elif command in ("all", "health"):
        import socket

        # Test endpoints
        for method_name, path, label in CRITICAL_ENDPOINTS:
            try:
                r = httpx.request(method_name, f"http://localhost:8000{path}", timeout=5)
                ok = 200 <= r.status_code < 500
                results.append({"label": label, "path": path, "status": r.status_code, "ok": ok})
                if ok:
                    passed += 1
                else:
                    failed += 1
            except Exception:
                results.append({"label": label, "path": path, "ok": False, "error": "unreachable"})
                failed += 1

        if command == "health":
            # Also check service ports
            for name, info in SERVICE_MAP.items():
                try:
                    with socket.create_connection(("127.0.0.1", info["port"]), timeout=2):
                        results.append({"label": f"Service: {name}", "port": info["port"], "ok": True})
                        passed += 1
                except Exception:
                    results.append({"label": f"Service: {name}", "port": info["port"], "ok": False})
                    failed += 1

    elif command == "build":
        pdir = os.path.expanduser("~/empire-repo/empire-command-center")
        try:
            r = subprocess.run(
                ["npx", "next", "build"],
                cwd=pdir, capture_output=True, text=True, timeout=300,
            )
            ok = r.returncode == 0
            results.append({"label": "CC Build", "ok": ok, "output": (r.stdout + r.stderr)[-2000:]})
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            results.append({"label": "CC Build", "ok": False, "error": str(e)})
            failed += 1

    duration = int((_time.time() - start) * 1000)
    log_execution("test_runner", params, {"passed": passed, "failed": failed}, desk=desk, success=True, duration_ms=duration)
    return ToolResult(tool="test_runner", success=True, result={
        "results": results, "passed": passed, "failed": failed,
    })


SCAFFOLD_TEMPLATES = {
    "router": '''"""
{name} Router — auto-generated by Atlas (CodeForge).
"""
from fastapi import APIRouter, HTTPException
import logging

router = APIRouter()
logger = logging.getLogger("{name}")


@router.get("/{name}/")
async def list_{name}():
    """List all {name} items."""
    return {{"items": [], "count": 0}}


@router.get("/{name}/{{item_id}}")
async def get_{name}(item_id: str):
    """Get a single {name} item."""
    raise HTTPException(status_code=404, detail="Not found")


@router.post("/{name}/")
async def create_{name}(data: dict):
    """Create a new {name} item."""
    return {{"id": "new", "status": "created", **data}}
''',
    "component": '''\'use client\';
import {{ useState, useEffect }} from 'react';
import {{ Loader2, AlertCircle }} from 'lucide-react';
import {{ API }} from '../../lib/api';

export default function {Name}() {{
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {{
    fetch(`${{API}}/{name}/`)
      .then(r => r.json())
      .then(d => {{ setData(d.items || []); setLoading(false); }})
      .catch(e => {{ setError(e.message); setLoading(false); }});
  }}, []);

  if (loading) return <div className="flex items-center justify-center p-8"><Loader2 className="animate-spin" size={{20}} /></div>;
  if (error) return <div className="flex items-center gap-2 p-4 text-red-600"><AlertCircle size={{16}} />{{error}}</div>;
  if (!data.length) return <div className="p-8 text-center text-gray-400">No items yet</div>;

  return (
    <div style={{{{ padding: '24px 28px' }}}}>
      <h2 style={{{{ fontSize: 20, fontWeight: 700, marginBottom: 16, color: '#1a1a1a' }}}}>
        {Name}
      </h2>
      <div style={{{{ display: 'flex', flexDirection: 'column', gap: 8 }}}}>
        {{data.map((item, i) => (
          <div key={{i}} style={{{{
            padding: '12px 16px', background: '#faf9f7',
            border: '1px solid #ece8e0', borderRadius: 10,
            fontSize: 13, color: '#555',
          }}}}>
            {{JSON.stringify(item)}}
          </div>
        ))}}
      </div>
    </div>
  );
}}
''',
    "desk": '''"""
{Name}Desk — auto-generated by Atlas (CodeForge).
"""
import logging
from .base_desk import BaseDesk, DeskTask, DeskAction

logger = logging.getLogger("max.desks.{name}")


class {Name}Desk(BaseDesk):
    desk_id = "{name}"
    desk_name = "{Name}Desk"
    agent_name = "{Name}"
    desk_description = "{Name} desk — handles {name}-related tasks"
    capabilities = ["{name}_management"]

    async def handle_task(self, task: DeskTask) -> DeskTask:
        await self.accept_task(task)
        try:
            result = await self.ai_execute_task(task)
            return await self.complete_task(task, result)
        except Exception as e:
            logger.error(f"{Name}Desk task failed: {{e}}")
            return await self.fail_task(task, str(e))
''',
}


@tool("project_scaffold")
def _project_scaffold(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Create new files from templates."""
    start = _time.time()
    command = params.get("command", "")
    name = params.get("name", "").strip()

    if not name:
        return ToolResult(tool="project_scaffold", success=False, error="name is required")

    if command not in SCAFFOLD_TEMPLATES and command != "page":
        return ToolResult(tool="project_scaffold", success=False, error=f"Unknown scaffold type: {command}")

    name_lower = name.lower().replace(" ", "_").replace("-", "_")
    name_cap = "".join(w.capitalize() for w in name_lower.split("_"))
    files_created = []
    hints = []

    try:
        if command == "router":
            path = os.path.expanduser(f"~/empire-repo/backend/app/routers/{name_lower}.py")
            content = SCAFFOLD_TEMPLATES["router"].format(name=name_lower)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            files_created.append(path)
            hints.append(f'Add to main.py: load_router("app.routers.{name_lower}", "/api/v1", ["{name_lower}"])')

        elif command == "component":
            path = os.path.expanduser(f"~/empire-repo/empire-command-center/app/components/screens/{name_cap}.tsx")
            content = SCAFFOLD_TEMPLATES["component"].format(name=name_lower, Name=name_cap)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            files_created.append(path)
            hints.append(f"Import in page.tsx: import {name_cap} from './components/screens/{name_cap}'")

        elif command == "desk":
            path = os.path.expanduser(f"~/empire-repo/backend/app/services/max/desks/{name_lower}_desk.py")
            content = SCAFFOLD_TEMPLATES["desk"].format(name=name_lower, Name=name_cap)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            files_created.append(path)
            hints.append(f"Register in desk_manager.py: from .{name_lower}_desk import {name_cap}Desk")

        elif command == "page":
            # Create both router + component
            router_path = os.path.expanduser(f"~/empire-repo/backend/app/routers/{name_lower}.py")
            comp_path = os.path.expanduser(f"~/empire-repo/empire-command-center/app/components/screens/{name_cap}Page.tsx")
            with open(router_path, "w") as f:
                f.write(SCAFFOLD_TEMPLATES["router"].format(name=name_lower))
            with open(comp_path, "w") as f:
                f.write(SCAFFOLD_TEMPLATES["component"].format(name=name_lower, Name=name_cap + "Page"))
            files_created.extend([router_path, comp_path])
            hints.append(f'Register router + import component in page.tsx')

        duration = int((_time.time() - start) * 1000)
        log_execution("project_scaffold", params, {"files": len(files_created)}, access_level=2, desk=desk, success=True, duration_ms=duration)
        return ToolResult(tool="project_scaffold", success=True, result={
            "files_created": files_created, "register_hints": hints,
        })
    except Exception as e:
        log_execution("project_scaffold", params, str(e), access_level=2, desk=desk, success=False)
        return ToolResult(tool="project_scaffold", success=False, error=str(e))


# ── CONVERSATION SEARCH ──────────────────────────────────────────────

@tool("search_conversations")
def _search_conversations(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Search conversation history across all channels (Telegram, Web, CC).

    Params:
        query (str): keyword or phrase to search for
        channel (str, optional): filter by channel — "telegram", "web", "cc"
        date_from (str, optional): start date YYYY-MM-DD
        date_to (str, optional): end date YYYY-MM-DD
        limit (int, optional): max results (default 20, max 50)
    """
    start = _time.time()
    query = params.get("query", "").strip()
    channel = params.get("channel", "").strip().lower()
    date_from = params.get("date_from", "")
    date_to = params.get("date_to", "")
    limit = min(int(params.get("limit", 20)), 50)

    if not query:
        return ToolResult(tool="search_conversations", success=False, error="query is required")

    results = []

    # 1. Search brain memories (conversation facts, intents, customer mentions)
    try:
        from app.services.max.brain.memory_store import MemoryStore
        store = MemoryStore()
        memories = store.search_memories(query=query, limit=limit)
        for mem in memories:
            created = mem.get("created_at", "")
            # Date range filter
            if date_from and created < date_from:
                continue
            if date_to and created > date_to + "T23:59:59":
                continue
            results.append({
                "type": "memory",
                "category": mem.get("category", ""),
                "subject": mem.get("subject", ""),
                "content": mem.get("content", "")[:500],
                "source": mem.get("source", ""),
                "date": created[:10] if created else "",
                "importance": mem.get("importance", 1),
            })
    except Exception as e:
        logger.warning(f"search_conversations: brain memory search failed: {e}")

    # 2. Search conversation summaries
    try:
        from app.services.max.brain.brain_config import get_db_path
        import sqlite3
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row

        conditions = ["(summary LIKE ? OR topics LIKE ? OR customers_mentioned LIKE ? OR key_decisions LIKE ?)"]
        q_like = f"%{query}%"
        sql_params = [q_like, q_like, q_like, q_like]

        if date_from:
            conditions.append("date >= ?")
            sql_params.append(date_from)
        if date_to:
            conditions.append("date <= ?")
            sql_params.append(date_to)

        where = " AND ".join(conditions)
        rows = conn.execute(
            f"SELECT * FROM conversation_summaries WHERE {where} ORDER BY created_at DESC LIMIT ?",
            sql_params + [limit],
        ).fetchall()

        for row in rows:
            r = dict(row)
            results.append({
                "type": "conversation_summary",
                "date": r.get("date", ""),
                "summary": r.get("summary", "")[:500],
                "topics": r.get("topics", "[]"),
                "customers_mentioned": r.get("customers_mentioned", "[]"),
                "key_decisions": r.get("key_decisions", "[]"),
                "message_count": r.get("message_count", 0),
            })
        conn.close()
    except Exception as e:
        logger.warning(f"search_conversations: summary search failed: {e}")

    # 3. Search chat messages in the main chat backup database
    try:
        from app.database import DATABASE_URL
        import sqlite3 as _sqlite3

        # Only search if using SQLite (sync access)
        if "sqlite" in DATABASE_URL:
            db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.path.expanduser("~/empire-repo/backend"), db_path)
            if os.path.exists(db_path):
                cconn = _sqlite3.connect(db_path)
                cconn.row_factory = _sqlite3.Row

                msg_conditions = ["m.content LIKE ?"]
                msg_params = [q_like]

                if channel:
                    msg_conditions.append("s.source LIKE ?")
                    msg_params.append(f"%{channel}%")
                if date_from:
                    msg_conditions.append("m.created_at >= ?")
                    msg_params.append(date_from)
                if date_to:
                    msg_conditions.append("m.created_at <= ?")
                    msg_params.append(date_to + "T23:59:59")

                msg_where = " AND ".join(msg_conditions)
                msg_rows = cconn.execute(
                    f"""SELECT m.content, m.role, m.created_at, s.title, s.source, s.agent_name
                        FROM chat_messages m
                        JOIN chat_sessions s ON m.session_id = s.id
                        WHERE {msg_where}
                        ORDER BY m.created_at DESC LIMIT ?""",
                    msg_params + [limit],
                ).fetchall()

                for row in msg_rows:
                    r = dict(row)
                    results.append({
                        "type": "chat_message",
                        "role": r.get("role", ""),
                        "content": r.get("content", "")[:500],
                        "channel": r.get("source", ""),
                        "agent": r.get("agent_name", ""),
                        "session_title": r.get("title", ""),
                        "date": (r.get("created_at", "") or "")[:10],
                    })
                cconn.close()
    except Exception as e:
        logger.warning(f"search_conversations: chat backup search failed: {e}")

    # Channel filter for memory/summary results if requested
    if channel:
        filtered = []
        for r in results:
            src = (r.get("source", "") + r.get("channel", "")).lower()
            if r["type"] == "chat_message":
                filtered.append(r)  # already filtered by SQL
            elif channel in src or not src:
                filtered.append(r)
        results = filtered

    # Sort by date descending
    results.sort(key=lambda x: x.get("date", ""), reverse=True)
    results = results[:limit]

    duration = int((_time.time() - start) * 1000)
    log_execution("search_conversations", params, {"count": len(results)}, access_level=1, desk=desk, success=True, duration_ms=duration)
    return ToolResult(tool="search_conversations", success=True, result={
        "query": query,
        "count": len(results),
        "results": results,
    })
