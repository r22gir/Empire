"""
ElectricForge - Electrician Industry Template
For electrical contractors and electricians
"""
from typing import Dict, List, Any
from app.templates.base import IndustryTemplate, PricingMethod


class ElectricForgeTemplate(IndustryTemplate):
    """Electrician template"""
    
    @property
    def industry_name(self) -> str:
        return "ElectricForge - Electricians"
    
    @property
    def industry_code(self) -> str:
        return "electrician"
    
    @property
    def primary_color(self) -> str:
        return "#FDB91B"  # Electric yellow/gold
    
    @property
    def terminology(self) -> Dict[str, str]:
        return {
            "project": "Job",
            "customer": "Client",
            "job": "Service Call",
            "quote": "Estimate",
            "invoice": "Invoice",
        }
    
    @property
    def workflow_stages(self) -> List[Dict[str, Any]]:
        return [
            {"code": "inquiry", "name": "Service Request", "order": 1},
            {"code": "quoted", "name": "Estimate Sent", "order": 2},
            {"code": "approved", "name": "Scheduled", "order": 3},
            {"code": "in_progress", "name": "In Progress", "order": 4},
            {"code": "inspection", "name": "Inspection Pending", "order": 5},
            {"code": "completed", "name": "Completed", "order": 6},
        ]
    
    @property
    def measurement_types(self) -> List[str]:
        return [
            "panel_amps",
            "circuit_count",
            "fixture_count",
            "outlet_count",
            "wire_length",
            "conduit_length",
        ]
    
    @property
    def catalog_categories(self) -> List[str]:
        return [
            "electrical_panel",
            "circuit_breaker",
            "fixture",
            "outlet",
            "switch",
            "wire",
            "conduit",
            "junction_box",
            "romex",
        ]
    
    @property
    def pricing_config(self) -> Dict[str, Any]:
        return {
            # Hourly rates
            "hourly_rate": {
                "apprentice": 55.0,
                "journeyman": 85.0,
                "master": 125.0,
            },
            # Per-fixture pricing
            "fixtures": {
                "outlet_install": 100.0,
                "switch_install": 125.0,
                "ceiling_light": 150.0,
                "chandelier": 350.0,
                "ceiling_fan": 200.0,
                "recessed_light": 175.0,
                "panel_upgrade_100amp": 1200.0,
                "panel_upgrade_200amp": 2800.0,
            },
            # Emergency multiplier
            "emergency_multiplier": 1.5,
            # Materials markup
            "materials_markup": 0.30,  # 30%
            # Trip charge
            "trip_charge": 75.0,
            # Minimum charge
            "minimum_charge": 150.0,
            # Payment terms
            "deposit_percentage": 0.0,  # Often pay on completion
            "due_on_completion": True,
        }
    
    @property
    def ai_intake_prompts(self) -> Dict[str, str]:
        return {
            "greeting": "Hi! I'm here to help with your electrical needs. What type of electrical work do you need? (Installation, Repair, Upgrade, Emergency Service, etc.)",
            "urgency": "Is this an emergency situation? (power outage, sparking outlet, etc.)",
            "scope": "Can you describe the work needed? For example: number of outlets, fixtures, or panels?",
            "location": "Where is the work located? (Residential, Commercial, Indoor, Outdoor)",
            "timeline": "When would you like this work completed?",
            "permits": "Have you checked if permits are required for this work?",
            "summary": "Got it! Let me prepare an estimate for you based on this information.",
        }
    
    @property
    def features_enabled(self) -> Dict[str, bool]:
        return {
            "production_queue": False,
            "sample_management": False,
            "permit_tracking": True,
            "crew_dispatch": True,
            "design_mockups": False,
            "seasonal_scheduling": False,
        }
    
    def calculate_estimate(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate estimate for electrical work
        """
        line_items = []
        subtotal = 0.0
        
        measurements = project_data.get("measurements", {})
        options = project_data.get("options", {})
        
        is_emergency = options.get("is_emergency", False)
        labor_type = options.get("labor_type", "journeyman")
        
        # Trip charge
        trip_charge = self.pricing_config["trip_charge"]
        line_items.append({
            "description": "Service Call / Trip Charge",
            "quantity": 1,
            "unit": "trip",
            "rate": trip_charge,
            "amount": trip_charge,
        })
        subtotal += trip_charge
        
        # Calculate labor costs
        fixtures = measurements.get("fixtures", [])
        
        if fixtures:
            # Per-fixture pricing
            for fixture in fixtures:
                fixture_type = fixture.get("type", "outlet_install")
                quantity = fixture.get("quantity", 1)
                
                if fixture_type in self.pricing_config["fixtures"]:
                    price = self.pricing_config["fixtures"][fixture_type]
                    
                    if is_emergency:
                        price *= self.pricing_config["emergency_multiplier"]
                        desc = f"{fixture_type.replace('_', ' ').title()} (EMERGENCY)"
                    else:
                        desc = fixture_type.replace("_", " ").title()
                    
                    amount = price * quantity
                    line_items.append({
                        "description": desc,
                        "quantity": quantity,
                        "unit": "each",
                        "rate": price,
                        "amount": amount,
                    })
                    subtotal += amount
        
        else:
            # Hourly pricing
            estimated_hours = options.get("estimated_hours", 2)
            hourly_rate = self.pricing_config["hourly_rate"][labor_type]
            
            if is_emergency:
                hourly_rate *= self.pricing_config["emergency_multiplier"]
                desc = f"Labor - {labor_type.title()} (EMERGENCY)"
            else:
                desc = f"Labor - {labor_type.title()}"
            
            labor_cost = estimated_hours * hourly_rate
            line_items.append({
                "description": desc,
                "quantity": estimated_hours,
                "unit": "hour",
                "rate": hourly_rate,
                "amount": labor_cost,
            })
            subtotal += labor_cost
        
        # Materials
        materials_cost = options.get("materials_cost", 0.0)
        if materials_cost > 0:
            materials_total = materials_cost * (1 + self.pricing_config["materials_markup"])
            line_items.append({
                "description": "Materials & Supplies",
                "quantity": 1,
                "unit": "lot",
                "rate": materials_total,
                "amount": materials_total,
            })
            subtotal += materials_total
        
        # Permit fees (if required)
        if options.get("permit_required", False):
            permit_fee = options.get("permit_fee", 150.0)
            line_items.append({
                "description": "Permit Fees",
                "quantity": 1,
                "unit": "permit",
                "rate": permit_fee,
                "amount": permit_fee,
            })
            subtotal += permit_fee
        
        # Apply minimum charge
        if subtotal < self.pricing_config["minimum_charge"]:
            adjustment = self.pricing_config["minimum_charge"] - subtotal
            line_items.append({
                "description": "Minimum Service Charge",
                "quantity": 1,
                "unit": "adjustment",
                "rate": adjustment,
                "amount": adjustment,
            })
            subtotal = self.pricing_config["minimum_charge"]
        
        # Calculate totals
        tax_rate = project_data.get("tax_rate", 0.08)
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        # Payment terms (usually due on completion for electricians)
        deposit_pct = self.pricing_config["deposit_percentage"]
        deposit_amount = total * (deposit_pct / 100) if deposit_pct > 0 else 0
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
        """Validate electrical measurements"""
        # For electricians, measurements are optional
        # Can quote based on description and photos
        
        if "fixtures" in measurements:
            fixtures = measurements["fixtures"]
            if not isinstance(fixtures, list):
                return False
            
            for fixture in fixtures:
                if "type" not in fixture:
                    return False
                if "quantity" not in fixture or fixture["quantity"] <= 0:
                    return False
        
        return True


# Singleton instance
electricforge = ElectricForgeTemplate()
