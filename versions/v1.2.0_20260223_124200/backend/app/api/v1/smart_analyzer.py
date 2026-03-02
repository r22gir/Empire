"""
Smart Window Analyzer - Multiple AI Methods for Best Estimates
==============================================================
Method 1: Ollama LLaVA (if available) - Vision AI
Method 2: Image Analysis (aspect ratio, color detection)
Method 3: Reference Object Calculation
Method 4: Standard Window Database Lookup
Method 5: Machine Learning Heuristics
"""

from fastapi import APIRouter
import httpx
import base64
import io
import re
from typing import Optional, Dict, Any

router = APIRouter(prefix="/smart-analyze", tags=["AI Analysis"])

# Standard window sizes database (inches)
STANDARD_WINDOWS = {
    "single_hung": {"widths": [24, 28, 32, 36], "heights": [36, 48, 52, 60]},
    "double_hung": {"widths": [24, 28, 32, 36, 40], "heights": [36, 48, 52, 60, 72]},
    "casement": {"widths": [18, 24, 30, 36], "heights": [36, 48, 60, 72]},
    "picture": {"widths": [36, 48, 60, 72, 84], "heights": [36, 48, 60, 72]},
    "sliding": {"widths": [36, 48, 60, 72], "heights": [36, 48, 60]},
    "bay": {"widths": [72, 84, 96, 108, 120], "heights": [48, 54, 60, 72]},
}

# Reference object sizes (inches)
REFERENCE_SIZES = {
    "credit_card": {"width": 3.37, "height": 2.13},
    "dollar_bill": {"width": 6.14, "height": 2.61},
    "iphone": {"width": 2.82, "height": 5.78},
    "letter_paper": {"width": 8.5, "height": 11},
    "door": {"width": 36, "height": 80},
    "outlet": {"width": 2.75, "height": 4.5},
    "light_switch": {"width": 2.75, "height": 4.5},
}

# Room-based typical window sizes
ROOM_DEFAULTS = {
    "living_room": {"width": 60, "height": 72, "treatment": "drapes"},
    "bedroom": {"width": 48, "height": 60, "treatment": "drapes"},
    "kitchen": {"width": 36, "height": 48, "treatment": "roman_shades"},
    "bathroom": {"width": 24, "height": 36, "treatment": "blinds"},
    "dining_room": {"width": 60, "height": 72, "treatment": "drapes"},
    "office": {"width": 48, "height": 60, "treatment": "blinds"},
}


async def method_1_llava(image_b64: str, reference: Optional[str] = None) -> Dict[str, Any]:
    """Method 1: Ollama LLaVA Vision Model"""
    try:
        ref_prompt = ""
        if reference and reference in REFERENCE_SIZES:
            ref = REFERENCE_SIZES[reference]
            ref_prompt = f"\n\nIMPORTANT: A {reference.replace('_', ' ')} ({ref['width']}\" x {ref['height']}\") is visible. Use it for scale."
        
        prompt = f"""Analyze this window photo for a drapery workroom.{ref_prompt}

Estimate these measurements in INCHES:
- WIDTH: (number only)
- HEIGHT: (number only)
- WINDOW_TYPE: (bay/picture/double-hung/casement/sliding/standard)
- ROOM: (living room/bedroom/kitchen/bathroom/office/dining room)

Use visual cues: door frames are 80" tall, outlets are 12" from floor, ceiling height is typically 96".

Reply in this exact format:
WIDTH: [number]
HEIGHT: [number]
WINDOW_TYPE: [type]
ROOM: [room]"""

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llava", "prompt": prompt, "images": [image_b64], "stream": False}
            )
            
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                return parse_llava_response(text)
    except Exception as e:
        print(f"LLaVA error: {e}")
    
    return {"success": False, "method": "llava"}


def parse_llava_response(text: str) -> Dict[str, Any]:
    """Parse LLaVA response into structured data"""
    result = {"success": False, "method": "llava", "raw": text}
    
    # Extract width
    w_match = re.search(r'WIDTH[:\s]*(\d+)', text, re.IGNORECASE)
    if w_match:
        result["width"] = int(w_match.group(1))
    
    # Extract height
    h_match = re.search(r'HEIGHT[:\s]*(\d+)', text, re.IGNORECASE)
    if h_match:
        result["height"] = int(h_match.group(1))
    
    # Extract window type
    for wtype in ["bay", "picture", "double-hung", "casement", "sliding"]:
        if wtype in text.lower():
            result["window_type"] = wtype
            break
    
    # Extract room
    for room in ["living room", "bedroom", "kitchen", "bathroom", "office", "dining"]:
        if room in text.lower():
            result["room_type"] = room
            break
    
    result["success"] = "width" in result or "height" in result
    return result


async def method_2_image_analysis(image_b64: str) -> Dict[str, Any]:
    """Method 2: Basic image analysis - aspect ratio and size estimation"""
    try:
        # Decode image to get dimensions
        from PIL import Image
        
        img_data = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(img_data))
        img_width, img_height = img.size
        aspect_ratio = img_width / img_height
        
        # Analyze image for window detection hints
        # Bright center = likely window
        # Aspect ratio hints at window type
        
        estimated_width = 48  # default
        estimated_height = 60  # default
        window_type = "standard"
        
        # Wide aspect ratio suggests picture window or bay
        if aspect_ratio > 1.5:
            window_type = "picture"
            estimated_width = 72
            estimated_height = 48
        elif aspect_ratio > 1.2:
            window_type = "sliding"
            estimated_width = 60
            estimated_height = 48
        # Tall aspect ratio suggests standard or double-hung
        elif aspect_ratio < 0.7:
            window_type = "double-hung"
            estimated_width = 32
            estimated_height = 60
        
        return {
            "success": True,
            "method": "image_analysis",
            "width": estimated_width,
            "height": estimated_height,
            "window_type": window_type,
            "confidence": "low",
            "img_dimensions": f"{img_width}x{img_height}",
            "aspect_ratio": round(aspect_ratio, 2)
        }
    except ImportError:
        return {"success": False, "method": "image_analysis", "error": "PIL not installed"}
    except Exception as e:
        return {"success": False, "method": "image_analysis", "error": str(e)}


def method_3_reference_calculation(reference: str, estimated_ratio: float = 15) -> Dict[str, Any]:
    """Method 3: Calculate from reference object"""
    if not reference or reference not in REFERENCE_SIZES:
        return {"success": False, "method": "reference"}
    
    ref = REFERENCE_SIZES[reference]
    
    # Assume reference object appears at roughly 1/15th of window width
    # This is a rough heuristic
    estimated_width = int(ref["width"] * estimated_ratio)
    estimated_height = int(ref["height"] * estimated_ratio * 1.5)  # windows typically taller
    
    # Clamp to reasonable window sizes
    estimated_width = max(24, min(120, estimated_width))
    estimated_height = max(36, min(96, estimated_height))
    
    return {
        "success": True,
        "method": "reference_calculation",
        "width": estimated_width,
        "height": estimated_height,
        "reference_used": reference,
        "confidence": "medium"
    }


def method_4_standard_lookup(window_type: str = "double_hung") -> Dict[str, Any]:
    """Method 4: Standard window size database lookup"""
    if window_type not in STANDARD_WINDOWS:
        window_type = "double_hung"
    
    sizes = STANDARD_WINDOWS[window_type]
    
    # Return median sizes
    width = sizes["widths"][len(sizes["widths"]) // 2]
    height = sizes["heights"][len(sizes["heights"]) // 2]
    
    return {
        "success": True,
        "method": "standard_lookup",
        "width": width,
        "height": height,
        "window_type": window_type,
        "confidence": "low",
        "note": f"Standard {window_type} size"
    }


def method_5_room_heuristics(room_type: str = None, message: str = "") -> Dict[str, Any]:
    """Method 5: Guess based on room type and message content"""
    
    # Try to detect room from message
    if not room_type:
        message_lower = message.lower()
        for room in ROOM_DEFAULTS.keys():
            if room.replace("_", " ") in message_lower:
                room_type = room
                break
    
    if not room_type:
        room_type = "living_room"  # default
    
    defaults = ROOM_DEFAULTS.get(room_type, ROOM_DEFAULTS["living_room"])
    
    return {
        "success": True,
        "method": "room_heuristics",
        "width": defaults["width"],
        "height": defaults["height"],
        "room_type": room_type,
        "treatment": defaults["treatment"],
        "confidence": "low"
    }


def combine_estimates(results: list) -> Dict[str, Any]:
    """Combine multiple estimates using weighted average"""
    
    weights = {
        "llava": 5,           # Highest weight for vision AI
        "reference_calculation": 4,
        "image_analysis": 3,
        "room_heuristics": 2,
        "standard_lookup": 1
    }
    
    total_weight = 0
    weighted_width = 0
    weighted_height = 0
    window_types = []
    room_types = []
    treatments = []
    methods_used = []
    
    for r in results:
        if not r.get("success"):
            continue
        
        method = r.get("method", "unknown")
        weight = weights.get(method, 1)
        methods_used.append(method)
        
        if "width" in r:
            weighted_width += r["width"] * weight
            total_weight += weight
        if "height" in r:
            weighted_height += r["height"] * weight
        if "window_type" in r:
            window_types.append(r["window_type"])
        if "room_type" in r:
            room_types.append(r["room_type"])
        if "treatment" in r:
            treatments.append(r["treatment"])
    
    if total_weight == 0:
        return {
            "status": "error",
            "analysis": "Could not estimate measurements",
            "measurements": {},
            "confidence": "none"
        }
    
    # Calculate weighted averages
    final_width = round(weighted_width / total_weight)
    final_height = round(weighted_height / total_weight)
    
    # Round to nearest standard size
    final_width = round(final_width / 2) * 2  # Round to even number
    final_height = round(final_height / 2) * 2
    
    # Most common window/room type
    final_window_type = max(set(window_types), key=window_types.count) if window_types else "standard"
    final_room_type = max(set(room_types), key=room_types.count) if room_types else "unknown"
    final_treatment = max(set(treatments), key=treatments.count) if treatments else "drapes"
    
    # Determine confidence
    confidence = "high" if "llava" in methods_used else "medium" if len(methods_used) >= 3 else "low"
    
    return {
        "status": "success",
        "analysis": f"Estimated using {len(methods_used)} methods: {', '.join(methods_used)}",
        "measurements": {
            "estimated_width": final_width,
            "estimated_height": final_height,
            "window_type": final_window_type,
            "room_type": final_room_type,
            "treatment_suggestion": final_treatment,
            "mount_recommendation": "outside_mount"
        },
        "confidence": confidence,
        "methods_used": methods_used,
        "note": "AI-assisted estimates - verify with tape measure"
    }


@router.post("")
async def smart_analyze(data: dict):
    """
    Multi-method AI analysis for window measurements.
    Combines multiple techniques for best accuracy.
    """
    image_data = data.get("image", "")
    reference = data.get("reference_object")
    message = data.get("message", "")
    
    # Clean up base64
    if "base64," in image_data:
        image_data = image_data.split("base64,")[1]
    
    results = []
    
    # Run all methods
    print("🔍 Running multi-method analysis...")
    
    # Method 1: LLaVA Vision (if available)
    print("  → Method 1: LLaVA Vision...")
    llava_result = await method_1_llava(image_data, reference)
    results.append(llava_result)
    print(f"     Result: {llava_result.get('success', False)}")
    
    # Method 2: Image Analysis
    print("  → Method 2: Image Analysis...")
    img_result = await method_2_image_analysis(image_data)
    results.append(img_result)
    print(f"     Result: {img_result.get('success', False)}")
    
    # Method 3: Reference Calculation
    if reference:
        print(f"  → Method 3: Reference Calculation ({reference})...")
        ref_result = method_3_reference_calculation(reference)
        results.append(ref_result)
        print(f"     Result: {ref_result.get('success', False)}")
    
    # Method 4: Standard Lookup
    print("  → Method 4: Standard Window Lookup...")
    # Use window type from previous methods if found
    detected_type = next((r.get("window_type") for r in results if r.get("window_type")), "double_hung")
    std_result = method_4_standard_lookup(detected_type)
    results.append(std_result)
    
    # Method 5: Room Heuristics
    print("  → Method 5: Room Heuristics...")
    detected_room = next((r.get("room_type") for r in results if r.get("room_type")), None)
    room_result = method_5_room_heuristics(detected_room, message)
    results.append(room_result)
    
    # Combine all results
    print("  → Combining estimates...")
    final = combine_estimates(results)
    
    print(f"✅ Analysis complete: {final.get('confidence', 'unknown')} confidence")
    return final


@router.get("/methods")
async def list_methods():
    """List available analysis methods"""
    return {
        "methods": [
            {"name": "LLaVA Vision", "weight": 5, "description": "AI vision model analyzes image directly"},
            {"name": "Reference Calculation", "weight": 4, "description": "Uses known object size for scale"},
            {"name": "Image Analysis", "weight": 3, "description": "Aspect ratio and dimension analysis"},
            {"name": "Room Heuristics", "weight": 2, "description": "Typical sizes based on room type"},
            {"name": "Standard Lookup", "weight": 1, "description": "Common window size database"},
        ],
        "reference_objects": list(REFERENCE_SIZES.keys()),
        "standard_windows": list(STANDARD_WINDOWS.keys()),
        "room_defaults": list(ROOM_DEFAULTS.keys())
    }
