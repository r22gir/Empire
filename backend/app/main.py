"""
Main FastAPI application entry point for EmpireBox backend.
"""
from pathlib import Path
from dotenv import load_dotenv

# Load .env before anything reads os.getenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.rate_limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
import os

# Create FastAPI app
app = FastAPI(
    title="EmpireBox API",
    description="Backend API for EmpireBox",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# No-cache middleware — EVERY response gets anti-cache headers
# This prevents phones/browsers/CDNs from serving stale data
@app.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Surrogate-Control"] = "no-store"
    response.headers["CDN-Cache-Control"] = "no-store"
    return response

# Helper to safely load routers
def load_router(module_path, prefix, tags):
    try:
        import importlib
        module = importlib.import_module(module_path)
        if hasattr(module, 'router') and module.router:
            app.include_router(module.router, prefix=prefix, tags=tags)
            print(f"✓ Loaded: {prefix}")
        else:
            print(f"✗ No router in: {module_path}")
    except Exception as e:
        print(f"✗ Failed {module_path}: {e}")

# MAX AI Router (primary)
load_router("app.routers.max", "", ["max"])
load_router("app.routers.max", "/api/v1", ["api-v1"])

# Files API
load_router("app.api.v1.files", "/api/v1", ["files"])

# Chat History API

# Quote Requests API (LuxeForge)
load_router("app.api.v1.quote_requests", "/api/v1", ["quote-requests"])
load_router("app.api.v1.chats", "/api/v1", ["chats"])

# Security/License API
load_router("app.api.v1.license", "/api/v1", ["license"])

# Other routers
load_router("app.routers.licenses", "/licenses", ["licenses"])
load_router("app.routers.shipping", "/shipping", ["shipping"])
load_router("app.routers.preorders", "/preorders", ["preorders"])
load_router("app.routers.auth", "/auth", ["auth"])
load_router("app.routers.users", "/users", ["users"])
load_router("app.routers.listings", "/listings", ["listings"])
load_router("app.routers.relist", "/api/v1", ["relist"])
load_router("app.routers.relistapp", "/api/v1", ["relistapp"])
load_router("app.routers.presentations", "/api/v1", ["presentations"])
load_router("app.routers.messages", "/messages", ["messages"])
load_router("app.routers.marketplaces", "/marketplaces", ["marketplaces"])
load_router("app.routers.webhooks", "/webhooks", ["webhooks"])
load_router("app.routers.ai", "/ai", ["ai"])
load_router("app.routers.supportforge_tickets", "/api/v1/tickets", ["supportforge"])
load_router("app.routers.supportforge_customers", "/api/v1/customers", ["supportforge"])
load_router("app.routers.supportforge_kb", "/api/v1/kb", ["supportforge"])
load_router("app.routers.supportforge_ai", "/api/v1/ai", ["supportforge"])
load_router("app.routers.crypto_payments", "/api/v1/crypto-payments", ["crypto"])
load_router("app.routers.economic", "/api/v1/economic", ["economic"])
load_router("app.routers.chat_backup", "/api/v1/chat-backup", ["chat-backup"])
load_router("app.routers.memory", "/api/v1", ["memory"])
load_router("app.routers.quotes", "/api/v1", ["quotes"])
load_router("app.routers.inbox", "/api/v1", ["inbox"])

# CraftForge — CNC & 3D print business
load_router("app.routers.craftforge", "/api/v1/craftforge", ["craftforge"])
load_router("app.routers.socialforge", "/api/v1/socialforge", ["socialforge"])
load_router("app.routers.social_setup", "/api/v1", ["social-setup"])

# Avatar / Presentation Mode
load_router("app.routers.avatar", "/api/v1", ["avatar"])

# RecoveryForge — Layer 3 classifier status/control
load_router("app.routers.recovery", "/api/v1", ["recovery"])

# Dev Panel API
load_router("app.routers.dev", "/api/v1", ["dev"])

# AI Cost Tracker
load_router("app.routers.costs", "/api/v1", ["costs"])

# MAX Accuracy Monitor
load_router("app.routers.accuracy", "/api/v1", ["accuracy"])

# Finance, CRM, Inventory
load_router("app.routers.finance", "/api/v1", ["finance"])
load_router("app.routers.payments", "/api/v1", ["payments"])
load_router("app.routers.crypto_checkout", "/api/v1", ["crypto-checkout"])
load_router("app.routers.emails", "/api/v1", ["emails"])
load_router("app.routers.customer_mgmt", "/api/v1", ["crm"])
load_router("app.routers.inventory", "/api/v1", ["inventory"])
# load_router("app.routers.jobs", "/api/v1", ["jobs"])  # replaced by jobs_unified
load_router("app.routers.jobs_unified", "/api/v1", ["jobs-unified"])

# LuxeForge FREE — Public intake portal
load_router("app.routers.intake_auth", "/api/v1/intake", ["intake"])

# AMP — Actitud Mental Positiva platform
load_router("app.routers.amp", "/api/v1/amp", ["amp"])

# LLC Factory — Business formation services (DC/MD/VA)
load_router("app.routers.llcfactory", "/api/v1", ["llcfactory"])

# ApostApp — Document apostille & authentication service (DC/MD/VA)
load_router("app.routers.apostapp", "/api/v1", ["apostapp"])

# ConstructionForge — Colombian real estate land development
load_router("app.routers.construction", "/api/v1", ["construction"])

# StoreFrontForge — Retail store management / POS
load_router("app.routers.storefront", "/api/v1", ["storefront"])

# Notes-to-Quote extraction + diagrams
load_router("app.routers.notes_extraction", "/api/v1", ["notes-extraction"])

# Pattern Template Generator — sewing pattern math + PDF export
load_router("app.routers.pattern_templates", "/api/v1/patterns", ["patterns"])
load_router("app.routers.custom_shapes", "/api/v1", ["custom-shapes"])

# Drawing Studio — architectural bench drawings (SVG + PDF)
load_router("app.routers.drawings", "/api/v1", ["drawings"])

# Fabric Library
load_router("app.routers.fabrics", "/api/v1/fabrics", ["fabrics"])

# Unified Photo Storage
load_router("app.routers.photos", "/api/v1", ["photos"])

# Vision analysis (measurement, mockup, outline, upholstery, image gen)
load_router("app.routers.vision", "", ["vision"])

# AI Analysis Sessions (save/load for PhotoAnalysisPanel)
load_router("app.routers.analysis_sessions", "/api/v1", ["analysis-sessions"])

# LuxeForge Measurements router
try:
    from app.models.luxeforge_measurement import ImageMeasurement  # noqa: ensure model is registered
    from app.routers import luxeforge_measurements
    app.include_router(luxeforge_measurements.router, prefix="/api/luxeforge/measurements", tags=["luxeforge-measurements"])
except ImportError:
    pass

# Create measurement table (avoid create_all due to JSONB in other models)
try:
    from app.database import engine
    ImageMeasurement.__table__.create(bind=engine, checkfirst=True)
except Exception as e:
    print(f"✗ Measurement table init: {e}")

# OpenClaw Bridge — MAX→OpenClaw autonomous task dispatch
load_router("app.routers.openclaw_bridge", "", ["openclaw"])

# OpenClaw Task Queue — persistent task queue with worker
load_router("app.routers.openclaw_tasks", "", ["openclaw-tasks"])

# Docker / System / Ollama management
load_router("app.routers.docker_manager", "/api/v1", ["docker"])
load_router("app.routers.system_monitor", "/api/v1", ["system"])
load_router("app.routers.ollama_manager", "/api/v1", ["ollama"])

# Serve intake uploads as static files
from fastapi.staticfiles import StaticFiles
_intake_uploads = os.path.expanduser("~/empire-repo/backend/data/intake_uploads")
os.makedirs(_intake_uploads, exist_ok=True)
app.mount("/intake_uploads", StaticFiles(directory=_intake_uploads), name="intake_uploads")

@app.get("/")
async def root():
    return {"message": "EmpireBox API", "version": "1.0.0", "status": "operational"}


# ── Alias routes (fix 404s for common frontend paths) ──────────────
from fastapi.responses import RedirectResponse

# invoices_alias removed — /api/v1/invoices now served by jobs_unified router
# Legacy finance invoices still available at /api/v1/finance/invoices

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "empirebox-backend"}


# ── STT endpoint (top-level for frontend compatibility) ──
from fastapi import UploadFile, File as FileParam

async def _do_transcribe(upload: UploadFile, language: str = "en"):
    """Shared transcription logic for both /api/transcribe and /api/v1/voice/transcribe."""
    from app.services.max.stt_service import stt_service
    from fastapi import HTTPException as _HTTPException
    import tempfile
    from pathlib import Path as _Path

    if not stt_service.is_configured:
        raise _HTTPException(status_code=503, detail="STT not configured — GROQ_API_KEY missing")

    suffix = _Path(upload.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await upload.read()
        tmp.write(content)
        tmp_path = _Path(tmp.name)

    try:
        transcript = await stt_service.transcribe(tmp_path, language=language)
        return {"text": transcript, "language": language, "filename": upload.filename}
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/api/transcribe")
async def api_transcribe(file: UploadFile = FileParam(...), language: str = "en"):
    """Transcribe uploaded audio via Groq Whisper (legacy endpoint, accepts 'file' field)."""
    return await _do_transcribe(file, language)


@app.post("/api/v1/voice/transcribe")
async def api_voice_transcribe(audio: UploadFile = FileParam(...), language: str = "en"):
    """Transcribe uploaded audio via Groq Whisper. Accepts 'audio' field name."""
    return await _do_transcribe(audio, language)


# Telegram Bot + Desk Scheduler auto-start
#
# When running with multiple uvicorn workers (--workers N), each worker fires
# its own "startup" event.  Singleton services like the Telegram polling loop
# must only run in ONE worker, otherwise they fight over getUpdates and crash.
# We use a simple file-lock: the first worker to acquire it becomes the
# "primary" and starts all singleton background services.
#
_WORKER_LOCK_PATH = Path("/tmp/empire_primary_worker.lock")
_worker_lock_file = None  # keep reference so the lock is held for process lifetime


def _acquire_primary_worker_lock() -> bool:
    """Try to become the primary worker by acquiring an exclusive file lock.

    Returns True if this process now holds the lock (i.e. is the primary).
    The lock is held for the lifetime of the process via the module-level
    ``_worker_lock_file`` reference.
    """
    import fcntl
    global _worker_lock_file
    try:
        _worker_lock_file = open(_WORKER_LOCK_PATH, "w")
        fcntl.flock(_worker_lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _worker_lock_file.write(str(os.getpid()))
        _worker_lock_file.flush()
        return True
    except (OSError, IOError):
        # Another worker already holds the lock
        if _worker_lock_file:
            _worker_lock_file.close()
            _worker_lock_file = None
        return False


@app.on_event("startup")
async def start_background_services():
    import asyncio

    is_primary = _acquire_primary_worker_lock()

    if not is_primary:
        print("⏭ Secondary worker — skipping singleton background services")
        return

    print("★ Primary worker — starting singleton background services")

    # Telegram Bot
    try:
        from app.services.max.telegram_bot import telegram_bot
        if telegram_bot.is_configured:
            asyncio.create_task(telegram_bot.start_bot())
            print("✓ Telegram Bot: starting in background")
        else:
            print("✗ Telegram Bot: not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_FOUNDER_CHAT_ID)")
    except Exception as e:
        print(f"✗ Telegram Bot: {e}")

    # Desk Scheduler
    try:
        from app.services.max.desks.desk_scheduler import desk_scheduler
        asyncio.create_task(desk_scheduler.start())
        print("✓ Desk Scheduler: starting in background")
    except Exception as e:
        print(f"✗ Desk Scheduler: {e}")

    # MAX Autonomous Scheduler (daily briefs, task checks, reports)
    try:
        from app.services.max.scheduler import max_scheduler
        await max_scheduler.start()
        status = max_scheduler.get_status()
        print(f"✓ MAX Scheduler: {len(status['jobs'])} jobs scheduled")
        for job in status['jobs']:
            print(f"  → {job['name']} — next: {job['next_run']}")
    except Exception as e:
        print(f"✗ MAX Scheduler: {e}")

    # MAX Proactive Monitor (overdue tasks, inbox, system health)
    try:
        from app.services.max.monitor import max_monitor
        await max_monitor.start()
        print(f"✓ MAX Monitor: checking every {max_monitor.get_status()['interval_seconds']}s")
    except Exception as e:
        print(f"✗ MAX Monitor: {e}")

    # OpenClaw Worker Loop — polls task queue, dispatches tasks
    try:
        from app.services.openclaw_worker import openclaw_worker_loop
        asyncio.create_task(openclaw_worker_loop())
        print("✓ OpenClaw Worker: polling task queue every 30s")
    except Exception as e:
        print(f"✗ OpenClaw Worker: {e}")

    # Task Auto-Execution Worker — polls todo tasks every 30s, routes to desks
    try:
        asyncio.create_task(_task_auto_worker())
        print("✓ Task Auto-Worker: polling todo tasks every 30s")
    except Exception as e:
        print(f"✗ Task Auto-Worker: {e}")

    # ── Autonomous Startup Probes ──
    # Run immediate health check + brain context warm-up on boot
    asyncio.create_task(_startup_probes())


async def _task_auto_worker():
    """Background worker that polls the tasks table every 30s for todo tasks and executes them.

    Only picks up tasks that are status='todo' and were created by 'max' or have
    source='tool' — avoids auto-executing manually created tasks the founder may
    want to review first.  Limits to 3 tasks per cycle to avoid overloading desks.
    """
    import asyncio
    await asyncio.sleep(15)  # Let startup finish before first poll

    from app.db.database import get_db, dict_rows
    from app.services.max.desks.desk_manager import desk_manager

    desk_manager.initialize()
    logger_prefix = "🔄 TaskWorker"
    print(f"{logger_prefix}: started — polling every 30s")

    while True:
        try:
            with get_db() as conn:
                rows = conn.execute(
                    """SELECT id, title, description, priority, desk, created_by
                       FROM tasks
                       WHERE status = 'todo'
                         AND (created_by = 'max' OR metadata LIKE '%"auto_execute"%')
                       ORDER BY
                           CASE priority
                               WHEN 'urgent' THEN 0 WHEN 'high' THEN 1
                               WHEN 'normal' THEN 2 WHEN 'low' THEN 3
                           END,
                           created_at ASC
                       LIMIT 3""",
                ).fetchall()
                todo_tasks = dict_rows(rows) if rows else []

            for task_row in todo_tasks:
                tid = task_row["id"]
                title = task_row["title"]
                try:
                    # Mark in_progress immediately
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE tasks SET status = 'in_progress', updated_at = datetime('now') WHERE id = ? AND status = 'todo'",
                            (tid,),
                        )
                        conn.execute(
                            "INSERT INTO task_activity (task_id, actor, action, detail, created_at) VALUES (?, 'task_worker', 'status_changed', 'Auto-worker picked up task', datetime('now'))",
                            (tid,),
                        )

                    result = await asyncio.wait_for(
                        desk_manager.submit_task(
                            title=title,
                            description=task_row.get("description") or title,
                            priority=task_row.get("priority", "normal"),
                            source="task_worker",
                            db_task_id=tid,
                        ),
                        timeout=60.0,
                    )

                    state = result.state.value if hasattr(result.state, "value") else str(result.state)
                    print(f"{logger_prefix}: {title} → {state}")

                    # Send Telegram notification on completion/failure
                    try:
                        from app.services.max.telegram_bot import telegram_bot
                        if telegram_bot.is_configured:
                            emoji = "✅" if state == "completed" else "❌" if state == "failed" else "⏳"
                            summary = (result.result or "")[:200]
                            await telegram_bot.send_message(
                                f"{emoji} <b>Task Auto-Executed</b>\n<b>{title}</b>\nStatus: {state}\n{summary}",
                            )
                    except Exception:
                        pass  # Telegram is best-effort

                except asyncio.TimeoutError:
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE tasks SET status = 'todo', updated_at = datetime('now') WHERE id = ?",
                            (tid,),
                        )
                    print(f"{logger_prefix}: {title} — timed out, reset to todo")
                except Exception as e:
                    print(f"{logger_prefix}: {title} — error: {e}")

        except Exception as e:
            print(f"{logger_prefix}: poll error: {e}")

        await asyncio.sleep(30)


async def _startup_probes():
    """Run autonomous probes immediately after startup.

    1. Warm up brain context cache so first user message is fast
    2. Run immediate service health check
    3. Check for pending urgent tasks and attempt execution
    4. Log startup event to MAX memory
    """
    import asyncio
    await asyncio.sleep(5)  # Let all services finish initializing

    startup_time = __import__('datetime').datetime.now()
    print("🧠 Running autonomous startup probes...")

    # 1. Warm up brain context
    try:
        from app.services.max.system_prompt import get_max_brain_context
        ctx = get_max_brain_context()
        print(f"  ✓ Brain context warmed: {len(ctx)} chars")
    except Exception as e:
        print(f"  ✗ Brain context warm-up: {e}")

    # 2. Immediate service health check
    try:
        import socket
        services = {"Backend API": 8000, "Command Center": 3005, "OpenClaw": 7878, "Ollama": 11434}
        online = []
        offline = []
        for name, port in services.items():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect(("127.0.0.1", port))
                s.close()
                online.append(name)
            except (ConnectionRefusedError, OSError):
                offline.append(name)
        print(f"  ✓ Services: {len(online)} online, {len(offline)} offline")
        if offline:
            print(f"    Offline: {', '.join(offline)}")
    except Exception as e:
        print(f"  ✗ Health check: {e}")

    # 3. Check for pending urgent tasks and attempt immediate execution
    try:
        from app.db.database import get_db
        with get_db() as conn:
            urgent_rows = conn.execute(
                """SELECT id, title, desk FROM tasks
                   WHERE status = 'todo' AND priority IN ('urgent', 'high')
                   ORDER BY created_at ASC LIMIT 3""",
            ).fetchall()

        if urgent_rows:
            print(f"  ⚡ Found {len(urgent_rows)} urgent/high tasks — attempting execution")
            try:
                from app.services.max.desks.desk_manager import desk_manager
                desk_manager.initialize()
                for row in urgent_rows:
                    try:
                        task = await desk_manager.submit_task(
                            title=row["title"],
                            description=f"Auto-executing urgent task {row['id']} on startup",
                            priority="high",
                            source="startup_probe",
                        )
                        state = task.state.value if hasattr(task.state, 'value') else str(task.state)
                        print(f"    → {row['title']}: {state}")
                        # Update the original task status
                        if state == "completed":
                            with get_db() as conn2:
                                conn2.execute(
                                    "UPDATE tasks SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                    (row["id"],),
                                )
                    except Exception as te:
                        print(f"    → {row['title']}: failed ({te})")
            except Exception as me:
                print(f"  ✗ Task execution: {me}")
        else:
            print("  ✓ No urgent tasks pending")
    except Exception as e:
        print(f"  ✗ Task check: {e}")

    # 4. Log startup to MAX memory
    try:
        from app.services.max.brain.memory_store import MemoryStore
        store = MemoryStore()
        store.add_memory(
            category="session_update",
            subcategory="startup",
            subject=f"MAX started {startup_time.strftime('%Y-%m-%d %H:%M')}",
            content=f"Backend started at {startup_time.isoformat()}. "
                    f"Services online: {', '.join(online) if online else 'checking...'}. "
                    f"Offline: {', '.join(offline) if offline else 'none'}. "
                    f"Urgent tasks: {len(urgent_rows) if 'urgent_rows' in dir() else 'unknown'}.",
            importance=6,
            source="startup",
            tags=["startup", "auto", "session_update"],
        )
        print("  ✓ Startup logged to MAX memory")
    except Exception as e:
        print(f"  ✗ Memory log: {e}")

    elapsed = (__import__('datetime').datetime.now() - startup_time).total_seconds()
    print(f"🧠 Startup probes complete ({elapsed:.1f}s)")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Notifications API
load_router("app.routers.notifications", "/api/v1", ["notifications"])

# Empire Task Engine — AI Desks, Tasks, Contacts
load_router("app.routers.desks", "/api/v1", ["desks"])
load_router("app.routers.tasks", "/api/v1", ["tasks"])
load_router("app.routers.contacts", "/api/v1", ["contacts"])

# LeadForge — Lead generation & sales machine
load_router("app.routers.leadforge", "/api/v1", ["leadforge"])

# Onboarding & Tier
load_router("app.routers.onboarding", "/api/v1", ["onboarding"])

# Smart Multi-Method Analyzer
try:
    from app.api.v1 import smart_analyzer
    app.include_router(smart_analyzer.router, prefix="/api/v1", tags=["Smart AI"])
    print("✓ Loaded: /api/v1/smart-analyze")
except Exception as e:
    print(f"✗ smart_analyzer: {e}")
