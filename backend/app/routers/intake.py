from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/v1/intake", tags=["intake"])

# Models
class IntakeSubmission(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    project_type: str  # drapery, upholstery, roman-shades, banquette, other
    message: Optional[str] = None
    photos: Optional[List[str]] = None  # URLs or base64
    measurements: Optional[dict] = None
    budget_range: Optional[str] = None
    timeline: Optional[str] = None

class IntakeResponse(BaseModel):
    id: str
    status: str  # received, reviewing, quoted, approved, rejected
    created_at: datetime
    estimated_response: str

# In-memory store (replace with database in production)
_intake_submissions: dict[str, IntakeResponse] = {}

@router.post("", response_model=IntakeResponse)
async def submit_intake(
    submission: IntakeSubmission,
    background_tasks: BackgroundTasks
):
    """Submit a new project intake request"""
    
    # Generate unique ID
    intake_id = str(uuid.uuid4())
    
    # Create response record
    response = IntakeResponse(
        id=intake_id,
        status="received",
        created_at=datetime.utcnow(),
        estimated_response="24 hours"
    )
    
    # Store submission
    _intake_submissions[intake_id] = response
    
    # Background task: notify team via Telegram/Slack
    async def notify_team():
        # TODO: Integrate with notification service
        print(f"New intake: {submission.name} - {submission.project_type}")
        # await send_telegram_alert(f"New project inquiry from {submission.name}")
    
    background_tasks.add_task(notify_team)
    
    # Background task: auto-analyze photos if provided
    if submission.photos:
        async def analyze_photos():
            # TODO: Call vision API for photo analysis
            print(f"Analyzing {len(submission.photos)} photos for {intake_id}")
            # await call_vision_api(submission.photos)
        background_tasks.add_task(analyze_photos)
    
    return response

@router.get("/{intake_id}", response_model=IntakeResponse)
async def get_intake_status(intake_id: str):
    """Get status of an intake submission"""
    if intake_id not in _intake_submissions:
        raise HTTPException(status_code=404, detail="Intake not found")
    return _intake_submissions[intake_id]

@router.get("", response_model=List[IntakeResponse])
async def list_intakes(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List intake submissions (admin only)"""
    # TODO: Add authentication check
    results = list(_intake_submissions.values())
    
    if status:
        results = [r for r in results if r.status == status]
    
    return results[offset:offset + limit]

@router.patch("/{intake_id}/status")
async def update_intake_status(
    intake_id: str,
    new_status: str,
    notes: Optional[str] = None
):
    """Update intake status (admin only)"""
    # TODO: Add authentication check
    if intake_id not in _intake_submissions:
        raise HTTPException(status_code=404, detail="Intake not found")
    
    valid_statuses = ["received", "reviewing", "quoted", "approved", "rejected", "completed"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    _intake_submissions[intake_id].status = new_status
    
    # TODO: Log status change, notify client if needed
    return {"message": f"Status updated to {new_status}"}
