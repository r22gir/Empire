"""
LLC Factory — One-stop business services platform.
Covers LLC formation, apostille, notary, registered agent, EIN, and more
for the DC / MD / VA corridor.

JSON file storage in ~/empire-repo/backend/data/llcfactory/.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import json
import uuid
import os
import logging
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llcfactory", tags=["llcfactory"])

# ── Storage ──────────────────────────────────────────────────────────
BASE_DIR = os.path.expanduser("~/empire-repo/backend/data/llcfactory")
ORDERS_DIR = os.path.join(BASE_DIR, "orders")
CUSTOMERS_DIR = os.path.join(BASE_DIR, "customers")
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")
SERVICES_FILE = os.path.join(BASE_DIR, "services.json")
PACKAGES_FILE = os.path.join(BASE_DIR, "packages.json")

for _d in (BASE_DIR, ORDERS_DIR, CUSTOMERS_DIR, DOCUMENTS_DIR):
    os.makedirs(_d, exist_ok=True)


# ── Pydantic Schemas ────────────────────────────────────────────────

class Member(BaseModel):
    name: str
    role: str = "member"  # member | manager
    ownership_pct: float = 100.0


class OrderCreate(BaseModel):
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_id: Optional[str] = None
    package: Optional[str] = None  # starter | professional | empire | custom
    services: List[str] = Field(default_factory=list)  # service IDs
    state: str = "DC"  # DC | MD | VA
    business_name: str = ""
    business_type: str = "llc"  # llc | corp | nonprofit | dba
    members: List[Member] = Field(default_factory=list)
    notes: str = ""
    payment_method: Optional[str] = None


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    paid: Optional[bool] = None
    payment_method: Optional[str] = None
    documents: Optional[List[dict]] = None


class CustomerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class QuoteRequest(BaseModel):
    services: List[str] = Field(default_factory=list)
    package: Optional[str] = None
    state: str = "DC"


class NameCheckRequest(BaseModel):
    name: str
    state: str = "DC"
    entity_type: str = "llc"


class GenerateOARequest(BaseModel):
    business_name: str
    state: str = "DC"
    members: List[Member] = Field(default_factory=list)
    business_purpose: str = "any lawful purpose"
    management_type: str = "member-managed"
    order_id: Optional[str] = None
    customer_id: Optional[str] = None


class GenerateDocsRequest(BaseModel):
    order_id: str
    doc_types: List[str] = Field(default_factory=list)  # articles, oa, ein_ss4, consent


# ── Seed Data ────────────────────────────────────────────────────────

SERVICES_SEED: list[dict] = [
    # A. BUSINESS FORMATION
    {"id": "llc-dc",          "category": "Business Formation", "name": "LLC Formation DC",              "state_fee": 99,  "service_fee": 149, "turnaround": "5 business days",   "description": "Form a domestic LLC in the District of Columbia."},
    {"id": "llc-md",          "category": "Business Formation", "name": "LLC Formation MD",              "state_fee": 100, "service_fee": 149, "turnaround": "5-7 business days",  "description": "Form a domestic LLC in Maryland."},
    {"id": "llc-va",          "category": "Business Formation", "name": "LLC Formation VA",              "state_fee": 100, "service_fee": 149, "turnaround": "2-5 business days",  "description": "Form a domestic LLC in Virginia."},
    {"id": "corp-formation",  "category": "Business Formation", "name": "Corporation Formation",          "state_fee": 0,   "service_fee": 199, "turnaround": "5-10 business days", "description": "Form a Corporation (C-Corp or S-Corp). State fees vary."},
    {"id": "nonprofit-501c3", "category": "Business Formation", "name": "Nonprofit 501(c)(3)",            "state_fee": 0,   "service_fee": 299, "turnaround": "2-6 weeks",          "description": "Form a nonprofit and prepare 501(c)(3) application. State fees vary."},
    {"id": "dba",             "category": "Business Formation", "name": "DBA / Trade Name",               "state_fee": 0,   "service_fee": 79,  "turnaround": "3-5 business days",  "description": "Register a 'Doing Business As' or trade name. State fees vary."},
    {"id": "foreign-reg",     "category": "Business Formation", "name": "Foreign Entity Registration",    "state_fee": 0,   "service_fee": 149, "turnaround": "5-10 business days", "description": "Register an out-of-state entity to do business in DC/MD/VA. State fees vary."},
    {"id": "biz-license",     "category": "Business Formation", "name": "Business License Application",   "state_fee": 0,   "service_fee": 99,  "turnaround": "varies",            "description": "Apply for required business licenses in your jurisdiction."},
    {"id": "annual-report",   "category": "Business Formation", "name": "Annual Report Filing",           "state_fee": 0,   "service_fee": 49,  "turnaround": "1-3 business days",  "description": "File annual/biennial reports. State fees: DC $300 biennial, MD $300/yr, VA $50/yr."},
    # B. TAX & COMPLIANCE
    {"id": "ein",             "category": "Tax & Compliance",   "name": "EIN Filing",                     "state_fee": 0,   "service_fee": 79,  "turnaround": "1 business day",    "description": "Obtain an Employer Identification Number from the IRS."},
    {"id": "state-tax-reg",   "category": "Tax & Compliance",   "name": "State Tax Registration",         "state_fee": 0,   "service_fee": 59,  "turnaround": "3-5 business days",  "description": "Register for state income and/or withholding taxes."},
    {"id": "sales-tax",       "category": "Tax & Compliance",   "name": "Sales Tax Permit",               "state_fee": 0,   "service_fee": 59,  "turnaround": "3-5 business days",  "description": "Obtain a sales & use tax permit."},
    {"id": "boi-fincen",      "category": "Tax & Compliance",   "name": "BOI Filing — FinCEN",            "state_fee": 0,   "service_fee": 49,  "turnaround": "1-2 business days",  "description": "Beneficial Ownership Information report (foreign entities only as of March 2025)."},
    {"id": "compliance-mon",  "category": "Tax & Compliance",   "name": "Compliance Monitoring",          "state_fee": 0,   "service_fee": 149, "turnaround": "ongoing / annual",  "description": "Annual compliance calendar, reminders, and filing support."},
    # C. DOCUMENT SERVICES
    {"id": "apostille-dc",    "category": "Document Services",  "name": "Apostille DC",                   "state_fee": 15,  "service_fee": 99,  "turnaround": "same-day walk-in",  "description": "DC Secretary apostille for Hague Convention countries."},
    {"id": "apostille-md",    "category": "Document Services",  "name": "Apostille MD",                   "state_fee": 5,   "service_fee": 99,  "turnaround": "1-2 days",          "description": "Maryland Secretary of State apostille."},
    {"id": "apostille-va",    "category": "Document Services",  "name": "Apostille VA",                   "state_fee": 10,  "service_fee": 99,  "turnaround": "5 days",            "description": "Virginia Secretary of the Commonwealth apostille."},
    {"id": "apostille-fed",   "category": "Document Services",  "name": "Apostille Federal / DOS",        "state_fee": 20,  "service_fee": 199, "turnaround": "2-5 weeks",         "description": "U.S. Department of State apostille for federal documents."},
    {"id": "embassy-legal",   "category": "Document Services",  "name": "Embassy Legalization",            "state_fee": 0,   "service_fee": 249, "turnaround": "varies by embassy", "description": "Embassy/consulate authentication for non-Hague countries. Embassy fees additional."},
    {"id": "good-standing",   "category": "Document Services",  "name": "Certificate of Good Standing",   "state_fee": 0,   "service_fee": 49,  "turnaround": "1-5 business days",  "description": "Obtain a Certificate of Good Standing (aka Certificate of Existence)."},
    {"id": "certified-copy",  "category": "Document Services",  "name": "Certified Copy of Articles",     "state_fee": 0,   "service_fee": 49,  "turnaround": "1-5 business days",  "description": "Certified copy of formation documents from the state."},
    # D. NOTARY SERVICES
    {"id": "mobile-notary",   "category": "Notary Services",    "name": "Mobile Notary DC/MD/VA",         "state_fee": 0,   "service_fee": 99,  "turnaround": "same-day / next-day", "description": "In-person notarization at your location."},
    {"id": "ron",             "category": "Notary Services",    "name": "Remote Online Notarization",     "state_fee": 0,   "service_fee": 49,  "turnaround": "same-day",          "description": "Notarize documents via live video session."},
    {"id": "notarized-trans", "category": "Notary Services",    "name": "Notarized Translation",          "state_fee": 0,   "service_fee": 99,  "turnaround": "2-5 business days",  "description": "Certified translation + notarization. $0.15/word for translation."},
    # E. REGISTERED AGENT
    {"id": "ra-dc",           "category": "Registered Agent",   "name": "Registered Agent DC",            "state_fee": 0,   "service_fee": 149, "turnaround": "annual service",    "description": "Statutory registered agent service in DC. Annual subscription."},
    {"id": "ra-md",           "category": "Registered Agent",   "name": "Registered Agent MD",            "state_fee": 0,   "service_fee": 149, "turnaround": "annual service",    "description": "Statutory registered agent service in Maryland. Annual subscription."},
    {"id": "ra-va",           "category": "Registered Agent",   "name": "Registered Agent VA",            "state_fee": 0,   "service_fee": 149, "turnaround": "annual service",    "description": "Statutory registered agent service in Virginia. Annual subscription."},
    # F. ADDITIONAL
    {"id": "tm-search",       "category": "Additional",         "name": "Trademark Search",               "state_fee": 0,   "service_fee": 99,  "turnaround": "2-3 business days",  "description": "Comprehensive federal + state trademark availability search."},
    {"id": "tm-filing",       "category": "Additional",         "name": "Trademark Filing",               "state_fee": 350, "service_fee": 349, "turnaround": "8-12 months (USPTO)", "description": "Prepare and file a USPTO trademark application."},
    {"id": "oa-ai",           "category": "Additional",         "name": "Operating Agreement AI Generation", "state_fee": 0, "service_fee": 79, "turnaround": "instant",           "description": "AI-generated custom operating agreement."},
]

PACKAGES_SEED: list[dict] = [
    {
        "id": "starter",
        "name": "Starter",
        "price": 0,
        "description": "Free LLC formation with basic operating agreement template. You pay only state filing fees.",
        "includes": ["LLC Formation (your state)", "Basic OA template"],
        "service_ids": [],  # dynamically resolved per state
        "note": "State filing fees apply."
    },
    {
        "id": "professional",
        "name": "Professional",
        "price": 149,
        "description": "Complete business launch package with EIN, custom operating agreement, registered agent for one year, BOI filing, and compliance reminders.",
        "includes": [
            "LLC Formation (your state)",
            "EIN Filing",
            "Custom Operating Agreement (AI-generated)",
            "1-Year Registered Agent",
            "BOI Filing (FinCEN)",
            "Compliance Reminders"
        ],
        "service_ids_template": ["llc-{state}", "ein", "oa-ai", "ra-{state}", "boi-fincen", "compliance-mon"],
        "note": "State filing fees apply."
    },
    {
        "id": "empire",
        "name": "Empire",
        "price": 349,
        "description": "Everything in Professional plus business license, apostille, certificate of good standing, bank account guidance, priority processing, and a 30-minute consultation.",
        "includes": [
            "Everything in Professional",
            "Business License Application",
            "Apostille (your state)",
            "Certificate of Good Standing",
            "Bank Account Guidance",
            "Priority Processing",
            "30-Minute Consultation"
        ],
        "service_ids_template": [
            "llc-{state}", "ein", "oa-ai", "ra-{state}", "boi-fincen",
            "compliance-mon", "biz-license", "apostille-{state}", "good-standing"
        ],
        "note": "State filing fees apply. Consultation scheduled after order confirmation."
    },
]

STATE_GUIDES: dict[str, dict] = {
    "DC": {
        "state": "DC",
        "name": "District of Columbia",
        "filing_authority": "DC Department of Licensing and Consumer Protection (DLCP)",
        "filing_url": "https://corponline.dcra.dc.gov/",
        "llc_state_fee": 99,
        "corp_state_fee": 220,
        "annual_report_fee": 300,
        "annual_report_frequency": "biennial",
        "registered_agent_required": True,
        "state_tax_registration_url": "https://otr.cfo.dc.gov/",
        "steps": [
            "1. Search business name availability on DLCP CorpOnline.",
            "2. Prepare and file Articles of Organization ($99 filing fee).",
            "3. Appoint a registered agent with a DC street address.",
            "4. Obtain a Basic Business License (BBL) from DLCP.",
            "5. Apply for an EIN from the IRS (free, online at irs.gov).",
            "6. Register with the DC Office of Tax and Revenue (OTR).",
            "7. Draft an Operating Agreement (not filed, but essential).",
            "8. File BOI report with FinCEN if required.",
            "9. File biennial report every 2 years ($300)."
        ],
        "notes": "DC requires a Basic Business License for most activities. Processing is typically 5 business days online."
    },
    "MD": {
        "state": "MD",
        "name": "Maryland",
        "filing_authority": "Maryland State Department of Assessments and Taxation (SDAT)",
        "filing_url": "https://egov.maryland.gov/BusinessExpress/",
        "llc_state_fee": 100,
        "corp_state_fee": 120,
        "annual_report_fee": 300,
        "annual_report_frequency": "annual",
        "registered_agent_required": True,
        "state_tax_registration_url": "https://interactive.marylandtaxes.gov/",
        "steps": [
            "1. Search name availability on Maryland Business Express.",
            "2. File Articles of Organization with SDAT ($100 online).",
            "3. Designate a registered agent with a Maryland address.",
            "4. Obtain necessary local business licenses (county/city).",
            "5. Apply for an EIN from the IRS.",
            "6. Register with the Comptroller of Maryland for state taxes.",
            "7. Draft an Operating Agreement.",
            "8. File BOI report with FinCEN if required.",
            "9. File Annual Report / Personal Property Return by April 15 ($300)."
        ],
        "notes": "Maryland annual report is combined with the Personal Property Return, due April 15 each year."
    },
    "VA": {
        "state": "VA",
        "name": "Virginia",
        "filing_authority": "Virginia State Corporation Commission (SCC)",
        "filing_url": "https://cis.scc.virginia.gov/",
        "llc_state_fee": 100,
        "corp_state_fee": 75,
        "annual_report_fee": 50,
        "annual_report_frequency": "annual",
        "registered_agent_required": True,
        "state_tax_registration_url": "https://www.tax.virginia.gov/",
        "steps": [
            "1. Search name availability on the SCC Clerk's Information System.",
            "2. File Articles of Organization with the SCC ($100).",
            "3. Designate a registered agent with a Virginia address.",
            "4. Obtain a local business license from your city/county.",
            "5. Apply for an EIN from the IRS.",
            "6. Register with the Virginia Department of Taxation.",
            "7. Draft an Operating Agreement.",
            "8. File BOI report with FinCEN if required.",
            "9. File Annual Registration with the SCC ($50/yr)."
        ],
        "notes": "Virginia is one of the fastest states for LLC formation (often 2-3 business days online)."
    },
}


# ── Helpers ──────────────────────────────────────────────────────────

def _load_json(path: str) -> list | dict:
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


def _save_json(path: str, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _new_id() -> str:
    return str(uuid.uuid4())[:8]


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_services() -> list[dict]:
    """Seed services.json on first access if missing."""
    if not os.path.exists(SERVICES_FILE):
        _save_json(SERVICES_FILE, SERVICES_SEED)
        logger.info("LLC Factory: seeded services.json with %d services", len(SERVICES_SEED))
    return _load_json(SERVICES_FILE)


def _ensure_packages() -> list[dict]:
    """Seed packages.json on first access if missing."""
    if not os.path.exists(PACKAGES_FILE):
        _save_json(PACKAGES_FILE, PACKAGES_SEED)
        logger.info("LLC Factory: seeded packages.json with %d packages", len(PACKAGES_SEED))
    return _load_json(PACKAGES_FILE)


def _get_service_map() -> dict[str, dict]:
    services = _ensure_services()
    return {s["id"]: s for s in services}


def _resolve_package_services(pkg_id: str, state: str) -> list[str]:
    """Resolve package template service IDs for a given state."""
    packages = _ensure_packages()
    pkg = next((p for p in packages if p["id"] == pkg_id), None)
    if not pkg:
        return []
    templates = pkg.get("service_ids_template", [])
    state_lower = state.lower()
    resolved = []
    for t in templates:
        resolved.append(t.replace("{state}", state_lower))
    return resolved


def _calc_order_price(service_ids: list[str]) -> tuple[float, float, float]:
    """Return (service_fees, state_fees, total)."""
    svc_map = _get_service_map()
    service_fees = 0.0
    state_fees = 0.0
    for sid in service_ids:
        svc = svc_map.get(sid)
        if svc:
            service_fees += svc.get("service_fee", 0)
            state_fees += svc.get("state_fee", 0)
    return service_fees, state_fees, service_fees + state_fees


def _load_order(order_id: str) -> dict | None:
    path = os.path.join(ORDERS_DIR, f"{order_id}.json")
    if not os.path.exists(path):
        return None
    return _load_json(path)


def _save_order(order: dict):
    path = os.path.join(ORDERS_DIR, f"{order['id']}.json")
    _save_json(path, order)


def _load_customer(cid: str) -> dict | None:
    path = os.path.join(CUSTOMERS_DIR, f"{cid}.json")
    if not os.path.exists(path):
        return None
    return _load_json(path)


def _save_customer(customer: dict):
    path = os.path.join(CUSTOMERS_DIR, f"{customer['id']}.json")
    _save_json(path, customer)


def _list_orders(status: str | None = None, customer_id: str | None = None) -> list[dict]:
    orders = []
    for fname in os.listdir(ORDERS_DIR):
        if not fname.endswith(".json"):
            continue
        o = _load_json(os.path.join(ORDERS_DIR, fname))
        if status and o.get("status") != status:
            continue
        if customer_id and o.get("customer_id") != customer_id:
            continue
        orders.append(o)
    orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return orders


def _list_customers() -> list[dict]:
    customers = []
    for fname in os.listdir(CUSTOMERS_DIR):
        if not fname.endswith(".json"):
            continue
        customers.append(_load_json(os.path.join(CUSTOMERS_DIR, fname)))
    customers.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return customers


def _save_document(order_id: str, doc_type: str, content: str, customer_id: str = None) -> dict:
    """Save generated document to disk and return metadata."""
    doc_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()
    filename = f"{order_id}_{doc_type}_{doc_id}.txt"
    filepath = os.path.join(DOCUMENTS_DIR, filename)

    with open(filepath, "w") as f:
        f.write(content)

    metadata = {
        "doc_id": doc_id,
        "order_id": order_id,
        "customer_id": customer_id,
        "type": doc_type,
        "filename": filename,
        "filepath": filepath,
        "generated_at": timestamp,
        "size_bytes": len(content.encode()),
    }

    # Save metadata index
    index_path = os.path.join(DOCUMENTS_DIR, "index.json")
    index = []
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
    index.append(metadata)
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    return metadata


# ── Routes: Services & Packages ─────────────────────────────────────

@router.get("/services")
def list_services():
    """List all services grouped by category with pricing."""
    services = _ensure_services()
    grouped: dict[str, list] = {}
    for s in services:
        cat = s.get("category", "Other")
        grouped.setdefault(cat, []).append(s)
    return {"services": grouped, "total": len(services)}


@router.get("/packages")
def list_packages():
    """List available packages with included services."""
    packages = _ensure_packages()
    return {"packages": packages}


@router.get("/states/{state}")
def state_guide(state: str):
    """State-specific requirements, fees, deadlines, filing URLs."""
    key = state.upper()
    guide = STATE_GUIDES.get(key)
    if not guide:
        raise HTTPException(status_code=404, detail=f"State guide not found for '{state}'. Available: DC, MD, VA.")
    return guide


# ── Routes: Orders ───────────────────────────────────────────────────

@router.post("/orders")
def create_order(body: OrderCreate):
    """Create a new order."""
    order_id = _new_id()
    now = _now()

    # Resolve services from package if provided
    service_ids = list(body.services)
    if body.package and body.package != "custom":
        pkg_services = _resolve_package_services(body.package, body.state)
        # Merge: package services + any extra services
        for sid in pkg_services:
            if sid not in service_ids:
                service_ids.append(sid)

    # Calculate pricing
    service_fees, state_fees, total = _calc_order_price(service_ids)

    # Add package price on top if applicable
    if body.package:
        packages = _ensure_packages()
        pkg = next((p for p in packages if p["id"] == body.package), None)
        if pkg:
            pkg_price = pkg.get("price", 0)
            # Package price replaces individual service fees
            total = pkg_price + state_fees
            service_fees = pkg_price

    # Auto-create or link customer
    customer_id = body.customer_id or _new_id()
    if not body.customer_id:
        customer = {
            "id": customer_id,
            "name": body.customer_name,
            "email": body.customer_email,
            "phone": body.customer_phone,
            "address": None,
            "notes": "",
            "created_at": now,
            "updated_at": now,
        }
        _save_customer(customer)

    order = {
        "id": order_id,
        "customer_id": customer_id,
        "customer_name": body.customer_name,
        "customer_email": body.customer_email,
        "customer_phone": body.customer_phone,
        "package": body.package or "custom",
        "services": service_ids,
        "state": body.state.upper(),
        "business_name": body.business_name,
        "business_type": body.business_type,
        "members": [m.model_dump() for m in body.members],
        "status": "received",
        "total_price": total,
        "state_fees": state_fees,
        "service_fees": service_fees,
        "paid": False,
        "payment_method": body.payment_method,
        "documents": [],
        "timeline": [{"status": "received", "timestamp": now, "note": "Order created."}],
        "notes": body.notes,
        "created_at": now,
        "updated_at": now,
    }
    _save_order(order)
    logger.info("LLC Factory: order %s created for %s", order_id, body.customer_name)
    return order


@router.get("/orders")
def list_orders_endpoint(
    status: Optional[str] = Query(None, description="Filter by status"),
    customer_id: Optional[str] = Query(None, description="Filter by customer"),
):
    """List orders with optional filters."""
    orders = _list_orders(status=status, customer_id=customer_id)
    return {"orders": orders, "total": len(orders)}


@router.get("/orders/{order_id}")
def get_order(order_id: str):
    """Get order detail with timeline."""
    order = _load_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")
    return order


@router.put("/orders/{order_id}")
def update_order(order_id: str, body: OrderUpdate):
    """Update order status, notes, documents."""
    order = _load_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")

    now = _now()
    valid_statuses = ["received", "processing", "filed", "approved", "delivered", "completed"]

    if body.status is not None:
        if body.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        order["status"] = body.status
        order["timeline"].append({
            "status": body.status,
            "timestamp": now,
            "note": body.notes or f"Status updated to {body.status}.",
        })

    if body.notes is not None:
        order["notes"] = body.notes
    if body.paid is not None:
        order["paid"] = body.paid
    if body.payment_method is not None:
        order["payment_method"] = body.payment_method
    if body.documents is not None:
        order["documents"].extend(body.documents)

    order["updated_at"] = now
    _save_order(order)
    return order


@router.get("/orders/{order_id}/timeline")
def get_order_timeline(order_id: str):
    """Get order status timeline."""
    order = _load_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")
    return {"order_id": order_id, "timeline": order.get("timeline", [])}


# ── Routes: Customers ───────────────────────────────────────────────

@router.get("/customers")
def list_customers_endpoint():
    """List all customers."""
    customers = _list_customers()
    return {"customers": customers, "total": len(customers)}


@router.post("/customers")
def create_customer(body: CustomerCreate):
    """Create a new customer."""
    cid = _new_id()
    now = _now()
    customer = {
        "id": cid,
        "name": body.name,
        "email": body.email,
        "phone": body.phone,
        "address": body.address,
        "notes": body.notes or "",
        "created_at": now,
        "updated_at": now,
    }
    _save_customer(customer)
    return customer


@router.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    """Get customer detail with their orders."""
    customer = _load_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found.")
    orders = _list_orders(customer_id=customer_id)
    return {**customer, "orders": orders}


# ── Routes: Quote ────────────────────────────────────────────────────

@router.post("/quote")
def generate_quote(body: QuoteRequest):
    """Generate a price quote for selected services + state."""
    svc_map = _get_service_map()

    # If package selected, resolve its services
    service_ids = list(body.services)
    pkg_price = 0
    pkg_name = None
    if body.package and body.package != "custom":
        packages = _ensure_packages()
        pkg = next((p for p in packages if p["id"] == body.package), None)
        if not pkg:
            raise HTTPException(status_code=404, detail=f"Package '{body.package}' not found.")
        pkg_price = pkg.get("price", 0)
        pkg_name = pkg.get("name")
        pkg_svcs = _resolve_package_services(body.package, body.state)
        for sid in pkg_svcs:
            if sid not in service_ids:
                service_ids.append(sid)

    # Build line items
    line_items = []
    total_state_fees = 0.0
    total_service_fees = 0.0
    for sid in service_ids:
        svc = svc_map.get(sid)
        if svc:
            line_items.append({
                "service_id": sid,
                "name": svc["name"],
                "service_fee": svc["service_fee"],
                "state_fee": svc["state_fee"],
                "total": svc["service_fee"] + svc["state_fee"],
            })
            total_state_fees += svc["state_fee"]
            total_service_fees += svc["service_fee"]

    # If package, service fee = package price
    if pkg_price > 0:
        total_service_fees = pkg_price

    return {
        "package": pkg_name,
        "state": body.state.upper(),
        "line_items": line_items,
        "service_fees": total_service_fees,
        "state_fees": total_state_fees,
        "total": total_service_fees + total_state_fees,
        "note": "State fees are paid to the government and are non-negotiable. Service fees cover our preparation, filing, and support.",
    }


# ── Routes: AI Features ─────────────────────────────────────────────

@router.post("/name-check")
def check_business_name(body: NameCheckRequest):
    """Check business name availability (mock — returns simulated result)."""
    # In production this would scrape or call state APIs
    name = body.name.strip()
    state = body.state.upper()
    if not name:
        raise HTTPException(status_code=400, detail="Business name is required.")

    # Simple mock logic
    taken_keywords = ["empire", "google", "amazon", "meta", "apple", "microsoft"]
    is_available = not any(kw in name.lower() for kw in taken_keywords)

    return {
        "name": name,
        "state": state,
        "entity_type": body.entity_type,
        "available": is_available,
        "similar_names": [] if is_available else [f"{name} LLC (existing)", f"{name} Inc (existing)"],
        "search_url": STATE_GUIDES.get(state, {}).get("filing_url", ""),
        "note": "This is a preliminary check. Official availability is confirmed upon filing with the state.",
    }


@router.post("/generate-oa")
async def generate_operating_agreement(body: GenerateOARequest):
    """AI-generate an operating agreement. Tries MAX/Grok, falls back to template."""
    members_text = "\n".join(
        f"  - {m.name} ({m.role}, {m.ownership_pct}% ownership)"
        for m in body.members
    ) or "  - [Single member / to be determined]"

    prompt = (
        f"Generate a professional Operating Agreement for the following LLC:\n\n"
        f"Business Name: {body.business_name}\n"
        f"State: {body.state}\n"
        f"Management Type: {body.management_type}\n"
        f"Business Purpose: {body.business_purpose}\n"
        f"Members:\n{members_text}\n\n"
        f"Include all standard sections: formation, purpose, members & ownership, "
        f"management, capital contributions, distributions, meetings, transfer of interests, "
        f"dissolution, and governing law ({body.state}). "
        f"Use professional legal language. Include signature blocks for each member."
    )

    # Try to call local MAX AI
    ai_source = "template"
    content = None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "http://localhost:8000/api/v1/max/chat/stream",
                json={"message": prompt, "desk_id": "legal"},
                headers={"Accept": "text/event-stream"},
            )
            if resp.status_code == 200:
                # Parse SSE response
                full_text = ""
                for line in resp.text.split("\n"):
                    if line.startswith("data:"):
                        try:
                            chunk = json.loads(line[5:].strip())
                            if chunk.get("type") == "text":
                                full_text += chunk.get("content", "")
                        except json.JSONDecodeError:
                            continue
                if full_text.strip():
                    content = full_text
                    ai_source = "MAX"
    except Exception as e:
        logger.warning("LLC Factory: AI OA generation failed, using template: %s", e)

    # Fallback: static template
    if not content:
        content = _generate_oa_template(body)

    # Persist document to disk
    oid = body.order_id or "standalone"
    doc_meta = _save_document(oid, "operating_agreement", content, customer_id=body.customer_id)

    # If order_id provided, update the order record with the document reference
    if body.order_id:
        order = _load_order(body.order_id)
        if order:
            order.setdefault("documents", []).append(doc_meta)
            order["updated_at"] = _now()
            _save_order(order)

    return {
        "business_name": body.business_name,
        "state": body.state,
        "generated": True,
        "ai_source": ai_source,
        "content": content,
        "doc_id": doc_meta["doc_id"],
        "filepath": doc_meta["filepath"],
        "generated_at": _now(),
    }


def _generate_oa_template(body: GenerateOARequest) -> str:
    """Fallback Operating Agreement template."""
    state_names = {"DC": "the District of Columbia", "MD": "Maryland", "VA": "Virginia"}
    state_name = state_names.get(body.state.upper(), body.state)
    members_section = ""
    for i, m in enumerate(body.members, 1):
        members_section += (
            f"    {i}. {m.name}\n"
            f"       Role: {m.role.title()}\n"
            f"       Ownership: {m.ownership_pct}%\n\n"
        )
    if not members_section:
        members_section = "    1. [Member Name]\n       Role: Member\n       Ownership: 100%\n\n"

    return f"""OPERATING AGREEMENT
OF
{body.business_name.upper()}
A {state_name} Limited Liability Company

Effective Date: {datetime.utcnow().strftime('%B %d, %Y')}

ARTICLE I — FORMATION
The Members hereby form a Limited Liability Company under the laws of {state_name}.
The name of the Company shall be "{body.business_name}".

ARTICLE II — PURPOSE
The purpose of the Company is to engage in {body.business_purpose}.

ARTICLE III — MEMBERS AND OWNERSHIP

{members_section}
ARTICLE IV — MANAGEMENT
The Company shall be {body.management_type}. {"Each Member shall have authority to act on behalf of the Company." if body.management_type == "member-managed" else "The Manager(s) shall have exclusive authority to manage the Company."}

ARTICLE V — CAPITAL CONTRIBUTIONS
Each Member shall contribute capital as agreed upon by the Members. No Member shall be required to make additional contributions without unanimous consent.

ARTICLE VI — DISTRIBUTIONS
Net profits and losses shall be allocated to the Members in proportion to their ownership percentages. Distributions shall be made at such times and in such amounts as determined by the {"Members" if body.management_type == "member-managed" else "Manager(s)"}.

ARTICLE VII — MEETINGS
Members shall hold at least one annual meeting. Special meetings may be called by any Member with reasonable notice.

ARTICLE VIII — TRANSFER OF INTERESTS
No Member may transfer their interest without the written consent of all other Members. Right of first refusal applies.

ARTICLE IX — DISSOLUTION
The Company shall be dissolved upon: (a) the written consent of all Members; (b) a judicial decree; or (c) any event that makes it unlawful for the Company to continue.

ARTICLE X — GOVERNING LAW
This Agreement shall be governed by the laws of {state_name}.

ARTICLE XI — AMENDMENTS
This Agreement may be amended only by the written consent of all Members.

IN WITNESS WHEREOF, the Members have executed this Operating Agreement as of the date first written above.

SIGNATURES:

{"".join(f'''_________________________________
{m.name}
Date: _______________

''' for m in body.members) if body.members else '''_________________________________
[Member Name]
Date: _______________
'''}

--- END OF OPERATING AGREEMENT ---
"""


@router.post("/generate-docs")
async def generate_formation_docs(body: GenerateDocsRequest):
    """Generate formation documents for an order."""
    order = _load_order(body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {body.order_id} not found.")

    doc_types = body.doc_types or ["articles", "oa"]
    generated = []
    now = _now()

    customer_id = order.get("customer_id")

    for doc_type in doc_types:
        content = None
        type_label = doc_type

        if doc_type == "oa":
            members = [Member(**m) for m in order.get("members", [])]
            oa_body = GenerateOARequest(
                business_name=order.get("business_name", ""),
                state=order.get("state", "DC"),
                members=members,
            )
            content = _generate_oa_template(oa_body)
            type_label = "operating_agreement"
        elif doc_type == "articles":
            content = _generate_articles_template(order)
            type_label = "articles_of_organization"
        elif doc_type == "ein_ss4":
            content = _generate_ss4_template(order)
            type_label = "ein_ss4"
        elif doc_type == "consent":
            content = _generate_consent_template(order)
            type_label = "consent_resolution"

        if content:
            doc_meta = _save_document(body.order_id, type_label, content, customer_id=customer_id)
            generated.append({
                **doc_meta,
                "content": content,
            })

    # Add document references to order (full metadata, not just filename)
    for doc in generated:
        order["documents"].append({
            "doc_id": doc["doc_id"],
            "order_id": doc["order_id"],
            "customer_id": doc.get("customer_id"),
            "type": doc["type"],
            "filename": doc["filename"],
            "filepath": doc["filepath"],
            "generated_at": doc["generated_at"],
            "size_bytes": doc["size_bytes"],
        })
    order["updated_at"] = now
    _save_order(order)

    return {"order_id": body.order_id, "documents": generated, "total": len(generated)}


def _generate_articles_template(order: dict) -> str:
    state_names = {"DC": "the District of Columbia", "MD": "Maryland", "VA": "Virginia"}
    state = order.get("state", "DC")
    state_name = state_names.get(state, state)
    return f"""ARTICLES OF ORGANIZATION
{order.get('business_name', '[Business Name]').upper()}

Filed with: {STATE_GUIDES.get(state, {}).get('filing_authority', 'State Filing Authority')}

1. NAME: {order.get('business_name', '[Business Name]')}

2. PRINCIPAL OFFICE ADDRESS: [To be provided]

3. REGISTERED AGENT: [Name and address of registered agent in {state_name}]

4. PURPOSE: The Company is organized for any lawful purpose.

5. MANAGEMENT: The Company shall be member-managed.

6. ORGANIZER: [Organizer name and address]

7. EFFECTIVE DATE: Upon filing.

--- This is a template. The actual filing must be submitted to {STATE_GUIDES.get(state, {}).get('filing_authority', 'the state')}. ---
"""


def _generate_ss4_template(order: dict) -> str:
    return f"""IRS FORM SS-4 — APPLICATION FOR EMPLOYER IDENTIFICATION NUMBER
(Template / Worksheet)

1. Legal Name: {order.get('business_name', '[Business Name]')}
2. Trade Name (DBA): [If applicable]
3. Entity Type: Limited Liability Company
4. State of Organization: {order.get('state', 'DC')}
5. Reason for Applying: Started new business
6. Date Business Started: [Date]
7. Principal Activity: [Description]
8. Responsible Party: {order.get('members', [{}])[0].get('name', '[Member Name]') if order.get('members') else '[Member Name]'}

APPLY ONLINE: https://www.irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online

--- This is a worksheet. Apply directly on IRS.gov for instant EIN issuance. ---
"""


def _generate_consent_template(order: dict) -> str:
    members = order.get("members", [])
    member_lines = "\n".join(
        f"  - {m.get('name', '[Name]')}" for m in members
    ) or "  - [Member Name]"

    return f"""UNANIMOUS WRITTEN CONSENT
OF THE MEMBERS OF
{order.get('business_name', '[Business Name]').upper()}

Date: {datetime.utcnow().strftime('%B %d, %Y')}

The undersigned, being all of the Members of {order.get('business_name', '[Business Name]')}
(the "Company"), hereby consent to and adopt the following resolutions:

RESOLVED, that the Company is hereby authorized to:
  1. Open business bank accounts at [Bank Name].
  2. Obtain an Employer Identification Number (EIN) from the IRS.
  3. Apply for all necessary business licenses and permits.
  4. Engage in all activities necessary to carry out the Company's purpose.

RESOLVED FURTHER, that the officers and members of the Company are authorized to
take all actions necessary to effectuate the foregoing resolutions.

Members:
{member_lines}

SIGNATURES:

{"".join(f'''_________________________________
{m.get("name", "[Name]")}
Date: _______________

''' for m in members) if members else '''_________________________________
[Member Name]
Date: _______________
'''}
"""


# ── Routes: Document Retrieval ──────────────────────────────────────

@router.get("/documents")
def list_documents(
    order_id: Optional[str] = Query(None, description="Filter by order ID"),
):
    """List all generated documents, with optional order_id filter."""
    index_path = os.path.join(DOCUMENTS_DIR, "index.json")
    if not os.path.exists(index_path):
        return {"documents": [], "total": 0}
    index = _load_json(index_path)
    if order_id:
        index = [d for d in index if d.get("order_id") == order_id]
    return {"documents": index, "total": len(index)}


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: str):
    """Download a generated document by doc_id."""
    index_path = os.path.join(DOCUMENTS_DIR, "index.json")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")
    index = _load_json(index_path)
    doc = next((d for d in index if d.get("doc_id") == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")
    filepath = doc.get("filepath", "")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Document file missing from disk: {doc['filename']}")
    with open(filepath, "r") as f:
        content = f.read()
    return PlainTextResponse(
        content=content,
        headers={"Content-Disposition": f'attachment; filename="{doc["filename"]}"'},
    )


# ── Routes: Dashboard ───────────────────────────────────────────────

@router.get("/dashboard")
def admin_dashboard():
    """Admin stats: orders pipeline, revenue MTD/YTD, popular services."""
    orders = _list_orders()
    now = datetime.utcnow()

    # Pipeline
    pipeline: dict[str, int] = {}
    for o in orders:
        s = o.get("status", "unknown")
        pipeline[s] = pipeline.get(s, 0) + 1

    # Revenue
    revenue_mtd = 0.0
    revenue_ytd = 0.0
    for o in orders:
        if not o.get("paid"):
            continue
        try:
            created = datetime.fromisoformat(o["created_at"].rstrip("Z"))
        except (ValueError, KeyError):
            continue
        total = o.get("total_price", 0)
        if created.year == now.year:
            revenue_ytd += total
            if created.month == now.month:
                revenue_mtd += total

    # Popular services
    service_counts: dict[str, int] = {}
    for o in orders:
        for sid in o.get("services", []):
            service_counts[sid] = service_counts.get(sid, 0) + 1
    popular = sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # State breakdown
    state_counts: dict[str, int] = {}
    for o in orders:
        st = o.get("state", "?")
        state_counts[st] = state_counts.get(st, 0) + 1

    return {
        "total_orders": len(orders),
        "pipeline": pipeline,
        "revenue_mtd": round(revenue_mtd, 2),
        "revenue_ytd": round(revenue_ytd, 2),
        "popular_services": [{"service_id": sid, "count": cnt} for sid, cnt in popular],
        "orders_by_state": state_counts,
        "total_customers": len(_list_customers()),
    }
