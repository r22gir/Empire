from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import licenses, shipping, preorders

app = FastAPI(
    title="EmpireBox API",
    description="Backend API for EmpireBox Setup Portal, License Management, and ShipForge",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(licenses.router, prefix="/licenses", tags=["licenses"])
app.include_router(shipping.router, prefix="/shipping", tags=["shipping"])
app.include_router(preorders.router, prefix="/preorders", tags=["preorders"])

@app.get("/")
async def root():
    return {
        "message": "EmpireBox API",
        "version": "1.0.0",
        "endpoints": {
            "licenses": "/licenses",
            "shipping": "/shipping",
            "preorders": "/preorders"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
