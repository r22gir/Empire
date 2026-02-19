"""
EmpireBox Control Center API
Fleet management for customer units
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

app = FastAPI(
    title="EmpireBox Control Center",
    description="Fleet management API for EmpireBox customer units",
    version="1.0.0",
)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
CONTROL_API_KEY = os.getenv("CONTROL_API_KEY", "")


def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    if not CONTROL_API_KEY or api_key != CONTROL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


# ── In-memory store (replace with DB in production) ──────────────────────────
_units: dict[str, dict] = {}
_licenses: dict[str, dict] = {}
_heartbeats: list[dict] = []


# ── Models ────────────────────────────────────────────────────────────────────
class UnitAction(BaseModel):
    action: str  # suspend | revoke | upgrade | reactivate
    reason: Optional[str] = None


class HeartbeatPayload(BaseModel):
    unit_id: str
    license_key: str
    hostname: Optional[str] = None
    ip: Optional[str] = None
    version: Optional[str] = None
    uptime_seconds: Optional[int] = None


class LicenseRequest(BaseModel):
    customer_name: str
    customer_email: str
    plan: str = "standard"
    valid_days: int = 365


# ── Fleet Endpoints ───────────────────────────────────────────────────────────
@app.get("/fleet", tags=["Fleet"])
def list_fleet(_: str = Depends(verify_api_key)):
    """List all registered customer units."""
    return {"units": list(_units.values()), "total": len(_units)}


@app.get("/fleet/{unit_id}", tags=["Fleet"])
def get_unit(unit_id: str, _: str = Depends(verify_api_key)):
    """Get details for a specific unit."""
    unit = _units.get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@app.post("/fleet/{unit_id}/action", tags=["Fleet"])
def unit_action(unit_id: str, payload: UnitAction, _: str = Depends(verify_api_key)):
    """Execute an action on a customer unit."""
    unit = _units.get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    valid_actions = {"suspend", "revoke", "upgrade", "reactivate"}
    if payload.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {valid_actions}",
        )

    unit["status"] = payload.action
    unit["last_action"] = {
        "action": payload.action,
        "reason": payload.reason,
        "timestamp": datetime.utcnow().isoformat(),
    }
    return {"unit_id": unit_id, "action": payload.action, "status": "applied"}


# ── Heartbeat ─────────────────────────────────────────────────────────────────
@app.post("/heartbeat", tags=["Heartbeat"])
def heartbeat(payload: HeartbeatPayload):
    """Customer units phone home here."""
    now = datetime.utcnow().isoformat()

    # Register unit if new
    if payload.unit_id not in _units:
        _units[payload.unit_id] = {
            "unit_id": payload.unit_id,
            "status": "active",
            "registered_at": now,
        }

    # Update unit info
    _units[payload.unit_id].update(
        {
            "hostname": payload.hostname,
            "ip": payload.ip,
            "version": payload.version,
            "last_seen": now,
            "uptime_seconds": payload.uptime_seconds,
        }
    )

    _heartbeats.append({"unit_id": payload.unit_id, "timestamp": now})

    # Check unit status — if suspended/revoked, tell unit to stop
    unit_status = _units[payload.unit_id].get("status", "active")
    return {
        "status": unit_status,
        "action": "stop" if unit_status in {"suspend", "revoke"} else "continue",
        "timestamp": now,
    }


# ── License Management ────────────────────────────────────────────────────────
@app.post("/license/generate", tags=["License"])
def generate_license(payload: LicenseRequest, _: str = Depends(verify_api_key)):
    """Generate a new license key."""
    key = f"EMP-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow().isoformat()
    _licenses[key] = {
        "key": key,
        "customer_name": payload.customer_name,
        "customer_email": payload.customer_email,
        "plan": payload.plan,
        "status": "active",
        "created_at": now,
        "valid_days": payload.valid_days,
    }
    return {"license_key": key, "details": _licenses[key]}


@app.get("/license/validate/{key}", tags=["License"])
def validate_license(key: str):
    """Validate a license key (public endpoint for customer units)."""
    license_data = _licenses.get(key)
    if not license_data:
        return {"valid": False, "reason": "License not found"}
    if license_data.get("status") != "active":
        return {"valid": False, "reason": f"License is {license_data['status']}"}
    return {"valid": True, "plan": license_data["plan"]}


# ── Metrics ───────────────────────────────────────────────────────────────────
@app.get("/metrics/overview", tags=["Metrics"])
def metrics_overview(_: str = Depends(verify_api_key)):
    """Fleet-wide metrics overview."""
    statuses = {}
    for unit in _units.values():
        s = unit.get("status", "unknown")
        statuses[s] = statuses.get(s, 0) + 1

    return {
        "total_units": len(_units),
        "total_licenses": len(_licenses),
        "total_heartbeats": len(_heartbeats),
        "units_by_status": statuses,
        "active_licenses": sum(
            1 for lic in _licenses.values() if lic.get("status") == "active"
        ),
        "generated_at": datetime.utcnow().isoformat(),
    }


@app.get("/health", tags=["System"])
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "control-center", "version": "1.0.0"}
