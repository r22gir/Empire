"""
Main FastAPI application entry point for EmpireBox backend.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Create FastAPI app
app = FastAPI(
    title="EmpireBox API",
    description="Backend API for EmpireBox",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# LuxeForge Measurements router
try:
    from app.routers import luxeforge_measurements
    app.include_router(luxeforge_measurements.router, prefix="/api/luxeforge/measurements", tags=["luxeforge-measurements"])
except ImportError:
    pass

# Docker / System / Ollama management
load_router("app.routers.docker_manager", "/api/v1", ["docker"])
load_router("app.routers.system_monitor", "/api/v1", ["system"])
load_router("app.routers.ollama_manager", "/api/v1", ["ollama"])

@app.get("/")
async def root():
    return {"message": "EmpireBox API", "version": "1.0.0", "status": "operational"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "empirebox-backend"}


# Telegram Bot + Desk Scheduler auto-start
@app.on_event("startup")
async def start_background_services():
    import asyncio

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Notifications API
load_router("app.routers.notifications", "/api/v1", ["notifications"])

# Empire Task Engine — AI Desks, Tasks, Contacts
load_router("app.routers.desks", "/api/v1", ["desks"])
load_router("app.routers.tasks", "/api/v1", ["tasks"])
load_router("app.routers.contacts", "/api/v1", ["contacts"])

# Onboarding & Tier
load_router("app.routers.onboarding", "/api/v1", ["onboarding"])

# Smart Multi-Method Analyzer
try:
    from app.api.v1 import smart_analyzer
    app.include_router(smart_analyzer.router, prefix="/api/v1", tags=["Smart AI"])
    print("✓ Loaded: /api/v1/smart-analyze")
except Exception as e:
    print(f"✗ smart_analyzer: {e}")
