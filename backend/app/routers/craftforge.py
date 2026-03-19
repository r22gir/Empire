"""
CraftForge — CNC & 3D Print Business Router.
Full QuickBooks-level business management + CNC-specific features.
Stores data as JSON files (same pattern as quotes router).
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
import json
import uuid
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["craftforge"])

# ── Data directories ──────────────────────────────────────────
DATA_DIR = os.path.expanduser("~/empire-repo/backend/data/craftforge")
DESIGNS_DIR = os.path.join(DATA_DIR, "designs")
JOBS_DIR = os.path.join(DATA_DIR, "jobs")
INVENTORY_DIR = os.path.join(DATA_DIR, "inventory")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")

for d in [DESIGNS_DIR, JOBS_DIR, INVENTORY_DIR, TEMPLATES_DIR]:
    os.makedirs(d, exist_ok=True)

COUNTER_FILE = os.path.join(DATA_DIR, "_counter.json")


def _next_number(prefix: str) -> str:
    """Generate next sequential number: CF-2026-001, JOB-2026-001, etc."""
    try:
        with open(COUNTER_FILE) as f:
            counters = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        counters = {}
    year = datetime.now().strftime("%Y")
    key = f"{prefix}_{year}"
    counters[key] = counters.get(key, 0) + 1
    with open(COUNTER_FILE, "w") as f:
        json.dump(counters, f)
    return f"{prefix}-{year}-{counters[key]:03d}"


# ── Schemas ──────────────────────────────────────────────────

class MaterialItem(BaseModel):
    name: str
    type: str = "wood"  # wood, hardware, finishing, consumable, filament
    quantity: float = 1.0
    unit: str = "ea"  # ea, sqft, bdft, lnft, ml, kg
    cost_per_unit: float = 0.0
    total: float = 0.0
    supplier: Optional[str] = None
    sku: Optional[str] = None


class CNCJob(BaseModel):
    machine: str = "x-carve"  # x-carve, elegoo-saturn, manual
    operation: str = "profile"  # profile, pocket, vcarve, engrave, 3d-relief, 3d-print
    tool: Optional[str] = None  # 1/4" endmill, 60deg v-bit, etc.
    material: Optional[str] = None
    thickness: Optional[float] = None
    estimated_time_min: float = 0.0
    feed_rate: Optional[float] = None
    spindle_speed: Optional[float] = None
    passes: int = 1
    notes: Optional[str] = None


class DesignCreate(BaseModel):
    # Customer info
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None

    # Design info
    name: str
    description: Optional[str] = None
    category: str = "cornice"  # cornice, valance, headboard, cabinet-door, sign, furniture, custom
    style: Optional[str] = None  # farmhouse, modern, art-deco, traditional, geometric, ornate

    # Dimensions
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    unit: str = "in"

    # Materials
    primary_material: str = "MDF"  # MDF, plywood, hardwood, acrylic, foam
    materials: list[MaterialItem] = Field(default_factory=list)

    # CNC operations
    cnc_jobs: list[CNCJob] = Field(default_factory=list)

    # Files (paths or URLs)
    svg_file: Optional[str] = None
    dxf_file: Optional[str] = None
    gcode_file: Optional[str] = None
    stl_file: Optional[str] = None
    preview_image: Optional[str] = None
    photos: list[str] = Field(default_factory=list)

    # Financials
    material_cost: float = 0.0
    cnc_time_cost: float = 0.0
    labor_cost: float = 0.0
    overhead: float = 0.0
    subtotal: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    total: float = 0.0
    deposit_percent: float = 50.0
    margin_percent: float = 40.0

    # Linked quote (if from Empire Workroom)
    linked_quote_id: Optional[str] = None
    linked_quote_number: Optional[str] = None

    notes: Optional[str] = None


class DesignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    style: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    primary_material: Optional[str] = None
    materials: Optional[list[MaterialItem]] = None
    cnc_jobs: Optional[list[CNCJob]] = None
    svg_file: Optional[str] = None
    dxf_file: Optional[str] = None
    gcode_file: Optional[str] = None
    stl_file: Optional[str] = None
    preview_image: Optional[str] = None
    photos: Optional[list[str]] = None
    material_cost: Optional[float] = None
    cnc_time_cost: Optional[float] = None
    labor_cost: Optional[float] = None
    subtotal: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    total: Optional[float] = None
    notes: Optional[str] = None
    linked_quote_id: Optional[str] = None
    linked_quote_number: Optional[str] = None


class JobCreate(BaseModel):
    """Production job — tracks a design through the shop."""
    design_id: str
    design_number: Optional[str] = None
    customer_name: str
    description: Optional[str] = None
    priority: str = "normal"  # low, normal, high, urgent
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None
    machine: str = "x-carve"
    estimated_time_min: float = 0.0
    material_list: list[MaterialItem] = Field(default_factory=list)
    notes: Optional[str] = None


class JobUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    actual_time_min: Optional[float] = None
    notes: Optional[str] = None
    completed_at: Optional[str] = None


class InventoryItem(BaseModel):
    name: str
    type: str = "wood"  # wood, hardware, finishing, consumable, filament, tool
    sku: Optional[str] = None
    quantity: float = 0.0
    unit: str = "ea"
    cost_per_unit: float = 0.0
    reorder_point: float = 0.0
    supplier: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


# ── Helper functions ─────────────────────────────────────────

def _save(directory: str, id: str, data: dict):
    with open(os.path.join(directory, f"{id}.json"), "w") as f:
        json.dump(data, f, indent=2, default=str)


def _load(directory: str, id: str) -> dict:
    path = os.path.join(directory, f"{id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Not found")
    with open(path) as f:
        return json.load(f)


def _list_all(directory: str) -> list[dict]:
    items = []
    for fname in os.listdir(directory):
        if fname.endswith(".json") and not fname.startswith("_"):
            with open(os.path.join(directory, fname)) as f:
                items.append(json.load(f))
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


def _delete(directory: str, id: str):
    path = os.path.join(directory, f"{id}.json")
    if os.path.exists(path):
        os.remove(path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DESIGNS — CNC/3D print design CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/designs")
async def create_design(design: DesignCreate):
    design_id = str(uuid.uuid4())
    design_number = _next_number("CF")
    data = {
        "id": design_id,
        "design_number": design_number,
        "status": "concept",  # concept, designing, ready, cutting, finishing, complete
        **design.model_dump(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    # Auto-compute financials
    data["material_cost"] = sum(m.get("total", 0) if isinstance(m, dict) else m.total for m in (design.materials or []))
    data["cnc_time_cost"] = sum(
        (j.get("estimated_time_min", 0) if isinstance(j, dict) else j.estimated_time_min) * 1.50  # $1.50/min CNC time
        for j in (design.cnc_jobs or [])
    )
    data["subtotal"] = data["material_cost"] + data["cnc_time_cost"] + data["labor_cost"]
    data["tax_amount"] = data["subtotal"] * data["tax_rate"]
    data["total"] = data["subtotal"] + data["tax_amount"] - data["discount_amount"]

    _save(DESIGNS_DIR, design_id, data)
    return data


@router.get("/designs")
async def list_designs(
    status: Optional[str] = None,
    category: Optional[str] = None,
    customer: Optional[str] = None,
    limit: int = 50,
):
    designs = _list_all(DESIGNS_DIR)
    if status:
        designs = [d for d in designs if d.get("status") == status]
    if category:
        designs = [d for d in designs if d.get("category") == category]
    if customer:
        designs = [d for d in designs if customer.lower() in d.get("customer_name", "").lower()]
    return {"designs": designs[:limit], "total": len(designs)}


@router.get("/designs/{design_id}")
async def get_design(design_id: str):
    return _load(DESIGNS_DIR, design_id)


@router.patch("/designs/{design_id}")
async def update_design(design_id: str, update: DesignUpdate):
    data = _load(DESIGNS_DIR, design_id)
    for key, val in update.model_dump(exclude_unset=True).items():
        if val is not None:
            data[key] = val if not isinstance(val, list) else [
                v.model_dump() if hasattr(v, "model_dump") else v for v in val
            ]
    data["updated_at"] = datetime.utcnow().isoformat()
    _save(DESIGNS_DIR, design_id, data)
    return data


@router.delete("/designs/{design_id}")
async def delete_design(design_id: str):
    _delete(DESIGNS_DIR, design_id)
    return {"deleted": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  JOBS — Production tracking (QB-level job costing)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/jobs")
async def create_job(job: JobCreate):
    job_id = str(uuid.uuid4())
    job_number = _next_number("JOB")
    data = {
        "id": job_id,
        "job_number": job_number,
        "status": "queued",  # queued, cutting, printing, sanding, finishing, assembly, complete, shipped
        **job.model_dump(),
        "actual_time_min": 0.0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
    }
    _save(JOBS_DIR, job_id, data)
    return data


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    machine: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
):
    jobs = _list_all(JOBS_DIR)
    if status:
        jobs = [j for j in jobs if j.get("status") == status]
    if machine:
        jobs = [j for j in jobs if j.get("machine") == machine]
    if priority:
        jobs = [j for j in jobs if j.get("priority") == priority]
    return {"jobs": jobs[:limit], "total": len(jobs)}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    return _load(JOBS_DIR, job_id)


@router.patch("/jobs/{job_id}")
async def update_job(job_id: str, update: JobUpdate):
    data = _load(JOBS_DIR, job_id)
    for key, val in update.model_dump(exclude_unset=True).items():
        if val is not None:
            data[key] = val
    if update.status == "cutting" or update.status == "printing":
        data["started_at"] = data.get("started_at") or datetime.utcnow().isoformat()
    if update.status == "complete":
        data["completed_at"] = datetime.utcnow().isoformat()
    data["updated_at"] = datetime.utcnow().isoformat()
    _save(JOBS_DIR, job_id, data)
    return data


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    _delete(JOBS_DIR, job_id)
    return {"deleted": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  INVENTORY — Materials, tools, consumables (QB-level)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/inventory")
async def add_inventory(item: InventoryItem):
    item_id = str(uuid.uuid4())
    data = {
        "id": item_id,
        **item.model_dump(),
        "total_value": item.quantity * item.cost_per_unit,
        "low_stock": item.quantity <= item.reorder_point,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    _save(INVENTORY_DIR, item_id, data)
    return data


@router.get("/inventory")
async def list_inventory(
    type: Optional[str] = None,
    low_stock: Optional[bool] = None,
):
    items = _list_all(INVENTORY_DIR)
    if type:
        items = [i for i in items if i.get("type") == type]
    if low_stock:
        items = [i for i in items if i.get("low_stock")]
    total_value = sum(i.get("total_value", 0) for i in items)
    return {"items": items, "total": len(items), "total_value": total_value}


@router.patch("/inventory/{item_id}")
async def update_inventory(item_id: str, update: dict):
    data = _load(INVENTORY_DIR, item_id)
    data.update(update)
    data["total_value"] = data.get("quantity", 0) * data.get("cost_per_unit", 0)
    data["low_stock"] = data.get("quantity", 0) <= data.get("reorder_point", 0)
    data["updated_at"] = datetime.utcnow().isoformat()
    _save(INVENTORY_DIR, item_id, data)
    return data


@router.delete("/inventory/{item_id}")
async def delete_inventory(item_id: str):
    _delete(INVENTORY_DIR, item_id)
    return {"deleted": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DASHBOARD — KPIs and stats (QB-level reporting)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/dashboard")
async def dashboard():
    designs = _list_all(DESIGNS_DIR)
    jobs = _list_all(JOBS_DIR)
    inventory = _list_all(INVENTORY_DIR)

    # Revenue / pipeline
    pipeline = sum(d.get("total", 0) for d in designs if d.get("status") not in ("complete", "cancelled"))
    revenue = sum(d.get("total", 0) for d in designs if d.get("status") == "complete")

    # Job stats
    active_jobs = [j for j in jobs if j.get("status") not in ("complete", "cancelled")]
    queued = len([j for j in jobs if j.get("status") == "queued"])
    in_progress = len([j for j in jobs if j.get("status") in ("cutting", "printing", "sanding", "finishing", "assembly")])
    completed = len([j for j in jobs if j.get("status") == "complete"])

    # Inventory
    low_stock_items = [i for i in inventory if i.get("low_stock")]
    inventory_value = sum(i.get("total_value", 0) for i in inventory)

    # Designs by status
    by_status = {}
    for d in designs:
        s = d.get("status", "concept")
        by_status[s] = by_status.get(s, 0) + 1

    # Designs by category
    by_category = {}
    for d in designs:
        c = d.get("category", "custom")
        by_category[c] = by_category.get(c, 0) + 1

    return {
        "pipeline": pipeline,
        "revenue": revenue,
        "total_designs": len(designs),
        "designs_by_status": by_status,
        "designs_by_category": by_category,
        "jobs": {
            "total": len(jobs),
            "queued": queued,
            "in_progress": in_progress,
            "completed": completed,
            "active": len(active_jobs),
        },
        "inventory": {
            "total_items": len(inventory),
            "low_stock": len(low_stock_items),
            "total_value": inventory_value,
            "low_stock_items": [i.get("name") for i in low_stock_items],
        },
        "machines": {
            "x-carve": {"status": "idle", "queued_jobs": len([j for j in active_jobs if j.get("machine") == "x-carve"])},
            "elegoo-saturn": {"status": "idle", "queued_jobs": len([j for j in active_jobs if j.get("machine") == "elegoo-saturn"])},
        },
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CUSTOMERS — CRM (mirrors quote system customer data)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/customers")
async def list_customers():
    """Extract unique customers from all designs."""
    designs = _list_all(DESIGNS_DIR)
    customers = {}
    for d in designs:
        name = d.get("customer_name", "")
        if name and name not in customers:
            customers[name] = {
                "name": name,
                "email": d.get("customer_email"),
                "phone": d.get("customer_phone"),
                "address": d.get("customer_address"),
                "total_designs": 0,
                "total_revenue": 0.0,
                "last_order": None,
            }
        if name in customers:
            customers[name]["total_designs"] += 1
            customers[name]["total_revenue"] += d.get("total", 0)
            created = d.get("created_at", "")
            if not customers[name]["last_order"] or created > customers[name]["last_order"]:
                customers[name]["last_order"] = created
    return {"customers": list(customers.values()), "total": len(customers)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PDF — Generate professional quote PDF for a design
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_woodcraft_config() -> dict:
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "woodcraft_business.json")
    try:
        with open(cfg_path) as f:
            return json.load(f)
    except Exception:
        return {"business_name": "WoodCraft by Empire", "business_email": "", "business_phone": "", "business_address": "", "business_website": ""}


@router.post("/designs/{design_id}/pdf")
async def generate_design_pdf(design_id: str):
    """Generate a professional PDF quote for a CraftForge design."""
    design = _load(DESIGNS_DIR, design_id)
    cfg = _load_woodcraft_config()

    biz_name = cfg.get("business_name", "WoodCraft by Empire")
    biz_tagline = cfg.get("business_tagline", "CNC & Custom Fabrication")
    biz_phone = cfg.get("business_phone", "")
    biz_email = cfg.get("business_email", "")
    biz_address = cfg.get("business_address", "")
    biz_website = cfg.get("business_website", "")
    tax_rate = cfg.get("tax_rate", 0.06)

    biz_contact_lines = [l for l in [biz_phone, biz_email, biz_address, biz_website] if l]
    biz_contact_html = "<br>".join(f'<span style="font-size:0.82em;color:#555">{l}</span>' for l in biz_contact_lines)

    design_number = design.get("design_number", "CF-000")
    created_date = design.get("created_at", "")[:10]
    valid_days = cfg.get("quote_valid_days", 30)
    try:
        expires = (datetime.fromisoformat(design["created_at"]) + timedelta(days=valid_days)).strftime("%Y-%m-%d")
    except Exception:
        expires = ""

    # Materials table
    materials = design.get("materials", [])
    mat_html = ""
    for m in materials:
        name = m.get("name", "") if isinstance(m, dict) else getattr(m, "name", "")
        qty = m.get("quantity", 0) if isinstance(m, dict) else getattr(m, "quantity", 0)
        unit = m.get("unit", "ea") if isinstance(m, dict) else getattr(m, "unit", "ea")
        cost = m.get("cost_per_unit", 0) if isinstance(m, dict) else getattr(m, "cost_per_unit", 0)
        total = qty * cost
        if name:
            mat_html += f"""<tr>
                <td style="padding:6px 8px;border-bottom:1px solid #eee">{name}</td>
                <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{qty} {unit}</td>
                <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">${cost:,.2f}</td>
                <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;font-weight:600">${total:,.2f}</td>
            </tr>"""

    # CNC operations table
    cnc_jobs = design.get("cnc_jobs", [])
    cnc_rate = cfg.get("cnc_rate_per_min", 1.50)
    cnc_html = ""
    for j in cnc_jobs:
        machine = j.get("machine", "") if isinstance(j, dict) else getattr(j, "machine", "")
        op = j.get("operation", "") if isinstance(j, dict) else getattr(j, "operation", "")
        tool = j.get("tool", "") if isinstance(j, dict) else getattr(j, "tool", "")
        mins = j.get("estimated_time_min", 0) if isinstance(j, dict) else getattr(j, "estimated_time_min", 0)
        cost = mins * cnc_rate
        if mins > 0:
            cnc_html += f"""<tr>
                <td style="padding:6px 8px;border-bottom:1px solid #eee">{machine}</td>
                <td style="padding:6px 8px;border-bottom:1px solid #eee">{op.replace('-', ' ')}</td>
                <td style="padding:6px 8px;border-bottom:1px solid #eee">{tool or '--'}</td>
                <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{mins} min</td>
                <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;font-weight:600">${cost:,.2f}</td>
            </tr>"""

    # Dimensions
    dims = ""
    if design.get("width") or design.get("height") or design.get("depth"):
        dim_unit = design.get("unit", "in")
        parts = []
        if design.get("width"): parts.append(f'{design["width"]}{dim_unit} W')
        if design.get("height"): parts.append(f'{design["height"]}{dim_unit} H')
        if design.get("depth"): parts.append(f'{design["depth"]}{dim_unit} D')
        dims = f'<p style="margin:4px 0;font-size:0.88em;color:#555"><strong>Dimensions:</strong> {" × ".join(parts)}</p>'

    # Costs
    material_cost = design.get("material_cost", 0)
    cnc_time_cost = design.get("cnc_time_cost", 0)
    labor_cost = design.get("labor_cost", 0)
    overhead = design.get("overhead", 0)
    subtotal = design.get("subtotal", 0)
    margin_pct = design.get("margin_percent", 40)
    margin_amount = subtotal * (margin_pct / 100)
    total = design.get("total", 0) or (subtotal + margin_amount)
    tax_amount = total * tax_rate
    grand_total = total + tax_amount
    deposit_pct = design.get("deposit_percent", 50)
    deposit_amount = grand_total * (deposit_pct / 100)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{design_number}</title>
<style>
  @page {{ size: letter; margin: 0.5in 0.6in; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #222; max-width: 800px; margin: 0 auto; padding: 0; font-size: 12px; line-height: 1.45; }}
  h1 {{ color: #1a1a2e; margin: 0; font-size: 28px; letter-spacing: -0.5px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }}
  th {{ background: #3d2e1a; color: #d4a636; padding: 8px 6px; text-align: left; font-size: 0.78em; text-transform: uppercase; letter-spacing: 0.5px; }}
</style></head><body>

<!-- HEADER -->
<div style="border-bottom:3px solid #d4a636;padding-bottom:14px;margin-bottom:16px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h1>{biz_name}</h1>
      <p style="margin:4px 0 0;color:#888;font-size:0.85em">{biz_tagline}</p>
      <p style="margin:6px 0 0;line-height:1.6">{biz_contact_html}</p>
    </div>
    <div style="text-align:right;padding-top:4px">
      <div style="background:#3d2e1a;color:#d4a636;padding:8px 16px;border-radius:6px;font-weight:700;font-size:1.1em;letter-spacing:1px;display:inline-block;margin-bottom:8px">ESTIMATE</div>
      <p style="margin:3px 0;color:#333;font-size:0.9em;font-weight:600">{design_number}</p>
      <p style="margin:3px 0;color:#666;font-size:0.82em">Date: {created_date}</p>
      <p style="margin:3px 0;color:#666;font-size:0.82em">Valid until: {expires}</p>
    </div>
  </div>
</div>

<!-- CLIENT -->
<div style="display:flex;gap:16px;margin-bottom:16px">
  <div style="flex:1;padding:14px 18px;background:#f8f8f8;border-radius:8px;border:1px solid #eee">
    <p style="margin:0 0 6px;font-size:0.75em;text-transform:uppercase;letter-spacing:0.5px;color:#999;font-weight:600">Prepared For</p>
    <p style="margin:0;font-weight:700;font-size:1.05em;color:#1a1a2e">{design.get('customer_name', 'Customer')}</p>
    {f'<p style="margin:3px 0 0;color:#555;font-size:0.88em">{design["customer_email"]}</p>' if design.get('customer_email') else ''}
    {f'<p style="margin:2px 0 0;color:#555;font-size:0.88em">{design["customer_phone"]}</p>' if design.get('customer_phone') else ''}
  </div>
  <div style="flex:1;padding:14px 18px;background:#fffcf0;border-radius:8px;border:1px solid #f0e6c0">
    <p style="margin:0 0 6px;font-size:0.75em;text-transform:uppercase;letter-spacing:0.5px;color:#999;font-weight:600">Project</p>
    <p style="margin:0;font-weight:600;color:#1a1a2e">{design.get('name', 'Custom Project')}</p>
    <p style="margin:4px 0 0;color:#777;font-size:0.82em">{design.get('category', '').replace('-', ' ').title()} &middot; {design.get('style', '').replace('-', ' ').title()}</p>
    {dims}
    <p style="margin:4px 0 0;color:#777;font-size:0.82em">Primary Material: {design.get('primary_material', 'MDF')}</p>
  </div>
</div>

{f'<p style="color:#555;margin-bottom:16px">{design["description"]}</p>' if design.get('description') else ''}

<!-- MATERIALS -->
{'<div style="margin-bottom:16px"><h3 style="font-size:0.9em;color:#3d2e1a;margin:0 0 8px;text-transform:uppercase;letter-spacing:0.5px">Materials</h3><table><thead><tr><th>Material</th><th style="text-align:center">Qty</th><th style="text-align:right">Unit Cost</th><th style="text-align:right">Total</th></tr></thead><tbody>' + mat_html + f'</tbody></table><div style="text-align:right;font-weight:700;color:#3d2e1a;font-size:0.9em">Materials: ${material_cost:,.2f}</div></div>' if mat_html else ''}

<!-- CNC OPERATIONS -->
{'<div style="margin-bottom:16px"><h3 style="font-size:0.9em;color:#3d2e1a;margin:0 0 8px;text-transform:uppercase;letter-spacing:0.5px">CNC Operations</h3><table><thead><tr><th>Machine</th><th>Operation</th><th>Tool</th><th style="text-align:center">Time</th><th style="text-align:right">Cost</th></tr></thead><tbody>' + cnc_html + f'</tbody></table><div style="text-align:right;font-size:0.8em;color:#888">@ ${cnc_rate:.2f}/min</div><div style="text-align:right;font-weight:700;color:#3d2e1a;font-size:0.9em">CNC Total: ${cnc_time_cost:,.2f}</div></div>' if cnc_html else ''}

<!-- COST BREAKDOWN -->
<div style="margin-top:20px;padding:16px 20px;background:#f8f8f8;border-radius:8px;border:1px solid #eee">
  <h3 style="font-size:0.9em;color:#3d2e1a;margin:0 0 12px;text-transform:uppercase;letter-spacing:0.5px">Cost Summary</h3>
  <table>
    <tbody>
      {'<tr><td style="padding:4px 8px;color:#666">Materials</td><td style="padding:4px 8px;text-align:right;color:#666">$' + f'{material_cost:,.2f}</td></tr>' if material_cost else ''}
      {'<tr><td style="padding:4px 8px;color:#666">CNC Time</td><td style="padding:4px 8px;text-align:right;color:#666">$' + f'{cnc_time_cost:,.2f}</td></tr>' if cnc_time_cost else ''}
      {'<tr><td style="padding:4px 8px;color:#666">Labor</td><td style="padding:4px 8px;text-align:right;color:#666">$' + f'{labor_cost:,.2f}</td></tr>' if labor_cost else ''}
      {'<tr><td style="padding:4px 8px;color:#666">Overhead</td><td style="padding:4px 8px;text-align:right;color:#666">$' + f'{overhead:,.2f}</td></tr>' if overhead else ''}
      <tr><td style="padding:4px 8px;color:#666">Subtotal</td><td style="padding:4px 8px;text-align:right;color:#666">${subtotal:,.2f}</td></tr>
      {'<tr><td style="padding:4px 8px;color:#666">Margin (' + f'{margin_pct}%)</td><td style="padding:4px 8px;text-align:right;color:#666">${margin_amount:,.2f}</td></tr>' if margin_amount else ''}
      <tr><td style="padding:4px 8px;color:#666">Tax ({tax_rate*100:.1f}%)</td><td style="padding:4px 8px;text-align:right;color:#666">${tax_amount:,.2f}</td></tr>
      <tr style="border-top:3px solid #d4a636"><td style="padding:12px 8px;font-weight:700;font-size:1.1em;color:#1a1a2e">Total</td><td style="padding:12px 8px;text-align:right;font-weight:700;font-size:1.2em;color:#d4a636">${grand_total:,.2f}</td></tr>
      {'<tr><td style="padding:4px 8px;font-weight:600;color:#2563eb">Deposit Due (' + f'{deposit_pct}%)</td><td style="padding:4px 8px;text-align:right;font-weight:600;color:#2563eb">${deposit_amount:,.2f}</td></tr>' if deposit_pct else ''}
    </tbody>
  </table>
</div>

{f'<div style="margin-top:12px;padding:12px 16px;background:#f8f8f8;border-radius:8px;font-size:0.88em;color:#666"><strong>Notes:</strong> {design["notes"]}</div>' if design.get('notes') else ''}

<!-- ACCEPTANCE -->
<div style="margin-top:36px;padding:24px 20px;border:2px solid #d4a636;border-radius:10px;page-break-inside:avoid">
  <p style="margin:0 0 12px;font-size:0.78em;text-transform:uppercase;letter-spacing:0.5px;color:#d4a636;font-weight:700">Acceptance</p>
  <p style="margin:0 0 20px;font-size:0.85em;color:#555">By signing below, I accept this estimate and authorize {biz_name} to proceed with the work described above.</p>
  <div style="display:flex;gap:40px;margin-top:16px">
    <div style="flex:1"><div style="border-bottom:1px solid #333;height:40px"></div><p style="margin:6px 0 0;font-size:0.78em;color:#888">Client Signature</p></div>
    <div style="width:160px"><div style="border-bottom:1px solid #333;height:40px"></div><p style="margin:6px 0 0;font-size:0.78em;color:#888">Date</p></div>
  </div>
</div>

<!-- FOOTER -->
<div style="margin-top:28px;padding-top:12px;border-top:1px solid #eee;text-align:center">
  <p style="margin:0;color:#aaa;font-size:0.72em">{biz_name} &middot; {biz_tagline}</p>
  <p style="margin:2px 0 0;color:#ccc;font-size:0.65em">Estimate {design_number} &middot; Generated {created_date}</p>
</div>
</body></html>"""

    try:
        from weasyprint import HTML as WeasyHTML
        pdf_bytes = WeasyHTML(string=html).write_pdf()
    except Exception as e:
        logger.error(f"WeasyPrint PDF generation failed: {e}")
        raise HTTPException(500, f"PDF generation failed: {str(e)}")

    pdf_dir = os.path.join(DATA_DIR, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"{design_number}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    logger.info(f"CraftForge PDF: {design_number} ({len(pdf_bytes)} bytes)")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{design_number}.pdf"'},
    )


@router.get("/designs/{design_id}/pdf")
async def download_design_pdf(design_id: str):
    """Download existing PDF or generate on the fly."""
    design = _load(DESIGNS_DIR, design_id)
    design_number = design.get("design_number", design_id)
    pdf_path = os.path.join(DATA_DIR, "pdf", f"{design_number}.pdf")
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{design_number}.pdf"'},
        )
    return await generate_design_pdf(design_id)


class SendDesignRequest(BaseModel):
    to_email: Optional[str] = None


@router.post("/designs/{design_id}/send")
async def send_design_quote(design_id: str, body: Optional[SendDesignRequest] = None):
    """Generate PDF and email it to the customer."""
    design = _load(DESIGNS_DIR, design_id)
    to_email = (body.to_email if body and body.to_email else None) or design.get("customer_email", "")

    if not to_email:
        raise HTTPException(400, "No email address — provide to_email or set customer_email on the design")

    # Generate PDF
    pdf_response = await generate_design_pdf(design_id)
    pdf_bytes = pdf_response.body if hasattr(pdf_response, "body") else None
    if not pdf_bytes:
        design_number = design.get("design_number", design_id)
        pdf_path = os.path.join(DATA_DIR, "pdf", f"{design_number}.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

    # Send email
    cfg = _load_woodcraft_config()
    biz_name = cfg.get("business_name", "WoodCraft by Empire")
    design_number = design.get("design_number", "CF-000")
    customer_name = design.get("customer_name", "Valued Customer")
    project_name = design.get("name", "Custom Project")
    total = design.get("total", 0)

    html_body = f"""
    <div style="font-family:'Helvetica Neue',Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
      <div style="border-bottom:3px solid #d4a636;padding-bottom:12px;margin-bottom:20px">
        <h1 style="margin:0;color:#3d2e1a;font-size:24px">{biz_name}</h1>
        <p style="margin:4px 0 0;color:#888;font-size:13px">{cfg.get('business_tagline', 'CNC & Custom Fabrication')}</p>
      </div>
      <p style="font-size:15px;color:#333">Hi {customer_name},</p>
      <p style="font-size:14px;color:#555;line-height:1.6">
        Thank you for your interest! Please find attached your estimate for <strong>{project_name}</strong>.
      </p>
      <div style="margin:20px 0;padding:16px;background:#fffcf0;border:1px solid #f0e6c0;border-radius:8px;text-align:center">
        <p style="margin:0;font-size:13px;color:#888">Estimate {design_number}</p>
        <p style="margin:8px 0 0;font-size:24px;font-weight:700;color:#d4a636">${total:,.2f}</p>
      </div>
      <p style="font-size:14px;color:#555">
        If you have any questions or would like to proceed, just reply to this email or give us a call.
      </p>
      <p style="font-size:14px;color:#333;font-weight:600">Best regards,<br>{biz_name}</p>
    </div>"""

    email_sent = False
    try:
        import base64 as b64
        sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")
        sendgrid_from = os.environ.get("SENDGRID_FROM_EMAIL", cfg.get("business_email", ""))

        if pdf_bytes and sendgrid_key:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

            message = Mail(
                from_email=sendgrid_from,
                to_emails=to_email,
                subject=f"Your Estimate from {biz_name} — {design_number}",
                html_content=html_body,
            )
            attachment = Attachment(
                FileContent(b64.b64encode(pdf_bytes).decode()),
                FileName(f"{design_number}.pdf"),
                FileType("application/pdf"),
                Disposition("attachment"),
            )
            message.attachment = attachment
            sg = SendGridAPIClient(sendgrid_key)
            response = sg.send(message)
            email_sent = response.status_code < 300
        else:
            from app.services.email.sender import send_email
            email_sent = await send_email(to_email, f"Your Estimate from {biz_name} — {design_number}", html_body)
    except Exception as e:
        logger.error(f"Failed to send CraftForge quote email: {e}")

    # Mark as sent
    design["status"] = "sent"
    design["sent_at"] = datetime.utcnow().isoformat()
    design["sent_to"] = to_email
    design["updated_at"] = datetime.utcnow().isoformat()
    _save(DESIGNS_DIR, design_id, design)

    return {"sent": True, "email_sent": email_sent, "to": to_email, "design_number": design_number}
