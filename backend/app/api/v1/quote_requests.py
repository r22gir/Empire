from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import json
import os

router = APIRouter(prefix="/quote-requests", tags=["quote-requests"])

REQUESTS_FILE = os.path.expanduser("~/empire-repo/backend/data/quote_requests.json")

class QuoteRequest(BaseModel):
    name: str
    phone: str
    message: str
    photos: List[str] = []

def load_requests():
    os.makedirs(os.path.dirname(REQUESTS_FILE), exist_ok=True)
    if os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_requests(requests):
    os.makedirs(os.path.dirname(REQUESTS_FILE), exist_ok=True)
    with open(REQUESTS_FILE, 'w') as f:
        json.dump(requests, f, indent=2)

@router.post("")
async def create_quote_request(request: QuoteRequest):
    requests = load_requests()
    new_request = {
        "id": str(uuid.uuid4()),
        "name": request.name,
        "phone": request.phone,
        "message": request.message,
        "photos": request.photos,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "quote": None
    }
    requests.append(new_request)
    save_requests(requests)
    return {"status": "success", "request": new_request}

@router.get("")
async def list_quote_requests():
    return {"requests": load_requests()}

@router.get("/{request_id}")
async def get_quote_request(request_id: str):
    requests = load_requests()
    for req in requests:
        if req["id"] == request_id:
            return req
    raise HTTPException(status_code=404, detail="Request not found")

@router.post("/{request_id}/quote")
async def send_quote(request_id: str, quote: dict):
    requests = load_requests()
    for req in requests:
        if req["id"] == request_id:
            req["quote"] = quote
            req["status"] = "quoted"
            save_requests(requests)
            return {"status": "success", "request": req}
    raise HTTPException(status_code=404, detail="Request not found")

# AI Photo Measurement Analyzer
from typing import Dict
import base64
import re

from app.services.ollama_vision_router import generate_vision_response

@router.post("/analyze-photo")
async def analyze_photo(data: dict):
    """
    AI-powered photo analysis for window measurements.
    Analyzes proportions and estimates dimensions.
    """
    image_data = data.get("image", "")
    reference_width = data.get("reference_width")  # Optional: known reference object width in inches
    
    # Extract base64 image data
    if "base64," in image_data:
        image_data = image_data.split("base64,")[1]
    
    # Call Ollama for vision analysis
    import httpx
    
    prompt = """Analyze this window/room photo for a custom drapery workroom. Identify and estimate:

1. WINDOW DIMENSIONS:
   - Estimated width (in inches)
   - Estimated height (in inches)
   - Window type (single, double-hung, casement, picture, sliding, bay)

2. MOUNT TYPE RECOMMENDATION:
   - Inside mount vs outside mount
   - Ceiling mount possibility
   - Distance from ceiling to window top

3. ROOM CONTEXT:
   - Room type (living room, bedroom, office, etc.)
   - Light exposure (north/south facing estimate)
   - Privacy needs assessment

4. TREATMENT RECOMMENDATIONS:
   - Best treatment type (drapes, blinds, shades, shutters)
   - Lining recommendation (blackout, privacy, sheer)
   - Hardware style suggestion

5. OBSTACLES/CONSIDERATIONS:
   - Furniture blocking access
   - HVAC vents near window
   - Electrical outlets
   - Crown molding

Provide measurements in inches. If you see a standard door (80" tall) or outlet (12" from floor), use as reference.
Return as JSON format."""

    try:
        ai_response, model = await generate_vision_response(
            prompt=prompt,
            image_b64=image_data,
            preferred_model="moondream",
            timeout=60.0,
        )
        if ai_response:
            measurements = parse_ai_measurements(ai_response)
            return {
                "status": "success",
                "analysis": ai_response,
                "measurements": measurements,
                "confidence": "medium",
                "model": model or "moondream",
                "note": "AI estimates - verify with tape measure"
            }
        return await fallback_analysis(data)
    except Exception as e:
        return await fallback_analysis(data, str(e))


async def fallback_analysis(data: dict, error: str = None):
    """Fallback when vision model unavailable"""
    return {
        "status": "partial",
        "analysis": "Vision model not available. Manual measurements required.",
        "measurements": {
            "estimated_width": None,
            "estimated_height": None,
            "window_type": "unknown",
            "mount_recommendation": "outside_mount",
            "treatment_suggestion": "drapes"
        },
        "confidence": "low",
        "error": error,
        "note": "Please enter measurements manually or ensure Ollama moondream/llava models are installed"
    }


def parse_ai_measurements(response: str) -> Dict:
    """Extract structured measurements from AI response"""
    measurements = {
        "estimated_width": None,
        "estimated_height": None,
        "window_type": "standard",
        "mount_recommendation": "outside_mount",
        "treatment_suggestion": "drapes",
        "lining_recommendation": "privacy",
        "room_type": "unknown",
        "obstacles": []
    }
    
    # Try to extract numbers for width/height
    width_match = re.search(r'width[:\s]*(\d+(?:\.\d+)?)["\s]*(?:inches|in|")?', response.lower())
    height_match = re.search(r'height[:\s]*(\d+(?:\.\d+)?)["\s]*(?:inches|in|")?', response.lower())
    
    if width_match:
        measurements["estimated_width"] = float(width_match.group(1))
    if height_match:
        measurements["estimated_height"] = float(height_match.group(1))
    
    # Detect window type
    for wtype in ["bay", "casement", "double-hung", "single", "picture", "sliding"]:
        if wtype in response.lower():
            measurements["window_type"] = wtype
            break
    
    # Detect treatment suggestions
    for treatment in ["roman shades", "blinds", "shutters", "drapes", "curtains", "sheer"]:
        if treatment in response.lower():
            measurements["treatment_suggestion"] = treatment
            break
    
    # Detect room type
    for room in ["living room", "bedroom", "office", "kitchen", "dining", "bathroom"]:
        if room in response.lower():
            measurements["room_type"] = room
            break
    
    # Detect mount type
    if "inside mount" in response.lower():
        measurements["mount_recommendation"] = "inside_mount"
    elif "ceiling" in response.lower():
        measurements["mount_recommendation"] = "ceiling_mount"
    
    return measurements
