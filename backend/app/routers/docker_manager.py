# STATUS: PARTIAL — Docker SDK integration is real (docker.from_env()).
# Start/stop/status endpoints work if Docker is running and containers exist.
# Limitation: container names in PRODUCTS dict are aspirational — most containers
# are not yet built or deployed. Gracefully returns "not_found" for missing containers.

"""Docker Product Manager — start/stop/status for EmpireBox product containers."""
import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("docker_manager")

router = APIRouter()

# All 13 EmpireBox products and their Docker container names
PRODUCTS = {
    "workroom-forge": {"name": "Workroom Forge", "container": "workroom-forge", "port": 3001, "emoji": "🔨"},
    "luxeforge": {"name": "LuxeForge", "container": "luxeforge", "port": 3002, "emoji": "✨"},
    "install-forge": {"name": "Install Forge", "container": "install-forge", "port": 3003, "emoji": "🔧"},
    "quote-forge": {"name": "Quote Forge", "container": "quote-forge", "port": 3004, "emoji": "📝"},
    "max-ai": {"name": "MAX AI", "container": "max-ai", "port": 8000, "emoji": "🤖"},
    "openclaw": {"name": "OpenClaw AI", "container": "openclaw", "port": 7878, "emoji": "🦀"},
    "supportforge": {"name": "SupportForge", "container": "supportforge", "port": 3005, "emoji": "🎧"},
    "cryptopay": {"name": "CryptoPay", "container": "cryptopay", "port": 3006, "emoji": "💰"},
    "listingbot": {"name": "ListingBot", "container": "listingbot", "port": 3007, "emoji": "📦"},
    "shippingbot": {"name": "ShippingBot", "container": "shippingbot", "port": 3008, "emoji": "🚚"},
    "analytics": {"name": "Analytics", "container": "analytics", "port": 3010, "emoji": "📊"},
    "founder-dashboard": {"name": "Founder Dashboard", "container": "founder-dashboard", "port": 3009, "emoji": "🏰"},
    "marketplace-hub": {"name": "Marketplace Hub", "container": "marketplace-hub", "port": 3011, "emoji": "🏪"},
}


def _get_docker_client():
    try:
        import docker
        return docker.from_env()
    except Exception as e:
        logger.warning(f"Docker not available: {e}")
        return None


@router.get("/docker/status")
async def docker_status():
    """Get status of all product containers."""
    client = _get_docker_client()
    results = []
    for pid, info in PRODUCTS.items():
        status = "unknown"
        if client:
            try:
                container = client.containers.get(info["container"])
                status = container.status  # running, exited, paused, etc.
            except Exception:
                status = "not_found"
        results.append({
            "id": pid,
            "name": info["name"],
            "container": info["container"],
            "port": info["port"],
            "emoji": info["emoji"],
            "status": status,
        })
    return {"products": results}


@router.post("/docker/{product}/start")
async def docker_start(product: str):
    """Start a product container."""
    if product not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Unknown product: {product}")
    client = _get_docker_client()
    if not client:
        raise HTTPException(status_code=503, detail="Docker not available")
    info = PRODUCTS[product]
    try:
        container = client.containers.get(info["container"])
        if container.status == "running":
            return {"status": "already_running", "product": product}
        container.start()
        return {"status": "started", "product": product}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/docker/{product}/stop")
async def docker_stop(product: str):
    """Stop a product container."""
    if product not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Unknown product: {product}")
    client = _get_docker_client()
    if not client:
        raise HTTPException(status_code=503, detail="Docker not available")
    info = PRODUCTS[product]
    try:
        container = client.containers.get(info["container"])
        if container.status != "running":
            return {"status": "already_stopped", "product": product}
        container.stop(timeout=10)
        return {"status": "stopped", "product": product}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
