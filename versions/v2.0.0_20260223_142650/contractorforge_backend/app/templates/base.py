"""
Base industry template interface
"""
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from enum import Enum


class PricingMethod(str, Enum):
    """Pricing calculation methods"""
    PER_HOUR = "per_hour"
    PER_ITEM = "per_item"
    PER_SQFT = "per_sqft"
    PER_WIDTH = "per_width"
    PER_LINEAR_FT = "per_linear_ft"
    FIXED = "fixed"


class IndustryTemplate(ABC):
    """
    Base class for industry templates
    Each industry implements this to customize behavior
    """
    
    @property
    @abstractmethod
    def industry_name(self) -> str:
        """Display name of the industry"""
        pass
    
    @property
    @abstractmethod
    def industry_code(self) -> str:
        """Code identifier (workroom, electrician, landscaping)"""
        pass
    
    @property
    @abstractmethod
    def primary_color(self) -> str:
        """Primary brand color (hex)"""
        pass
    
    @property
    @abstractmethod
    def terminology(self) -> Dict[str, str]:
        """Industry-specific terminology mapping"""
        pass
    
    @property
    @abstractmethod
    def workflow_stages(self) -> List[Dict[str, Any]]:
        """Project workflow stages"""
        pass
    
    @property
    @abstractmethod
    def measurement_types(self) -> List[str]:
        """Types of measurements for this industry"""
        pass
    
    @property
    @abstractmethod
    def catalog_categories(self) -> List[str]:
        """Product catalog categories"""
        pass
    
    @property
    @abstractmethod
    def pricing_config(self) -> Dict[str, Any]:
        """Default pricing configuration"""
        pass
    
    @property
    @abstractmethod
    def ai_intake_prompts(self) -> Dict[str, str]:
        """AI prompts for conversation intake"""
        pass
    
    @abstractmethod
    def calculate_estimate(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate estimate based on project data
        Returns dict with line_items, subtotal, etc.
        """
        pass
    
    @abstractmethod
    def validate_measurements(self, measurements: Dict[str, Any]) -> bool:
        """Validate measurement data for this industry"""
        pass
    
    @property
    def features_enabled(self) -> Dict[str, bool]:
        """Feature flags specific to this industry"""
        return {
            "production_queue": False,
            "sample_management": False,
            "permit_tracking": False,
            "crew_dispatch": False,
            "design_mockups": False,
            "seasonal_scheduling": False,
        }
