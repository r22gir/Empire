"""
LuxeForge - Custom Workroom Industry Template
For drapery, window treatments, soft furnishings
"""
from typing import Dict, List, Any
from app.templates.base import IndustryTemplate, PricingMethod


class LuxeForgeTemplate(IndustryTemplate):
    """Custom Workroom template - primary industry"""
    
    @property
    def industry_name(self) -> str:
        return "LuxeForge - Custom Workrooms"
    
    @property
    def industry_code(self) -> str:
        return "workroom"
    
    @property
    def primary_color(self) -> str:
        return "#8B4789"  # Royal purple for luxury
    
    @property
    def terminology(self) -> Dict[str, str]:
        return {
            "project": "Project",
            "customer": "Designer",
            "job": "Project",
            "quote": "Proposal",
            "invoice": "Invoice",
        }
    
    @property
    def workflow_stages(self) -> List[Dict[str, Any]]:
        return [
            {"code": "inquiry", "name": "Inquiry", "order": 1},
            {"code": "quoted", "name": "Proposal Sent", "order": 2},
            {"code": "approved", "name": "Approved", "order": 3},
            {"code": "in_production", "name": "In Production", "order": 4},
            {"code": "ready_to_install", "name": "Ready to Install", "order": 5},
            {"code": "installed", "name": "Installed", "order": 6},
            {"code": "completed", "name": "Completed", "order": 7},
        ]
    
    @property
    def measurement_types(self) -> List[str]:
        return [
            "window_width",
            "window_height",
            "window_depth",
            "rod_length",
            "panel_count",
            "fabric_yards",
        ]
    
    @property
    def catalog_categories(self) -> List[str]:
        return [
            "fabric",
            "hardware",
            "trim",
            "lining",
            "interlining",
            "cord",
            "rings",
            "brackets",
        ]
    
    @property
    def pricing_config(self) -> Dict[str, Any]:
        return {
            # Drapery pricing
            "drapery_per_width": {
                "min": 95.0,
                "max": 150.0,
                "default": 120.0,
            },
            # Roman shade pricing
            "roman_shade_per_sqft": {
                "min": 15.0,
                "max": 20.0,
                "default": 17.5,
            },
            # Installation pricing
            "installation": {
                "small_window": 45.0,  # < 60" wide
                "medium_window": 95.0,  # 60-96" wide
                "large_window": 195.0,  # > 96" wide
            },
            # Material markups
            "fabric_markup": 0.40,  # 40% markup
            "hardware_markup": 0.50,  # 50% markup
            # Payment terms
            "deposit_percentage": 50.0,
            "balance_on_completion": True,
        }
    
    @property
    def ai_intake_prompts(self) -> Dict[str, str]:
        return {
            "greeting": "Hello! I'm here to help you with your window treatment project. Let's start by understanding what you need. What type of window treatments are you interested in? (Drapery, Roman Shades, Valances, etc.)",
            "window_count": "How many windows do you need treatments for?",
            "measurements": "Do you have measurements for the windows? I can help you with that! For each window, I'll need the width and height. You can also upload photos with a reference object (like a credit card) for automatic measurements.",
            "fabric_preference": "Do you have a fabric in mind? If you're bringing your own fabric (COM), let me know and I'll calculate yardage requirements.",
            "hardware": "What about hardware? Are you looking for decorative rods, traverse rods, or other hardware?",
            "timeline": "When would you like the installation completed?",
            "summary": "Great! Let me summarize what we've discussed and prepare a proposal for you.",
        }
    
    @property
    def features_enabled(self) -> Dict[str, bool]:
        return {
            "production_queue": True,
            "sample_management": True,
            "permit_tracking": False,
            "crew_dispatch": False,
            "design_mockups": True,
            "seasonal_scheduling": False,
        }
    
    def calculate_estimate(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate estimate for workroom project
        """
        line_items = []
        subtotal = 0.0
        
        measurements = project_data.get("measurements", {})
        options = project_data.get("options", {})
        
        # Calculate drapery costs
        windows = measurements.get("windows", [])
        for i, window in enumerate(windows, 1):
            width = window.get("width", 0)
            treatment_type = window.get("treatment_type", "drapery")
            
            if treatment_type == "drapery":
                # Calculate widths (assumes 2-2.5x fullness)
                widths = max(2, round(width / 24))  # Standard width is 24"
                price_per_width = self.pricing_config["drapery_per_width"]["default"]
                labor_cost = widths * price_per_width
                
                line_items.append({
                    "description": f"Drapery - Window {i} ({width}\" wide)",
                    "quantity": widths,
                    "unit": "width",
                    "rate": price_per_width,
                    "amount": labor_cost,
                })
                subtotal += labor_cost
                
                # Fabric calculation
                if options.get("fabric_provided", False):
                    # Customer providing fabric (COM)
                    yards_needed = self._calculate_fabric_yards(window, widths)
                    line_items.append({
                        "description": f"Fabric Required - Window {i}",
                        "quantity": yards_needed,
                        "unit": "yard",
                        "rate": 0,
                        "amount": 0,
                        "note": "Customer Providing Fabric (COM)",
                    })
                else:
                    # We're providing fabric
                    yards_needed = self._calculate_fabric_yards(window, widths)
                    fabric_cost_per_yard = options.get("fabric_cost_per_yard", 50.0)
                    fabric_cost = yards_needed * fabric_cost_per_yard
                    fabric_total = fabric_cost * (1 + self.pricing_config["fabric_markup"])
                    
                    line_items.append({
                        "description": f"Fabric - Window {i}",
                        "quantity": yards_needed,
                        "unit": "yard",
                        "rate": fabric_cost_per_yard * (1 + self.pricing_config["fabric_markup"]),
                        "amount": fabric_total,
                    })
                    subtotal += fabric_total
            
            elif treatment_type == "roman_shade":
                height = window.get("height", 0)
                sqft = (width * height) / 144  # Convert to sqft
                price_per_sqft = self.pricing_config["roman_shade_per_sqft"]["default"]
                labor_cost = sqft * price_per_sqft
                
                line_items.append({
                    "description": f"Roman Shade - Window {i} ({width}\"x{height}\")",
                    "quantity": sqft,
                    "unit": "sqft",
                    "rate": price_per_sqft,
                    "amount": labor_cost,
                })
                subtotal += labor_cost
            
            # Installation
            if options.get("installation_required", True):
                if width < 60:
                    install_cost = self.pricing_config["installation"]["small_window"]
                elif width <= 96:
                    install_cost = self.pricing_config["installation"]["medium_window"]
                else:
                    install_cost = self.pricing_config["installation"]["large_window"]
                
                line_items.append({
                    "description": f"Installation - Window {i}",
                    "quantity": 1,
                    "unit": "window",
                    "rate": install_cost,
                    "amount": install_cost,
                })
                subtotal += install_cost
        
        # Hardware
        if options.get("hardware_required", True):
            hardware_cost = options.get("hardware_cost", 100.0)
            hardware_total = hardware_cost * (1 + self.pricing_config["hardware_markup"])
            
            line_items.append({
                "description": "Hardware & Accessories",
                "quantity": len(windows),
                "unit": "set",
                "rate": hardware_total / len(windows) if windows else hardware_total,
                "amount": hardware_total,
            })
            subtotal += hardware_total
        
        # Calculate totals
        tax_rate = project_data.get("tax_rate", 0.08)
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        # Payment terms
        deposit_pct = self.pricing_config["deposit_percentage"]
        deposit_amount = total * (deposit_pct / 100)
        balance_due = total - deposit_amount
        
        return {
            "line_items": line_items,
            "subtotal": round(subtotal, 2),
            "tax_rate": tax_rate,
            "tax_amount": round(tax_amount, 2),
            "total": round(total, 2),
            "deposit_percentage": deposit_pct,
            "deposit_amount": round(deposit_amount, 2),
            "balance_due": round(balance_due, 2),
        }
    
    def _calculate_fabric_yards(self, window: Dict[str, Any], widths: int) -> float:
        """Calculate fabric yardage needed"""
        height = window.get("height", 84)  # Default 84" drop
        
        # Add allowances
        height_with_allowance = height + 16  # Hem + header allowance
        
        # Calculate yards (54" wide fabric standard)
        yards_per_width = height_with_allowance / 36
        total_yards = yards_per_width * widths
        
        # Add pattern repeat allowance if applicable
        pattern_repeat = window.get("pattern_repeat", 0)
        if pattern_repeat > 0:
            repeats_needed = (height_with_allowance / pattern_repeat) + 1
            total_yards = (repeats_needed * pattern_repeat / 36) * widths
        
        return round(total_yards, 2)
    
    def validate_measurements(self, measurements: Dict[str, Any]) -> bool:
        """Validate workroom measurements"""
        if "windows" not in measurements:
            return False
        
        windows = measurements["windows"]
        if not isinstance(windows, list) or len(windows) == 0:
            return False
        
        for window in windows:
            # Must have width
            if "width" not in window or window["width"] <= 0:
                return False
            
            # Height is optional but must be valid if provided
            if "height" in window and window["height"] <= 0:
                return False
        
        return True


# Singleton instance
luxeforge = LuxeForgeTemplate()
