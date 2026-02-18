"""
Main FastAPI application entry point for EmpireBox backend.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Create FastAPI app
app = FastAPI(
    title="EmpireBox API",
    description="Backend API for EmpireBox - Setup Portal, License Management, ShipForge, and AI-powered marketplace automation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Get CORS origins from environment or use default
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers with error handling for missing modules
try:
    from app.routers import licenses
    app.include_router(licenses.router, prefix="/licenses", tags=["licenses"])
except ImportError:
    pass

try:
    from app.routers import shipping
    app.include_router(shipping.router, prefix="/shipping", tags=["shipping"])
except ImportError:
    pass

try:
    from app.routers import preorders
    app.include_router(preorders.router, prefix="/preorders", tags=["preorders"])
except ImportError:
    pass

try:
    from app.routers import auth
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
except ImportError:
    pass

try:
    from app.routers import users
    app.include_router(users.router, prefix="/users", tags=["users"])
except ImportError:
    pass

try:
    from app.routers import listings
    app.include_router(listings.router, prefix="/listings", tags=["listings"])
except ImportError:
    pass

try:
    from app.routers import messages
    app.include_router(messages.router, prefix="/messages", tags=["messages"])
except ImportError:
    pass

try:
    from app.routers import marketplaces
    app.include_router(marketplaces.router, prefix="/marketplaces", tags=["marketplaces"])
except ImportError:
    pass

try:
    from app.routers import webhooks
    app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
except ImportError:
    pass

try:
    from app.routers import ai
    app.include_router(ai.router, prefix="/ai", tags=["ai"])
except ImportError:
    pass

# SupportForge routers
try:
    from app.routers import supportforge_tickets
    app.include_router(supportforge_tickets.router, prefix="/api/v1/supportforge/tickets", tags=["supportforge-tickets"])
except ImportError:
    pass

try:
    from app.routers import supportforge_ai
    app.include_router(supportforge_ai.router, prefix="/api/v1/supportforge/ai", tags=["supportforge-ai"])
except ImportError:
    pass

try:
    from app.routers import supportforge_customers
    app.include_router(supportforge_customers.router, prefix="/api/v1/supportforge/customers", tags=["supportforge-customers"])
except ImportError:
    pass


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "message": "EmpireBox API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "licenses": "/licenses",
            "shipping": "/shipping",
            "preorders": "/preorders",
            "auth": "/auth",
            "users": "/users",
            "listings": "/listings",
            "messages": "/messages",
            "marketplaces": "/marketplaces",
            "webhooks": "/webhooks",
            "ai": "/ai",
            "supportforge": "/api/v1/supportforge"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "empirebox-backend"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)