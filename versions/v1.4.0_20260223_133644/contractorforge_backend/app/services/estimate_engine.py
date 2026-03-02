"""
Estimate Engine Service
Generates estimates using industry templates
"""
from typing import Dict, Any
from app.templates import get_template


class EstimateEngineService:
    """
    Service for generating estimates based on industry templates
    """
    
    def generate_estimate(
        self,
        industry_code: str,
        project_data: Dict[str, Any],
        pricing_overrides: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate estimate for a project
        
        Args:
            industry_code: Industry template code
            project_data: Project measurements and options
            pricing_overrides: Optional tenant-specific pricing overrides
        
        Returns:
            Dict with line items, totals, payment terms
        """
        template = get_template(industry_code)
        
        # Apply pricing overrides if provided
        if pricing_overrides:
            # Merge overrides with template pricing
            project_data = self._apply_pricing_overrides(
                project_data,
                pricing_overrides,
                template
            )
        
        # Generate estimate using template
        estimate = template.calculate_estimate(project_data)
        
        # Add metadata
        estimate["industry_code"] = industry_code
        estimate["generated_at"] = None  # Will be set when saving to DB
        
        return estimate
    
    def _apply_pricing_overrides(
        self,
        project_data: Dict[str, Any],
        overrides: Dict[str, Any],
        template
    ) -> Dict[str, Any]:
        """
        Apply tenant-specific pricing overrides
        """
        # Create a copy to avoid mutating input
        data = project_data.copy()
        
        # Apply tax rate override
        if "tax_rate" in overrides:
            data["tax_rate"] = overrides["tax_rate"]
        
        # Apply deposit percentage override
        if "deposit_percentage" in overrides:
            data["deposit_percentage"] = overrides["deposit_percentage"]
        
        # Industry-specific overrides
        if "options" not in data:
            data["options"] = {}
        
        # Merge pricing overrides into options
        for key, value in overrides.items():
            if key not in ["tax_rate", "deposit_percentage"]:
                data["options"][key] = value
        
        return data
    
    def validate_estimate_data(
        self,
        industry_code: str,
        project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that project data is sufficient for estimate generation
        """
        template = get_template(industry_code)
        
        # Check measurements
        measurements = project_data.get("measurements", {})
        is_valid = template.validate_measurements(measurements)
        
        if not is_valid:
            return {
                "valid": False,
                "error": "Invalid or insufficient measurement data",
                "required_fields": template.measurement_types,
            }
        
        return {
            "valid": True,
            "message": "Estimate data is valid",
        }
    
    def calculate_payment_schedule(
        self,
        total_amount: float,
        deposit_percentage: float,
        progress_payments: int = 0
    ) -> Dict[str, Any]:
        """
        Calculate payment schedule
        
        Args:
            total_amount: Total estimate amount
            deposit_percentage: Deposit percentage (0-100)
            progress_payments: Number of progress payments
        
        Returns:
            Dict with payment schedule
        """
        deposit_amount = total_amount * (deposit_percentage / 100)
        remaining = total_amount - deposit_amount
        
        schedule = [
            {
                "payment_number": 1,
                "type": "deposit",
                "amount": round(deposit_amount, 2),
                "percentage": deposit_percentage,
                "due": "On approval",
            }
        ]
        
        if progress_payments > 0:
            payment_amount = remaining / (progress_payments + 1)
            for i in range(progress_payments):
                schedule.append({
                    "payment_number": i + 2,
                    "type": "progress",
                    "amount": round(payment_amount, 2),
                    "percentage": round((payment_amount / total_amount) * 100, 2),
                    "due": f"Progress payment {i + 1}",
                })
            
            # Final payment
            final_amount = remaining - (payment_amount * progress_payments)
            schedule.append({
                "payment_number": progress_payments + 2,
                "type": "final",
                "amount": round(final_amount, 2),
                "percentage": round((final_amount / total_amount) * 100, 2),
                "due": "On completion",
            })
        else:
            # Just deposit and final
            schedule.append({
                "payment_number": 2,
                "type": "final",
                "amount": round(remaining, 2),
                "percentage": round((remaining / total_amount) * 100, 2),
                "due": "On completion",
            })
        
        return {
            "total_amount": round(total_amount, 2),
            "number_of_payments": len(schedule),
            "schedule": schedule,
        }
    
    def compare_estimates(
        self,
        estimate1: Dict[str, Any],
        estimate2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare two estimates
        """
        diff = {
            "total_difference": estimate2["total"] - estimate1["total"],
            "total_difference_pct": ((estimate2["total"] - estimate1["total"]) / estimate1["total"]) * 100 if estimate1["total"] > 0 else 0,
            "subtotal_difference": estimate2["subtotal"] - estimate1["subtotal"],
            "item_count_difference": len(estimate2["line_items"]) - len(estimate1["line_items"]),
        }
        
        return diff


# Singleton service
estimate_engine = EstimateEngineService()
