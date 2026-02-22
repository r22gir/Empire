"""
Main FastAPI application entry point for EmpireBox backend.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Create FastAPI app
app = FastAPI(
    title="EmpireBox API",
    description="Backend API for EmpireBox - Setup Portal, License Management, ShipForge, MarketF, SupportForge, Economic Intelligence, and AI-powered marketplace automation",
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
    if auth:
        app.include_router(auth.router, prefix="/auth", tags=["auth"])
except (ImportError, AttributeError):
    pass

try:
    from app.routers import users
    if users:
        app.include_router(users.router, prefix="/users", tags=["users"])
except (ImportError, AttributeError):
    pass

try:
    from app.routers import listings
    if listings:
        app.include_router(listings.router, prefix="/listings", tags=["listings"])
except (ImportError, AttributeError):
    pass

try:
    from app.routers import messages
    if messages:
        app.include_router(messages.router, prefix="/messages", tags=["messages"])
except (ImportError, AttributeError):
    pass

try:
    from app.routers import marketplaces
    if marketplaces:
        app.include_router(marketplaces.router, prefix="/marketplaces", tags=["marketplaces"])
except (ImportError, AttributeError):
    pass

try:
    from app.routers import webhooks
    if webhooks:
        app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
except (ImportError, AttributeError):
    pass

try:
    from app.routers import ai
    if ai:
        app.include_router(ai.router, prefix="/ai", tags=["ai"])
except (ImportError, AttributeError):
    pass

# SupportForge routers
try:
    from app.routers import supportforge_tickets
    app.include_router(supportforge_tickets.router, prefix="/api/v1/tickets", tags=["supportforge-tickets"])
except ImportError:
    pass

try:
    from app.routers import supportforge_customers
    app.include_router(supportforge_customers.router, prefix="/api/v1/customers", tags=["supportforge-customers"])
except ImportError:
    pass

try:
    from app.routers import supportforge_kb
    app.include_router(supportforge_kb.router, prefix="/api/v1/kb", tags=["supportforge-kb"])
except (ImportError, AttributeError):
    pass

try:
    from app.routers import supportforge_ai
    app.include_router(supportforge_ai.router, prefix="/api/v1/ai", tags=["supportforge-ai"])
except (ImportError, AttributeError):
    pass

# MarketF routers
try:
    from app.routers.marketplace import products, orders, reviews, seller
    app.include_router(products.router, prefix="/marketplace", tags=["marketplace-products"])
    app.include_router(orders.router, prefix="/marketplace", tags=["marketplace-orders"])
    app.include_router(reviews.router, prefix="/marketplace", tags=["marketplace-reviews"])
    app.include_router(seller.router, prefix="/marketplace", tags=["marketplace-seller"])
except ImportError:
    pass

# Crypto Payments router
try:
    from app.routers import crypto_payments
    app.include_router(crypto_payments.router, prefix="/api/v1/crypto-payments", tags=["crypto-payments"])
except ImportError:
    pass

# Economic Intelligence router
try:
    from app.routers import economic
    app.include_router(economic.router, prefix="/api/v1/economic", tags=["economic"])
except ImportError:
    pass

# Chat Backup and Decision Context router
try:
    from app.routers import chat_backup
    app.include_router(chat_backup.router, prefix="/api/v1/chat-backup", tags=["chat-backup"])
except ImportError:
    pass


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "message": "EmpireBox API",
        "version": "1.0.0",
        "status": "operational",
        "marketplace_fee": "8%",
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
            "marketplace_products": "/marketplace/products",
            "marketplace_orders": "/marketplace/orders",
            "marketplace_reviews": "/marketplace/reviews",
            "marketplace_seller": "/marketplace/seller",
            "supportforge_tickets": "/api/v1/tickets",
            "supportforge_customers": "/api/v1/customers",
            "supportforge_kb": "/api/v1/kb",
            "supportforge_ai": "/api/v1/ai",
            "economic": "/api/v1/economic",
            "chat_backup": "/api/v1/chat-backup",
            "crypto_payments": "/api/v1/crypto-payments"
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