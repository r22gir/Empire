"""
Amazon SP-API module for MarketF — package init (Phase 0 scaffolding).

Exports the primary public API of this module.
See docs/MARKETF_AMAZON_SPEC.md for full documentation.
"""

from .compliance import ComplianceManager, KillSwitchError
from .product_validator import ProductValidator, ValidationResult
from .sp_api_client import SPAPIClient, SPAPIError

__all__ = [
    "SPAPIClient",
    "SPAPIError",
    "ComplianceManager",
    "KillSwitchError",
    "ProductValidator",
    "ValidationResult",
]
