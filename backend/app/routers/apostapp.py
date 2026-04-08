"""
ApostApp — Document Apostille & Authentication Service.
Handles apostille, notarization, certification, and embassy legalization
for DC / MD / VA. JSON file storage.

Integrates with LLC Factory for seamless business document apostille.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
import json
import uuid
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apostapp", tags=["apostapp"])

# ── Storage ──────────────────────────────────────────────────────────
BASE_DIR = os.path.expanduser("~/empire-repo/backend/data/apostapp")
ORDERS_DIR = os.path.join(BASE_DIR, "orders")
CUSTOMERS_DIR = os.path.join(BASE_DIR, "customers")
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")

for _d in (BASE_DIR, ORDERS_DIR, CUSTOMERS_DIR, DOCUMENTS_DIR):
    os.makedirs(_d, exist_ok=True)

# LLC Factory data path (for cross-service integration)
LLC_ORDERS_DIR = os.path.expanduser("~/empire-repo/backend/data/llcfactory/orders")


# ── Services & Pricing ──────────────────────────────────────────────

APOSTILLE_SERVICES = {
    "state_apostille": {"name": "State Apostille", "base_fee": 50, "state_fee": {"DC": 20, "MD": 22, "VA": 12}, "processing_days": 5},
    "federal_apostille": {"name": "Federal Apostille (US Dept of State)", "base_fee": 85, "state_fee": {}, "processing_days": 10},
    "notarization": {"name": "Notarization", "base_fee": 25, "per_page": 5},
    "certified_copy": {"name": "Certified Copy", "base_fee": 35},
    "translation": {"name": "Certified Translation", "base_fee": 75, "per_page": 15},
    "authentication": {"name": "Embassy Authentication/Legalization", "base_fee": 150, "processing_days": 15},
    "rush_processing": {"name": "Rush Processing", "multiplier": 2.0},
    "same_day": {"name": "Same Day Service", "multiplier": 3.0, "available_states": ["DC"]},
}

DOCUMENT_TYPES = [
    "birth_certificate", "marriage_certificate", "death_certificate", "divorce_decree",
    "diploma", "transcript", "corporate_document", "articles_of_organization",
    "operating_agreement", "power_of_attorney", "affidavit", "court_order",
    "fbi_background_check", "commercial_invoice", "certificate_of_good_standing",
    "other"
]

DESTINATION_COUNTRIES = {
    "common": [
        "Mexico", "Colombia", "Brazil", "China", "India", "Philippines",
        "South Korea", "Japan", "Germany", "France", "Spain", "Italy",
        "UK", "Canada", "Australia"
    ],
    "hague_members": True,
}

SHIPPING_OPTIONS = {
    "standard": {"name": "Standard (USPS Priority)", "fee": 12, "days": "3-5"},
    "express": {"name": "Express (USPS Express)", "fee": 28, "days": "1-2"},
    "fedex": {"name": "FedEx Overnight", "fee": 35, "days": "Next day"},
    "international": {"name": "International (DHL)", "fee": 65, "days": "5-10"},
    "pickup": {"name": "Local Pickup (DC Office)", "fee": 0, "days": "Same day"},
}


# ── Pydantic Schemas ────────────────────────────────────────────────

class ApostilleDocument(BaseModel):
    doc_type: str = "other"
    doc_description: str = ""
    state_of_origin: str = "DC"
    destination_country: str = ""
    needs_notarization: bool = False
    needs_certification: bool = False
    status: str = "received"  # received | notarized | certified | at_state | apostilled | completed
    tracking_number: Optional[str] = None
    fee: float = 0.0


class ApostilleOrderCreate(BaseModel):
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_id: Optional[str] = None
    documents: List[ApostilleDocument] = Field(default_factory=list)
    rush: bool = False
    same_day: bool = False
    shipping_method: str = "standard"
    shipping_address: Optional[str] = None
    notes: str = ""


class ApostilleOrderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    paid: Optional[bool] = None
    shipping_method: Optional[str] = None
    shipping_address: Optional[str] = None
    tracking_number: Optional[str] = None


class DocumentStatusUpdate(BaseModel):
    status: Optional[str] = None
    tracking_number: Optional[str] = None
    fee: Optional[float] = None


class ApostilleCustomerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class LLCOrderLink(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    destination_country: str = ""
    rush: bool = False
    shipping_method: str = "standard"
    shipping_address: Optional[str] = None
    notes: str = ""


# ── Helpers ──────────────────────────────────────────────────────────

def _save_json(directory: str, filename: str, data: dict):
    path = os.path.join(directory, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _load_json(directory: str, filename: str) -> dict:
    path = os.path.join(directory, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Not found: {filename}")
    with open(path) as f:
        return json.load(f)


def _list_json(directory: str) -> list[dict]:
    results = []
    if not os.path.isdir(directory):
        return results
    for fname in sorted(os.listdir(directory)):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(directory, fname)) as f:
                    results.append(json.load(f))
            except Exception:
                pass
    return results


def _calculate_document_fee(doc: ApostilleDocument, rush: bool = False) -> float:
    """Calculate fee for a single document based on services needed."""
    fee = 0.0
    state = doc.state_of_origin.upper()

    # Base apostille fee
    if state in ("DC", "MD", "VA"):
        svc = APOSTILLE_SERVICES["state_apostille"]
        fee += svc["base_fee"] + svc["state_fee"].get(state, 0)
    else:
        svc = APOSTILLE_SERVICES["federal_apostille"]
        fee += svc["base_fee"]

    # Notarization add-on
    if doc.needs_notarization:
        fee += APOSTILLE_SERVICES["notarization"]["base_fee"]

    # Certification add-on
    if doc.needs_certification:
        fee += APOSTILLE_SERVICES["certified_copy"]["base_fee"]

    # Rush multiplier
    if rush:
        fee *= APOSTILLE_SERVICES["rush_processing"]["multiplier"]

    return round(fee, 2)


def _calculate_order_total(documents: list[dict], rush: bool, shipping_method: str) -> float:
    """Calculate total for an order."""
    total = 0.0
    for d in documents:
        total += d.get("fee", 0.0)
    # Shipping
    ship = SHIPPING_OPTIONS.get(shipping_method, SHIPPING_OPTIONS["standard"])
    total += ship["fee"]
    return round(total, 2)


# ── Endpoints ────────────────────────────────────────────────────────

# 1. Service info
@router.get("/")
async def apostapp_info():
    """ApostApp service overview and pricing."""
    return {
        "service": "ApostApp",
        "description": "Document Apostille & Authentication Service for DC, MD, VA",
        "tagline": "Get your documents internationally recognized — fast.",
        "coverage": ["DC", "MD", "VA", "Federal (US Dept of State)"],
        "services": APOSTILLE_SERVICES,
        "document_types": DOCUMENT_TYPES,
        "shipping_options": SHIPPING_OPTIONS,
        "destination_countries": DESTINATION_COUNTRIES,
        "office": "Washington, DC",
    }


# 2. All services with pricing
@router.get("/services")
async def list_services():
    """All apostille services with pricing details."""
    return {"services": APOSTILLE_SERVICES}


# 3. Document types
@router.get("/document-types")
async def list_document_types():
    """Supported document types for apostille."""
    return {"document_types": DOCUMENT_TYPES}


# 4. Pricing calculator
@router.get("/pricing-calculator")
async def pricing_calculator(
    doc_type: str = Query("other", description="Document type"),
    state: str = Query("DC", description="State of origin (DC, MD, VA, or federal)"),
    rush: bool = Query(False, description="Rush processing"),
    shipping: str = Query("standard", description="Shipping method"),
    needs_notarization: bool = Query(False),
    needs_certification: bool = Query(False),
    num_documents: int = Query(1, ge=1, le=50),
):
    """Calculate estimated total for apostille services."""
    doc = ApostilleDocument(
        doc_type=doc_type,
        state_of_origin=state,
        needs_notarization=needs_notarization,
        needs_certification=needs_certification,
    )
    per_doc_fee = _calculate_document_fee(doc, rush=rush)
    shipping_fee = SHIPPING_OPTIONS.get(shipping, SHIPPING_OPTIONS["standard"])["fee"]
    total = round(per_doc_fee * num_documents + shipping_fee, 2)

    # Estimate processing days
    if state.upper() in ("DC", "MD", "VA"):
        base_days = APOSTILLE_SERVICES["state_apostille"]["processing_days"]
    else:
        base_days = APOSTILLE_SERVICES["federal_apostille"]["processing_days"]
    if rush:
        base_days = max(1, base_days // 2)

    return {
        "per_document_fee": per_doc_fee,
        "num_documents": num_documents,
        "documents_subtotal": round(per_doc_fee * num_documents, 2),
        "shipping_method": shipping,
        "shipping_fee": shipping_fee,
        "total": total,
        "estimated_processing_days": base_days,
        "rush": rush,
        "breakdown": {
            "apostille_base": APOSTILLE_SERVICES["state_apostille"]["base_fee"] if state.upper() in ("DC", "MD", "VA") else APOSTILLE_SERVICES["federal_apostille"]["base_fee"],
            "state_fee": APOSTILLE_SERVICES["state_apostille"]["state_fee"].get(state.upper(), 0) if state.upper() in ("DC", "MD", "VA") else 0,
            "notarization": APOSTILLE_SERVICES["notarization"]["base_fee"] if needs_notarization else 0,
            "certification": APOSTILLE_SERVICES["certified_copy"]["base_fee"] if needs_certification else 0,
            "rush_multiplier": APOSTILLE_SERVICES["rush_processing"]["multiplier"] if rush else 1.0,
        },
    }


# 5. Create order
_ORDER_COUNTER = 0

def _next_order_number() -> str:
    global _ORDER_COUNTER
    _ORDER_COUNTER += 1
    return f"APO-{datetime.utcnow().strftime('%Y%m')}-{_ORDER_COUNTER:04d}"


@router.post("/orders")
async def create_order(order: ApostilleOrderCreate):
    """Create a new apostille order."""
    order_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    # Calculate fees for each document
    docs = []
    for d in order.documents:
        doc_dict = d.model_dump()
        fee = _calculate_document_fee(d, rush=order.rush)
        if order.same_day and d.state_of_origin.upper() == "DC":
            fee *= APOSTILLE_SERVICES["same_day"]["multiplier"]
        doc_dict["fee"] = round(fee, 2)
        docs.append(doc_dict)

    # Resolve or create customer
    customer_id = order.customer_id
    if not customer_id:
        customer_id = str(uuid.uuid4())[:8]
        customer_data = {
            "id": customer_id,
            "name": order.customer_name,
            "email": order.customer_email,
            "phone": order.customer_phone,
            "address": order.shipping_address,
            "orders": [order_id],
            "created_at": now,
        }
        _save_json(CUSTOMERS_DIR, f"{customer_id}.json", customer_data)
    else:
        # Add order to existing customer
        try:
            cust = _load_json(CUSTOMERS_DIR, f"{customer_id}.json")
            cust.setdefault("orders", []).append(order_id)
            _save_json(CUSTOMERS_DIR, f"{customer_id}.json", cust)
        except HTTPException:
            pass  # customer not found — proceed anyway

    shipping_fee = SHIPPING_OPTIONS.get(order.shipping_method, SHIPPING_OPTIONS["standard"])["fee"]
    doc_total = sum(d["fee"] for d in docs)
    total = round(doc_total + shipping_fee, 2)

    order_data = {
        "id": order_id,
        "order_number": _next_order_number(),
        "customer_id": customer_id,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "customer_phone": order.customer_phone,
        "documents": docs,
        "status": "received",
        "rush": order.rush,
        "same_day": order.same_day,
        "shipping_method": order.shipping_method,
        "shipping_address": order.shipping_address,
        "total": total,
        "paid": False,
        "notes": order.notes,
        "metadata": {},
        "created_at": now,
        "updated_at": now,
    }

    _save_json(ORDERS_DIR, f"{order_id}.json", order_data)
    logger.info(f"ApostApp order created: {order_id} — {len(docs)} docs, ${total}")
    return order_data


# 6. List orders
@router.get("/orders")
async def list_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List all apostille orders, optionally filtered by status."""
    orders = _list_json(ORDERS_DIR)
    if status:
        orders = [o for o in orders if o.get("status") == status]
    # Sort newest first
    orders.sort(key=lambda o: o.get("created_at", ""), reverse=True)
    return {"orders": orders, "count": len(orders)}


# 7. Get order
@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get apostille order details."""
    return _load_json(ORDERS_DIR, f"{order_id}.json")


# 8. Update order
@router.put("/orders/{order_id}")
async def update_order(order_id: str, update: ApostilleOrderUpdate):
    """Update apostille order (status, notes, payment, shipping)."""
    order = _load_json(ORDERS_DIR, f"{order_id}.json")
    changes = update.model_dump(exclude_none=True)

    for key, val in changes.items():
        order[key] = val
    order["updated_at"] = datetime.utcnow().isoformat()

    _save_json(ORDERS_DIR, f"{order_id}.json", order)
    logger.info(f"ApostApp order updated: {order_id} — {list(changes.keys())}")
    return order


# 9. Update individual document status
@router.put("/orders/{order_id}/documents/{doc_index}/status")
async def update_document_status(order_id: str, doc_index: int, update: DocumentStatusUpdate):
    """Update the status of a specific document within an order."""
    order = _load_json(ORDERS_DIR, f"{order_id}.json")
    docs = order.get("documents", [])

    if doc_index < 0 or doc_index >= len(docs):
        raise HTTPException(status_code=404, detail=f"Document index {doc_index} out of range (0-{len(docs)-1})")

    changes = update.model_dump(exclude_none=True)
    for key, val in changes.items():
        docs[doc_index][key] = val

    order["documents"] = docs
    order["updated_at"] = datetime.utcnow().isoformat()

    # Auto-update order status based on document statuses
    doc_statuses = [d.get("status", "received") for d in docs]
    if all(s == "completed" for s in doc_statuses):
        order["status"] = "completed"
    elif any(s == "at_state" for s in doc_statuses):
        order["status"] = "at_state"
    elif any(s in ("notarized", "certified", "apostilled") for s in doc_statuses):
        order["status"] = "processing"

    _save_json(ORDERS_DIR, f"{order_id}.json", order)
    logger.info(f"ApostApp doc {doc_index} in order {order_id} updated: {changes}")
    return order


# 10. Create customer
@router.post("/customers")
async def create_customer(customer: ApostilleCustomerCreate):
    """Create a new ApostApp customer."""
    customer_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    customer_data = {
        "id": customer_id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "address": customer.address,
        "orders": [],
        "created_at": now,
    }
    _save_json(CUSTOMERS_DIR, f"{customer_id}.json", customer_data)
    logger.info(f"ApostApp customer created: {customer_id} — {customer.name}")
    return customer_data


# 11. List customers
@router.get("/customers")
async def list_customers():
    """List all ApostApp customers."""
    customers = _list_json(CUSTOMERS_DIR)
    customers.sort(key=lambda c: c.get("created_at", ""), reverse=True)
    return {"customers": customers, "count": len(customers)}


# 12. Get customer with order history
@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    """Get customer with full order history."""
    customer = _load_json(CUSTOMERS_DIR, f"{customer_id}.json")

    # Load order details
    order_details = []
    for oid in customer.get("orders", []):
        try:
            order_details.append(_load_json(ORDERS_DIR, f"{oid}.json"))
        except HTTPException:
            order_details.append({"id": oid, "status": "not_found"})

    customer["order_history"] = order_details
    return customer


# 13. Dashboard KPIs
@router.get("/dashboard")
async def dashboard():
    """ApostApp business dashboard — KPIs and metrics."""
    orders = _list_json(ORDERS_DIR)
    now = datetime.utcnow()
    current_month = now.strftime("%Y-%m")

    active_statuses = {"received", "processing", "at_state"}
    active_orders = [o for o in orders if o.get("status") in active_statuses]
    completed_this_month = [
        o for o in orders
        if o.get("status") == "completed"
        and o.get("updated_at", "").startswith(current_month)
    ]
    at_state = [o for o in orders if o.get("status") == "at_state"]

    # Revenue MTD — sum of paid orders this month
    revenue_mtd = sum(
        o.get("total", 0)
        for o in orders
        if o.get("paid") and o.get("created_at", "").startswith(current_month)
    )

    # Average processing time (completed orders with both timestamps)
    processing_times = []
    for o in orders:
        if o.get("status") == "completed" and o.get("created_at") and o.get("updated_at"):
            try:
                created = datetime.fromisoformat(o["created_at"])
                updated = datetime.fromisoformat(o["updated_at"])
                days = (updated - created).days
                processing_times.append(days)
            except Exception:
                pass
    avg_processing = round(sum(processing_times) / len(processing_times), 1) if processing_times else 0

    # Total documents in pipeline
    total_docs = sum(len(o.get("documents", [])) for o in active_orders)

    # Revenue by service type breakdown
    doc_type_counts = {}
    for o in orders:
        for d in o.get("documents", []):
            dt = d.get("doc_type", "other")
            doc_type_counts[dt] = doc_type_counts.get(dt, 0) + 1

    return {
        "total_orders": len(orders),
        "active_orders": len(active_orders),
        "pending_at_state": len(at_state),
        "completed_this_month": len(completed_this_month),
        "revenue_mtd": round(revenue_mtd, 2),
        "avg_processing_days": avg_processing,
        "total_documents_in_pipeline": total_docs,
        "document_type_breakdown": doc_type_counts,
        "customers_total": len(_list_json(CUSTOMERS_DIR)),
        "month": current_month,
    }


# 14. Create apostille order from LLC Factory order
@router.post("/orders/from-llc/{llc_order_id}")
async def create_from_llc_order(llc_order_id: str, link: LLCOrderLink = LLCOrderLink()):
    """
    Create an apostille order from an existing LLC Factory order.
    Auto-extracts documents that commonly need apostille:
    - Articles of Organization
    - Operating Agreement
    - Certificate of Good Standing
    """
    # Read the LLC order
    llc_path = os.path.join(LLC_ORDERS_DIR, f"{llc_order_id}.json")
    if not os.path.exists(llc_path):
        raise HTTPException(status_code=404, detail=f"LLC Factory order {llc_order_id} not found")

    with open(llc_path) as f:
        llc_order = json.load(f)

    # Extract info from LLC order
    customer_name = link.customer_name or llc_order.get("customer_name", "")
    customer_email = link.customer_email or llc_order.get("customer_email")
    customer_phone = link.customer_phone or llc_order.get("customer_phone")
    state = llc_order.get("state", "DC")
    business_name = llc_order.get("business_name", "")

    # Determine which documents to auto-add based on LLC order services/documents
    auto_docs = []

    # Articles of Organization — always needed for an LLC
    auto_docs.append(ApostilleDocument(
        doc_type="articles_of_organization",
        doc_description=f"Articles of Organization — {business_name} ({state})",
        state_of_origin=state,
        destination_country=link.destination_country,
        needs_notarization=False,
        needs_certification=True,
    ))

    # Operating Agreement — if the LLC order included OA generation
    llc_services = llc_order.get("services", [])
    llc_docs = llc_order.get("documents", [])
    llc_service_ids = []
    if isinstance(llc_services, list):
        for s in llc_services:
            if isinstance(s, str):
                llc_service_ids.append(s)
            elif isinstance(s, dict):
                llc_service_ids.append(s.get("id", ""))

    has_oa = any("oa" in sid.lower() for sid in llc_service_ids) or \
             any("operating" in str(d).lower() for d in llc_docs)

    if has_oa or True:  # Always include OA — it's standard
        auto_docs.append(ApostilleDocument(
            doc_type="operating_agreement",
            doc_description=f"Operating Agreement — {business_name}",
            state_of_origin=state,
            destination_country=link.destination_country,
            needs_notarization=True,
            needs_certification=False,
        ))

    # Certificate of Good Standing — if LLC order had it or always useful
    has_gs = any("good-standing" in sid or "good_standing" in sid for sid in llc_service_ids)
    if has_gs:
        auto_docs.append(ApostilleDocument(
            doc_type="certificate_of_good_standing",
            doc_description=f"Certificate of Good Standing — {business_name} ({state})",
            state_of_origin=state,
            destination_country=link.destination_country,
            needs_notarization=False,
            needs_certification=False,
        ))

    # EIN confirmation letter — if LLC had EIN service
    has_ein = any("ein" in sid.lower() for sid in llc_service_ids)
    if has_ein:
        auto_docs.append(ApostilleDocument(
            doc_type="corporate_document",
            doc_description=f"EIN Confirmation Letter — {business_name}",
            state_of_origin="federal",
            destination_country=link.destination_country,
            needs_notarization=False,
            needs_certification=False,
        ))

    # Create the apostille order
    order_create = ApostilleOrderCreate(
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        customer_id=llc_order.get("customer_id"),
        documents=auto_docs,
        rush=link.rush,
        shipping_method=link.shipping_method,
        shipping_address=link.shipping_address,
        notes=link.notes or f"Auto-created from LLC Factory order {llc_order_id}",
    )

    # Use the create_order function
    result = await create_order(order_create)

    # Add LLC link metadata
    result["metadata"] = {
        "source": "llcfactory",
        "llc_order_id": llc_order_id,
        "business_name": business_name,
        "state": state,
    }
    _save_json(ORDERS_DIR, f"{result['id']}.json", result)

    logger.info(f"ApostApp order {result['id']} created from LLC order {llc_order_id} — {len(auto_docs)} docs")
    return result
