"""
Database models for EmpireBox.
"""
# License and shipping models
try:
    from app.models.license import License
except ImportError:
    License = None

try:
    from app.models.shipment import Shipment
except ImportError:
    Shipment = None

try:
    from app.models.preorder import PreOrder
except ImportError:
    PreOrder = None

# User and marketplace models
try:
    from app.models.user import User
except ImportError:
    User = None

try:
    from app.models.listing import Listing
except ImportError:
    Listing = None

try:
    from app.models.message import Message
except ImportError:
    Message = None

try:
    from app.models.marketplace_account import MarketplaceAccount
except ImportError:
    MarketplaceAccount = None

__all__ = [
    "License",
    "Shipment",
    "PreOrder",
    "User",
    "Listing",
    "Message",
    "MarketplaceAccount"
]