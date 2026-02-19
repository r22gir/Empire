# Industry Templates Guide

Learn how to create custom industry templates for ContractorForge.

## Overview

Industry templates customize ContractorForge for specific service businesses. Each template defines:
- Pricing methods and calculations
- AI conversation prompts
- Measurement types
- Catalog categories
- Workflow stages
- Terminology
- Features

## Creating a New Template

### 1. Create Template Class

Create a new file in `contractorforge_backend/app/templates/`:

```python
# app/templates/plumbing.py
from typing import Dict, List, Any
from app.templates.base import IndustryTemplate, PricingMethod

class PlumbingForgeTemplate(IndustryTemplate):
    """Plumbing contractors template"""
    
    @property
    def industry_name(self) -> str:
        return "PlumbingForge - Plumbers"
    
    @property
    def industry_code(self) -> str:
        return "plumbing"
    
    @property
    def primary_color(self) -> str:
        return "#1E90FF"  # Dodger blue
    
    @property
    def terminology(self) -> Dict[str, str]:
        return {
            "project": "Service Call",
            "customer": "Client",
            "quote": "Estimate",
        }
    
    @property
    def workflow_stages(self) -> List[Dict[str, Any]]:
        return [
            {"code": "inquiry", "name": "Service Request", "order": 1},
            {"code": "quoted", "name": "Estimate Sent", "order": 2},
            {"code": "scheduled", "name": "Scheduled", "order": 3},
            {"code": "in_progress", "name": "In Progress", "order": 4},
            {"code": "completed", "name": "Completed", "order": 5},
        ]
    
    @property
    def measurement_types(self) -> List[str]:
        return ["pipe_length", "fixture_count", "drain_count"]
    
    @property
    def catalog_categories(self) -> List[str]:
        return ["pipe", "fixture", "fitting", "valve", "drain"]
    
    @property
    def pricing_config(self) -> Dict[str, Any]:
        return {
            "hourly_rate": 95.0,
            "trip_charge": 75.0,
            "fixtures": {
                "toilet_install": 250.0,
                "sink_install": 200.0,
                "water_heater": 1200.0,
            },
            "materials_markup": 0.35,
            "emergency_multiplier": 2.0,
        }
    
    @property
    def ai_intake_prompts(self) -> Dict[str, str]:
        return {
            "greeting": "Hi! What plumbing issue can I help with today?",
            "urgency": "Is this an emergency? (leak, burst pipe, etc.)",
            "scope": "Can you describe the work needed?",
            "summary": "Got it! Let me prepare an estimate.",
        }
    
    def calculate_estimate(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate estimate for plumbing work"""
        line_items = []
        subtotal = 0.0
        
        # Trip charge
        trip_charge = self.pricing_config["trip_charge"]
        line_items.append({
            "description": "Service Call",
            "rate": trip_charge,
            "amount": trip_charge,
        })
        subtotal += trip_charge
        
        # Labor or fixtures
        fixtures = project_data.get("measurements", {}).get("fixtures", [])
        for fixture in fixtures:
            fixture_type = fixture["type"]
            if fixture_type in self.pricing_config["fixtures"]:
                price = self.pricing_config["fixtures"][fixture_type]
                line_items.append({
                    "description": fixture_type.replace("_", " ").title(),
                    "rate": price,
                    "amount": price,
                })
                subtotal += price
        
        # Calculate tax
        tax_rate = project_data.get("tax_rate", 0.08)
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        return {
            "line_items": line_items,
            "subtotal": round(subtotal, 2),
            "tax_amount": round(tax_amount, 2),
            "total": round(total, 2),
        }
    
    def validate_measurements(self, measurements: Dict[str, Any]) -> bool:
        """Validate measurements"""
        return True  # Basic validation
    
    @property
    def features_enabled(self) -> Dict[str, bool]:
        return {
            "production_queue": False,
            "permit_tracking": True,
            "crew_dispatch": True,
        }

# Create singleton
plumbingforge = PlumbingForgeTemplate()
```

### 2. Register Template

Add to `app/templates/__init__.py`:

```python
from app.templates.plumbing import plumbingforge

class TemplateRegistry:
    def _register_default_templates(self):
        self.register(luxeforge)
        self.register(electricforge)
        self.register(landscapeforge)
        self.register(plumbingforge)  # Add here
```

### 3. Update Database Enum

Add to `app/models.py`:

```python
class IndustryType(str, enum.Enum):
    WORKROOM = "workroom"
    ELECTRICIAN = "electrician"
    LANDSCAPING = "landscaping"
    PLUMBING = "plumbing"  # Add here
```

### 4. Create Migration

```bash
alembic revision --autogenerate -m "Add plumbing industry"
alembic upgrade head
```

### 5. Add Frontend Support

Create industry landing page at `contractorforge_web/src/app/industries/plumbing/page.tsx`

## Template Properties

### Required Properties

| Property | Type | Description |
|----------|------|-------------|
| `industry_name` | str | Display name |
| `industry_code` | str | Unique identifier |
| `primary_color` | str | Hex color code |
| `terminology` | Dict | Custom terms |
| `workflow_stages` | List | Project stages |
| `measurement_types` | List | What to measure |
| `catalog_categories` | List | Product categories |
| `pricing_config` | Dict | Pricing rules |
| `ai_intake_prompts` | Dict | AI questions |

### Required Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `calculate_estimate()` | Dict | Generate quote |
| `validate_measurements()` | bool | Check data validity |

## Pricing Methods

Common pricing patterns:

### Hourly Rate
```python
"hourly_rate": 85.0,
"estimated_hours": 4
```

### Per-Item
```python
"fixtures": {
    "item_type": 150.0
}
```

### Per-Square-Foot
```python
"installation_sqft": {
    "patio": 15.0
}
```

### Per-Width (Custom Workrooms)
```python
"drapery_per_width": {
    "default": 120.0
}
```

## Best Practices

1. **Keep pricing logic simple** - Easy to understand and maintain
2. **Provide good defaults** - Most users won't customize
3. **Add helpful prompts** - Guide AI conversations naturally
4. **Include validation** - Prevent invalid estimates
5. **Document custom fields** - Help future developers

## Testing Your Template

```python
# Test in Python
from app.templates import get_template

template = get_template("plumbing")
project_data = {
    "measurements": {
        "fixtures": [{"type": "toilet_install"}]
    },
    "tax_rate": 0.08
}

estimate = template.calculate_estimate(project_data)
print(estimate)
```

## Examples

See existing templates for reference:
- `app/templates/workroom.py` - Complex pricing with materials
- `app/templates/electrician.py` - Hourly + per-fixture hybrid
- `app/templates/landscaping.py` - Area-based + per-plant

## Support

Questions about creating templates? Email support@contractorforge.com
