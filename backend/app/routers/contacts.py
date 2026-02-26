"""
Empire Contacts — API routes for client, contractor, vendor contacts.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import json

from app.db.database import get_db, dict_row, dict_rows

router = APIRouter(prefix="/contacts", tags=["contacts"])


class ContactCreate(BaseModel):
    name: str
    type: str  # client, contractor, vendor, other
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None


def _enrich_contact(contact: dict) -> dict:
    if contact:
        contact["metadata"] = json.loads(contact["metadata"]) if contact.get("metadata") else {}
    return contact


@router.get("/")
def list_contacts(
    type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List contacts with optional filters."""
    clauses = []
    params = []

    if type:
        clauses.append("type = ?")
        params.append(type)
    if search:
        clauses.append("(name LIKE ? OR email LIKE ? OR phone LIKE ?)")
        q = f"%{search}%"
        params.extend([q, q, q])

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM contacts{where} ORDER BY name LIMIT ? OFFSET ?",
            params,
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM contacts{where}", params[:-2]
        ).fetchone()[0]

        return {
            "contacts": [_enrich_contact(dict_row(r)) for r in rows],
            "total": total,
        }


@router.post("/")
def create_contact(contact: ContactCreate):
    """Create a new contact."""
    valid_types = ("client", "contractor", "vendor", "other")
    if contact.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"type must be one of {valid_types}")

    with get_db() as conn:
        conn.execute(
            """INSERT INTO contacts (id, name, type, phone, email, address, notes, metadata)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?)""",
            (
                contact.name,
                contact.type,
                contact.phone,
                contact.email,
                contact.address,
                contact.notes,
                json.dumps(contact.metadata) if contact.metadata else None,
            ),
        )
        row = conn.execute(
            "SELECT * FROM contacts ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return {"contact": _enrich_contact(dict_row(row))}


@router.get("/{contact_id}")
def get_contact(contact_id: str):
    """Get a single contact."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Contact not found")
        return {"contact": _enrich_contact(dict_row(row))}


@router.patch("/{contact_id}")
def update_contact(contact_id: str, update: ContactUpdate):
    """Update a contact."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM contacts WHERE id = ?", (contact_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Contact not found")

        data = update.model_dump(exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")

        if "type" in data:
            valid_types = ("client", "contractor", "vendor", "other")
            if data["type"] not in valid_types:
                raise HTTPException(status_code=400, detail=f"type must be one of {valid_types}")

        fields = []
        values = []
        for key, val in data.items():
            if key == "metadata":
                val = json.dumps(val)
            fields.append(f"{key} = ?")
            values.append(val)

        fields.append("updated_at = datetime('now')")
        values.append(contact_id)

        conn.execute(
            f"UPDATE contacts SET {', '.join(fields)} WHERE id = ?", values
        )
        return get_contact(contact_id)


@router.delete("/{contact_id}")
def delete_contact(contact_id: str):
    """Permanently delete a contact."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM contacts WHERE id = ?", (contact_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Contact not found")
        conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        return {"status": "deleted", "contact_id": contact_id}
