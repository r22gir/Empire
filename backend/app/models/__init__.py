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

# Economic intelligence models
try:
    from app.models.economic import EconomicLedger, EconomicTransaction
except ImportError:
    EconomicLedger = None
    EconomicTransaction = None

# SupportForge models
try:
    from app.models.supportforge_tenant import Tenant
except ImportError:
    Tenant = None

try:
    from app.models.supportforge_agent import SupportAgent
except ImportError:
    SupportAgent = None

try:
    from app.models.supportforge_customer import Customer
except ImportError:
    Customer = None

try:
    from app.models.supportforge_ticket import Ticket
except ImportError:
    Ticket = None

try:
    from app.models.supportforge_message import Message as SFMessage
except ImportError:
    SFMessage = None

try:
    from app.models.supportforge_kb import KBArticle, KBCategory
except ImportError:
    KBArticle = None
    KBCategory = None

try:
    from app.models.supportforge_automation import Automation, SLAPolicy, CannedResponse
except ImportError:
    Automation = None
    SLAPolicy = None
    CannedResponse = None

try:
    from app.models.supportforge_integration import Integration, SatisfactionRating
except ImportError:
    Integration = None
    SatisfactionRating = None

__all__ = [
    # Core models
    "License",
    "Shipment",
    "PreOrder",
    "User",
    "Listing",
    "Message",
    "MarketplaceAccount",
    # Economic Intelligence
    "EconomicLedger",
    "EconomicTransaction",
    # SupportForge
    "Tenant",
    "SupportAgent",
    "Customer",
    "Ticket",
    "SFMessage",
    "KBArticle",
    "KBCategory",
    "Automation",
    "SLAPolicy",
    "CannedResponse",
    "Integration",
    "SatisfactionRating"
]