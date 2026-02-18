"""
Main FastAPI application entry point for MarketForge backend.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, users, listings, messages, marketplaces, webhooks, ai

# Create FastAPI app
app = FastAPI(
    title="MarketForge API",
    description="Backend API for MarketForge - AI-powered marketplace automation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(listings.router)
app.include_router(messages.router)
app.include_router(marketplaces.router)
app.include_router(webhooks.router)
app.include_router(ai.router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "message": "MarketForge API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "marketforge-backend"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
