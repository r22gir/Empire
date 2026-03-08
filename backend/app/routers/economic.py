"""
Economic Intelligence API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
import uuid

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import User
from app.services.economic_service import EconomicService
from app.services.quality_evaluator import QualityEvaluator
from pydantic import BaseModel

router = APIRouter(tags=["economic"])


class QualityEvaluationRequest(BaseModel):
    """Request for quality evaluation."""
    listing_data: Dict[str, Any]
    category: Optional[str] = None


@router.get("/ledger/{entity_type}/{entity_id}")
async def get_ledger(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get economic ledger for an entity.
    
    Args:
        entity_type: Type of entity (user, listing, shipment, license)
        entity_id: UUID of the entity
    
    Returns:
        Ledger information
    """
    # Verify user has access to this entity
    if entity_type == "user" and str(current_user.id) != entity_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        entity_uuid = uuid.UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity_id format")
    
    economic_service = EconomicService(db)
    ledger = await economic_service.get_ledger(entity_type, entity_uuid)
    
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    return {
        "id": str(ledger.id),
        "entity_type": ledger.entity_type,
        "entity_id": str(ledger.entity_id),
        "balance": float(ledger.balance),
        "total_income": float(ledger.total_income),
        "total_costs": float(ledger.total_costs),
        "total_profit": float(ledger.total_profit),
        "status": ledger.status,
        "transaction_count": int(ledger.transaction_count),
        "last_transaction_at": ledger.last_transaction_at.isoformat() if ledger.last_transaction_at else None,
        "created_at": ledger.created_at.isoformat(),
        "updated_at": ledger.updated_at.isoformat() if ledger.updated_at else None,
    }


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive dashboard overview for current user.
    
    Returns:
        Dashboard data with ledger, metrics, and recent transactions
    """
    economic_service = EconomicService(db)
    overview = await economic_service.get_dashboard_overview("user", current_user.id)
    
    return overview


@router.get("/transactions")
async def get_transactions(
    entity_type: str = Query("user", description="Type of entity"),
    entity_id: Optional[str] = Query(None, description="UUID of entity (defaults to current user)"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of transactions"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get transaction history for an entity.
    
    Args:
        entity_type: Type of entity
        entity_id: UUID of entity (defaults to current user)
        transaction_type: Optional filter by transaction type
        limit: Maximum number of transactions
        offset: Offset for pagination
    
    Returns:
        List of transactions
    """
    # Default to current user if no entity_id provided
    if not entity_id:
        entity_id = str(current_user.id)
        entity_type = "user"
    
    # Verify user has access
    if entity_type == "user" and str(current_user.id) != entity_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        entity_uuid = uuid.UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity_id format")
    
    economic_service = EconomicService(db)
    transactions = await economic_service.get_transactions(
        entity_type=entity_type,
        entity_id=entity_uuid,
        transaction_type=transaction_type,
        limit=limit,
        offset=offset
    )
    
    return {
        "transactions": [
            {
                "id": str(t.id),
                "ledger_id": str(t.ledger_id),
                "entity_type": t.entity_type,
                "entity_id": str(t.entity_id),
                "transaction_type": t.transaction_type,
                "amount": float(t.amount),
                "currency": t.currency,
                "resource_details": t.resource_details,
                "quality_score": float(t.quality_score) if t.quality_score else None,
                "description": t.description,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ],
        "count": len(transactions),
        "limit": limit,
        "offset": offset,
    }


@router.get("/projects/{project_id}/efficiency")
async def get_project_efficiency(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get efficiency metrics for a project (listing in EmpireBox context).
    
    Args:
        project_id: UUID of the project/listing
    
    Returns:
        Efficiency metrics
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")
    
    economic_service = EconomicService(db)
    ledger = await economic_service.get_ledger("listing", project_uuid)
    
    if not ledger:
        raise HTTPException(status_code=404, detail="Project ledger not found")
    
    # Calculate efficiency metrics
    efficiency = 0.0
    if ledger.total_costs > 0:
        efficiency = float(ledger.total_income / ledger.total_costs * 100)
    
    cost_per_transaction = 0.0
    if ledger.transaction_count > 0:
        cost_per_transaction = float(ledger.total_costs / ledger.transaction_count)
    
    return {
        "project_id": project_id,
        "efficiency": round(efficiency, 2),
        "total_income": float(ledger.total_income),
        "total_costs": float(ledger.total_costs),
        "total_profit": float(ledger.total_profit),
        "cost_per_transaction": round(cost_per_transaction, 2),
        "transaction_count": int(ledger.transaction_count),
        "status": ledger.status,
    }


@router.post("/quality/evaluate")
async def evaluate_quality(
    request: QualityEvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluate quality of a listing or content.
    
    Args:
        request: Quality evaluation request with listing data
    
    Returns:
        Quality scores and feedback
    """
    # Ensure user_id is set in listing_data
    if "user_id" not in request.listing_data:
        request.listing_data["user_id"] = current_user.id
    
    quality_evaluator = QualityEvaluator(db)
    evaluation = await quality_evaluator.evaluate_listing(
        listing_data=request.listing_data,
        category=request.category
    )
    
    return evaluation


@router.post("/quality/evaluate-batch")
async def evaluate_quality_batch(
    listings: List[Dict[str, Any]] = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluate quality of multiple listings in batch.
    
    Args:
        listings: List of listing data dictionaries
    
    Returns:
        List of evaluations
    """
    # Ensure user_id is set for all listings
    for listing in listings:
        if "user_id" not in listing:
            listing["user_id"] = current_user.id
    
    quality_evaluator = QualityEvaluator(db)
    evaluations = await quality_evaluator.batch_evaluate_listings(listings)
    
    return {"evaluations": evaluations}


@router.get("/quality/prompt-example")
async def get_evaluation_prompt_example(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get an example LLM evaluation prompt.
    
    Useful for understanding how the quality evaluation works.
    
    Returns:
        Example prompt that would be sent to LLM
    """
    # Create sample listing data
    sample_listing = {
        "title": "Vintage Leather Jacket - Size M",
        "description": "Classic brown leather jacket in excellent condition. Made from genuine leather with full zip closure and side pockets. Perfect for casual wear.",
        "price": 79.99,
        "photos": ["photo1.jpg", "photo2.jpg", "photo3.jpg"],
        "condition": "like_new",
        "category": "clothing"
    }
    
    quality_evaluator = QualityEvaluator(db)
    prompt = await quality_evaluator.generate_llm_evaluation_prompt(
        listing_data=sample_listing,
        category="clothing"
    )
    
    return {
        "sample_listing": sample_listing,
        "llm_prompt": prompt
    }
