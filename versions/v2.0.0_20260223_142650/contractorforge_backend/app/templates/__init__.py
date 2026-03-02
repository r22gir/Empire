"""
Industry Template Registry
Central registry for all industry templates
"""
from typing import Dict
from app.templates.base import IndustryTemplate
from app.templates.workroom import luxeforge
from app.templates.electrician import electricforge
from app.templates.landscaping import landscapeforge


class TemplateRegistry:
    """Registry for all industry templates"""
    
    def __init__(self):
        self._templates: Dict[str, IndustryTemplate] = {}
        self._register_default_templates()
    
    def _register_default_templates(self):
        """Register the default industry templates"""
        self.register(luxeforge)
        self.register(electricforge)
        self.register(landscapeforge)
    
    def register(self, template: IndustryTemplate):
        """Register a new industry template"""
        self._templates[template.industry_code] = template
    
    def get(self, industry_code: str) -> IndustryTemplate:
        """Get template by industry code"""
        if industry_code not in self._templates:
            raise ValueError(f"Unknown industry template: {industry_code}")
        return self._templates[industry_code]
    
    def list_all(self) -> Dict[str, IndustryTemplate]:
        """Get all registered templates"""
        return self._templates.copy()
    
    def get_industry_names(self) -> Dict[str, str]:
        """Get mapping of industry codes to display names"""
        return {
            code: template.industry_name
            for code, template in self._templates.items()
        }


# Singleton registry
registry = TemplateRegistry()


def get_template(industry_code: str) -> IndustryTemplate:
    """Convenience function to get a template"""
    return registry.get(industry_code)
