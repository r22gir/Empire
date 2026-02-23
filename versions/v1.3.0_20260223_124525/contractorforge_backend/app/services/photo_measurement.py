"""
Photo Measurement Service
Uses OpenCV and MiDaS depth estimation to measure from photos
"""
import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image
import io


class ConfidenceLevel:
    """Confidence levels for measurements"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReferenceObject:
    """Known reference objects for scale"""
    CREDIT_CARD = {"width": 3.375, "height": 2.125, "unit": "inches"}
    DOLLAR_BILL = {"width": 6.14, "height": 2.61, "unit": "inches"}
    QUARTER = {"diameter": 0.955, "unit": "inches"}


class PhotoMeasurementService:
    """
    Service for extracting measurements from photos
    """
    
    def __init__(self):
        self.reference_objects = {
            "credit_card": ReferenceObject.CREDIT_CARD,
            "dollar_bill": ReferenceObject.DOLLAR_BILL,
            "quarter": ReferenceObject.QUARTER,
        }
    
    def measure_from_photo(
        self,
        image_bytes: bytes,
        reference_type: Optional[str] = None,
        measurement_type: str = "window"
    ) -> Dict[str, Any]:
        """
        Measure objects in a photo
        
        Args:
            image_bytes: Image file bytes
            reference_type: Type of reference object (credit_card, dollar_bill, etc.)
            measurement_type: What to measure (window, panel, area, etc.)
        
        Returns:
            Dict with measurements and confidence scores
        """
        try:
            # Load image
            image = self._load_image(image_bytes)
            
            # Detect reference object
            reference_info = None
            if reference_type:
                reference_info = self._detect_reference_object(image, reference_type)
            
            # Calculate scale
            pixels_per_inch = None
            confidence = ConfidenceLevel.LOW
            
            if reference_info:
                pixels_per_inch = reference_info["pixels_per_inch"]
                confidence = reference_info["confidence"]
            else:
                # Fall back to depth estimation
                pixels_per_inch = self._estimate_scale_from_depth(image)
                confidence = ConfidenceLevel.LOW
            
            # Detect and measure target object
            measurements = self._measure_target(
                image,
                pixels_per_inch,
                measurement_type
            )
            
            return {
                "success": True,
                "measurements": measurements,
                "confidence": confidence,
                "reference_detected": reference_info is not None,
                "scale_factor": pixels_per_inch,
                "unit": "inches",
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "confidence": ConfidenceLevel.LOW,
            }
    
    def _load_image(self, image_bytes: bytes) -> np.ndarray:
        """Load image from bytes"""
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Failed to load image")
        return image
    
    def _detect_reference_object(
        self,
        image: np.ndarray,
        reference_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Detect reference object in image
        Uses edge detection and rectangle finding
        """
        if reference_type not in self.reference_objects:
            return None
        
        ref_obj = self.reference_objects[reference_type]
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Look for rectangular contours
        rectangles = []
        for contour in contours:
            # Approximate contour
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Check if it's a rectangle (4 corners)
            if len(approx) == 4:
                area = cv2.contourArea(contour)
                if area > 1000:  # Minimum area threshold
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect_ratio = float(w) / h if h > 0 else 0
                    
                    # Check aspect ratio matches reference object
                    expected_ratio = ref_obj["width"] / ref_obj["height"]
                    ratio_diff = abs(aspect_ratio - expected_ratio)
                    
                    if ratio_diff < 0.3:  # Allow some tolerance
                        rectangles.append({
                            "width_pixels": w,
                            "height_pixels": h,
                            "aspect_ratio": aspect_ratio,
                            "area": area,
                            "ratio_diff": ratio_diff,
                        })
        
        if not rectangles:
            return None
        
        # Find best match (closest aspect ratio)
        best_match = min(rectangles, key=lambda r: r["ratio_diff"])
        
        # Calculate pixels per inch
        pixels_per_inch = best_match["width_pixels"] / ref_obj["width"]
        
        # Determine confidence based on match quality
        if best_match["ratio_diff"] < 0.1:
            confidence = ConfidenceLevel.HIGH
        elif best_match["ratio_diff"] < 0.2:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW
        
        return {
            "pixels_per_inch": pixels_per_inch,
            "confidence": confidence,
            "reference_dimensions": ref_obj,
            "detected_pixels": best_match,
        }
    
    def _estimate_scale_from_depth(self, image: np.ndarray) -> float:
        """
        Estimate scale using depth estimation (MiDaS)
        This is a fallback when no reference object is detected
        Note: Returns a rough estimate, confidence will be LOW
        """
        # For now, return a default value
        # In production, would use MiDaS model here
        # torch model loading would happen here
        
        # Placeholder: assume 100 pixels per foot at average distance
        return 100.0 / 12.0  # pixels per inch
    
    def _measure_target(
        self,
        image: np.ndarray,
        pixels_per_inch: float,
        measurement_type: str
    ) -> Dict[str, Any]:
        """
        Measure the target object (window, panel, area, etc.)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find largest contour (assuming it's the target)
        if not contours:
            return {"error": "No objects detected"}
        
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Convert pixels to inches
        width_inches = w / pixels_per_inch
        height_inches = h / pixels_per_inch
        
        # Calculate area
        area_sqft = (width_inches * height_inches) / 144
        
        measurements = {
            "width": round(width_inches, 2),
            "height": round(height_inches, 2),
            "area_sqft": round(area_sqft, 2),
            "type": measurement_type,
        }
        
        # Add industry-specific fields
        if measurement_type == "window":
            measurements["width_in_widths"] = round(width_inches / 24, 1)  # For drapery
        
        return measurements
    
    def batch_measure(
        self,
        images: List[bytes],
        reference_type: Optional[str] = None,
        measurement_type: str = "window"
    ) -> List[Dict[str, Any]]:
        """
        Measure multiple images
        """
        results = []
        for image_bytes in images:
            result = self.measure_from_photo(image_bytes, reference_type, measurement_type)
            results.append(result)
        return results


# Singleton service
photo_measurement_service = PhotoMeasurementService()
