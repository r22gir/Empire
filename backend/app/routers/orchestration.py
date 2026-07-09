"""
MAX Orchestration Router
REST endpoints for autonomous orchestration control.
"""
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks
import httpx

from app.services.orchestration.orchestrator import orchestrator_instance
from app.services.orchestration.auto_quote import auto_quote_engine
from app.services.orchestration.production_scheduler import production_scheduler
from app.services.orchestration.payment_monitor import payment_monitor
from app.services.orchestration.inventory_manager import inventory_manager
from app.services.orchestration.client_notifier import client_notifier

router = APIRouter(prefix="/orchestration", tags=["orchestration"])

API = "http://localhost:8000/api/v1"


# ── Status & Health ─────────────────────────────────────────────────────────────

@router.get("/status")
async def get_business_health():
    """Return full business ecosystem health score."""
    backend_ok = await check_service("http://localhost:8000/health")
    frontend_ok = await check_service("http://localhost:3005")
    openclaw_ok = await check_service("http://localhost:7878/health")
    ollama_ok = await check_service("http://localhost:11434/api/tags")

    services = {
        "backend": backend_ok,
        "frontend": frontend_ok,
        "openclaw": openclaw_ok,
        "ollama": ollama_ok,
    }
    score = round(sum(100 for v in services.values() if v) / len(services))

    return {
        "health_score": score,
        "services": {k: "healthy" if v else "degraded" for k, v in services.items()},
        "orchestrator_enabled": orchestrator_instance.enabled,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def check_service(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            return r.is_success
    except Exception:
        return False


# ── Autonomous Mode ────────────────────────────────────────────────────────────

@router.post("/enable")
async def enable_orchestration(background_tasks: BackgroundTasks):
    """Enable autonomous orchestration loop."""
    from app.services.orchestration.daily_loop import start_scheduler
    start_scheduler()
    orchestrator_instance.enabled = True
    return {"enabled": True, "message": "Autonomous orchestration enabled"}


@router.post("/disable")
async def disable_orchestration():
    """Disable autonomous orchestration loop."""
    from app.services.orchestration.daily_loop import stop_scheduler
    stop_scheduler()
    orchestrator_instance.enabled = False
    return {"enabled": False, "message": "Autonomous orchestration disabled"}


# ── Auto-Quote ──────────────────────────────────────────────────────────────────

@router.post("/generate-quotes")
async def trigger_auto_quotes(client_id: str = None, image_url: str = None):
    """Manually trigger auto-quote for a client."""
    if not image_url:
        return {"error": "image_url required"}

    result = await auto_quote_engine.run_auto_quote(
        image_url=image_url,
        client_id=client_id or "manual",
        client_email="client@example.com",
        client_name="Client",
    )
    return result


# ── Production Scheduler ───────────────────────────────────────────────────────

@router.post("/optimize-schedule")
async def optimize_production_schedule():
    """Manually trigger production schedule optimization."""
    result = await production_scheduler.run_daily_optimization()
    return result


# ── Payment Follow-up ──────────────────────────────────────────────────────────

@router.post("/followup-invoices")
async def trigger_payment_followup():
    """Manually trigger payment follow-up scan."""
    result = await payment_monitor.run_hourly_scan()
    return result


# ── Inventory ──────────────────────────────────────────────────────────────────

@router.get("/inventory-status")
async def get_inventory_status():
    """Check current inventory levels and reorder status."""
    inventory = await inventory_manager.check_stock_levels()
    low_stock = inventory_manager.identify_low_stock(inventory)
    return {
        "total_materials": len(inventory.get("materials", [])),
        "low_stock_count": len(low_stock),
        "low_stock_materials": low_stock,
    }


# ── Client Notifications ───────────────────────────────────────────────────────

@router.post("/send-updates")
async def trigger_client_updates(job_id: str = None, stage: str = None):
    """Manually trigger client notification for a job stage change."""
    if job_id and stage:
        result = await client_notifier.on_job_stage_change(job_id, stage)
        return result
    return {"error": "job_id and stage required"}


# ── Orchestration Dashboard Data ───────────────────────────────────────────────

@router.get("/dashboard")
async def get_orchestration_dashboard():
    """Sprint 1d-fix: was returning hardcoded fake decisions and zero-value
    counters. Replaced with honest {'implemented': False} until real data
    is wired (the orchestrator.py module itself also has hardcoded sample
    data — to be replaced in a follow-up sprint)."""
    return {
        "implemented": False,
        "reason": "Sprint 1d-fix: previous response fabricated hardcoded metrics "
                  "(auto_quote_count=0, jobs_optimized=0, etc.) and four "
                  "fake 'decisions' entries (Production schedule optimized, "
                  "Low stock alert, Payment reminder, Auto-quote). Real data "
                  "wiring is queued for a follow-up sprint.",
        "metrics": {
            "auto_quotes_today": None,
            "jobs_optimized": None,
            "overdue_chased": None,
            "low_stock_alerts": None,
            "notifications_sent": None,
        },
        "decisions": [],
        "health": await check_ecosystem_health(),
        "timestamp": datetime.utcnow().isoformat(),
    }


async def check_ecosystem_health():
    """Sprint 1d-fix: was returning fabricated hardcoded data
    (tasks=60, desks=18, memories="3000+"). Replaced with honest
    {'implemented': False} response until real data is wired."""
    return {
        "implemented": False,
        "reason": "Sprint 1d-fix: previous response fabricated hardcoded metrics "
                  "(tasks=60, desks=18, memories='3000+'). Real data wiring "
                  "is queued for a follow-up sprint.",
        "services_checked_live": {
            "backend_up": await check_service("http://localhost:8000/health"),
            "frontend_up": await check_service("http://localhost:3005"),
            "openclaw_up": await check_service("http://localhost:7878/health"),
            "ollama_up": await check_service("http://localhost:11434/api/tags"),
        },
    }
