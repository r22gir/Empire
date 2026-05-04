"""
System Admin Router — Service management endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.system.service_manager import service_manager

router = APIRouter(prefix="/api/v1/admin", tags=["System Admin"])


class StartRequest(BaseModel):
    force: bool = False


@router.get("/services")
async def list_services():
    """Get status of all registered services."""
    return service_manager.get_status()


@router.get("/services/{name}")
async def get_service(name: str):
    """Get detailed info about a specific service."""
    info = service_manager.get_service_info(name)
    if "error" in info:
        raise HTTPException(status_code=404, detail=info["error"])
    return info


@router.post("/services/{name}/start")
async def start_service(name: str, force: bool = False):
    """Start a service. Use force=true to kill conflicting processes on the port."""
    result = service_manager.start_service(name, force=force)
    if "error" in result and "conflict" in result.get("error", "").lower():
        raise HTTPException(status_code=409, detail=result)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/services/{name}/stop")
async def stop_service(name: str):
    """Stop a running service."""
    result = service_manager.stop_service(name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/services/{name}/restart")
async def restart_service(name: str):
    """Restart a service (stop + start with force)."""
    result = service_manager.restart_service(name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result
