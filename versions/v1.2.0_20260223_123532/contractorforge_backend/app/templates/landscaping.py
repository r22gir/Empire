"""
LandscapeForge - Landscaping Industry Template
For landscaping contractors
"""
from typing import Dict, List, Any
from app.templates.base import IndustryTemplate, PricingMethod


class LandscapeForgeTemplate(IndustryTemplate):
    """Landscaping template"""
    
    @property
    def industry_name(self) -> str:
        return "LandscapeForge - Landscaping"
    
    @property
    def industry_code(self) -> str:
        return "landscaping"
    
    @property
    def primary_color(self) -> str:
        return "#2D8659"  # Nature green
    
    @property
    def terminology(self) -> Dict[str, str]:
        return {
            "project": "Project",
            "customer": "Client",
            "job": "Project",
            "quote": "Proposal",
            "invoice": "Invoice",
        }
    
    @property
    def workflow_stages(self) -> List[Dict[str, Any]]:
        return [
            {"code": "inquiry", "name": "Consultation", "order": 1},
            {"code": "quoted", "name": "Proposal Sent", "order": 2},
            {"code": "approved", "name": "Approved", "order": 3},
            {"code": "design", "name": "Design Phase", "order": 4},
            {"code": "in_progress", "name": "Installation", "order": 5},
            {"code": "completed", "name": "Completed", "order": 6},
        ]
    
    @property
    def measurement_types(self) -> List[str]:
        return [
            "total_sqft",
            "lawn_area",
            "bed_area",
            "patio_sqft",
            "walkway_linear_ft",
            "plant_count",
            "tree_count",
        ]
    
    @property
    def catalog_categories(self) -> List[str]:
        return [
            "tree",
            "shrub",
            "perennial",
            "annual",
            "groundcover",
            "mulch",
            "stone",
            "paver",
            "soil",
            "fertilizer",
        ]
    
    @property
    def pricing_config(self) -> Dict[str, Any]:
        return {
            # Per-sqft pricing for installations
            "installation_sqft": {
                "patio": 15.0,
                "walkway": 12.0,
                "lawn": 0.80,  # Sod
                "mulch_bed": 2.50,
                "gravel": 8.0,
            },
            # Per-plant pricing ranges
            "plants": {
                "annual_min": 5.0,
                "annual_max": 15.0,
                "perennial_min": 15.0,
                "perennial_max": 50.0,
                "shrub_min": 30.0,
                "shrub_max": 150.0,
                "tree_min": 100.0,
                "tree_max": 800.0,
            },
            # Labor rates
            "labor_per_hour": 65.0,
            "crew_size_typical": 2,
            # Materials markup
            "materials_markup": 0.40,  # 40%
            # Design fee
            "design_fee": 500.0,
            # Payment terms
            "deposit_percentage": 50.0,
            "progress_payment": True,
        }
    
    @property
    def ai_intake_prompts(self) -> Dict[str, str]:
        return {
            "greeting": "Hello! I'm excited to help with your landscaping project. What type of work are you looking for? (New Installation, Renovation, Maintenance, Design, etc.)",
            "project_type": "What specific areas are you looking to landscape? (Front yard, backyard, patio, garden beds, etc.)",
            "size": "Do you know the approximate size of the area? You can provide square footage or dimensions, or I can help estimate from photos.",
            "plants": "Are you interested in specific plants or trees? Tell me about your preferences (colors, maintenance level, sun/shade conditions).",
            "hardscape": "Do you need any hardscaping? (Patio, walkway, retaining wall, etc.)",
            "timeline": "What's your ideal timeline for completion? Any seasonal preferences?",
            "budget": "Do you have a budget range in mind for this project?",
            "summary": "Perfect! Let me create a proposal based on your vision.",
        }
    
    @property
    def features_enabled(self) -> Dict[str, bool]:
        return {
            "production_queue": False,
            "sample_management": False,
            "permit_tracking": False,
            "crew_dispatch": True,
            "design_mockups": True,
            "seasonal_scheduling": True,
        }
    
    def calculate_estimate(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate estimate for landscaping project
        """
        line_items = []
        subtotal = 0.0
        
        measurements = project_data.get("measurements", {})
        options = project_data.get("options", {})
        
        # Design fee (if applicable)
        if options.get("design_required", True):
            design_fee = self.pricing_config["design_fee"]
            line_items.append({
                "description": "Landscape Design & Planning",
                "quantity": 1,
                "unit": "project",
                "rate": design_fee,
                "amount": design_fee,
            })
            subtotal += design_fee
        
        # Calculate area-based costs
        areas = measurements.get("areas", [])
        for area in areas:
            area_type = area.get("type", "lawn")
            sqft = area.get("sqft", 0)
            
            if area_type in self.pricing_config["installation_sqft"]:
                price_per_sqft = self.pricing_config["installation_sqft"][area_type]
                amount = sqft * price_per_sqft
                
                line_items.append({
                    "description": f"{area_type.title()} Installation ({sqft} sqft)",
                    "quantity": sqft,
                    "unit": "sqft",
                    "rate": price_per_sqft,
                    "amount": amount,
                })
                subtotal += amount
        
        # Plants and trees
        plants = measurements.get("plants", [])
        for plant in plants:
            plant_type = plant.get("type", "perennial")
            name = plant.get("name", plant_type.title())
            quantity = plant.get("quantity", 1)
            cost_per_plant = plant.get("cost", 25.0)
            
            # Apply markup
            sell_price = cost_per_plant * (1 + self.pricing_config["materials_markup"])
            amount = sell_price * quantity
            
            line_items.append({
                "description": f"{name} ({plant_type})",
                "quantity": quantity,
                "unit": "each",
                "rate": sell_price,
                "amount": amount,
            })
            subtotal += amount
        
        # Materials (mulch, stone, etc.)
        materials = measurements.get("materials", [])
        for material in materials:
            material_type = material.get("type", "Material")
            quantity = material.get("quantity", 1)
            unit = material.get("unit", "yard")
            cost = material.get("cost", 50.0)
            
            # Apply markup
            sell_price = cost * (1 + self.pricing_config["materials_markup"])
            amount = sell_price * quantity
            
            line_items.append({
                "description": material_type.title(),
                "quantity": quantity,
                "unit": unit,
                "rate": sell_price,
                "amount": amount,
            })
            subtotal += amount
        
        # Labor (if hourly estimate)
        estimated_hours = options.get("estimated_hours", 0)
        if estimated_hours > 0:
            crew_size = options.get("crew_size", self.pricing_config["crew_size_typical"])
            labor_rate = self.pricing_config["labor_per_hour"]
            labor_cost = estimated_hours * crew_size * labor_rate
            
            line_items.append({
                "description": f"Labor ({crew_size}-person crew, {estimated_hours} hours)",
                "quantity": estimated_hours * crew_size,
                "unit": "hour",
                "rate": labor_rate,
                "amount": labor_cost,
            })
            subtotal += labor_cost
        
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
    
    def validate_measurements(self, measurements: Dict[str, Any]) -> bool:
        """Validate landscaping measurements"""
        # At minimum, need some area or plant information
        
        has_areas = "areas" in measurements and len(measurements["areas"]) > 0
        has_plants = "plants" in measurements and len(measurements["plants"]) > 0
        has_materials = "materials" in measurements and len(measurements["materials"]) > 0
        
        if not (has_areas or has_plants or has_materials):
            return False
        
        # Validate areas
        if has_areas:
            for area in measurements["areas"]:
                if "type" not in area or "sqft" not in area:
                    return False
                if area["sqft"] <= 0:
                    return False
        
        # Validate plants
        if has_plants:
            for plant in measurements["plants"]:
                if "type" not in plant or "quantity" not in plant:
                    return False
                if plant["quantity"] <= 0:
                    return False
        
        return True


# Singleton instance
landscapeforge = LandscapeForgeTemplate()
