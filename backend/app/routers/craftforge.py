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
