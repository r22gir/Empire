from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.routers.marketplace import products, orders, reviews, seller

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MarketF API",
    description="Peer-to-peer marketplace platform with 8% fees, integrated shipping, and escrow payments",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(reviews.router)
app.include_router(seller.router)


@app.get("/")
def root():
    return {
        "message": "MarketF API",
        "version": "1.0.0",
        "features": {
            "marketplace_fee": "8%",
            "escrow_payments": True,
            "integrated_shipping": True
        }
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
