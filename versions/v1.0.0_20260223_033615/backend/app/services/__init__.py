"""
Business logic services for EmpireBox.
"""
# License and shipping services
try:
    from app.services.license_service import LicenseService
except ImportError:
    LicenseService = None

try:
    from app.services.shipping_service import ShippingService
except ImportError:
    ShippingService = None

try:
    from app.services.preorder_service import PreOrderService
except ImportError:
    PreOrderService = None

# Auth services
try:
    from app.services.auth_service import signup_user, login_user, refresh_access_token
except ImportError:
    signup_user = login_user = refresh_access_token = None

# User services
try:
    from app.services.user_service import (
        get_user_by_id,
        update_user_profile,
        get_subscription_info
    )
except ImportError:
    get_user_by_id = update_user_profile = get_subscription_info = None

# Listing services
try:
    from app.services.listing_service import (
        create_listing,
        get_user_listings,
        get_listing_by_id,
        update_listing,
        delete_listing,
        publish_listing
    )
except ImportError:
    create_listing = get_user_listings = get_listing_by_id = None
    update_listing = delete_listing = publish_listing = None

# Message services
try:
    from app.services.message_service import (
        get_user_messages,
        get_message_by_id,
        mark_message_read
    )
except ImportError:
    get_user_messages = get_message_by_id = mark_message_read = None

# AI services
try:
    from app.services.ai_service import AIService
except ImportError:
    AIService = None

__all__ = [
    # License and shipping
    "LicenseService",
    "ShippingService",
    "PreOrderService",
    # Auth
    "signup_user",
    "login_user",
    "refresh_access_token",
    # User
    "get_user_by_id",
    "update_user_profile",
    "get_subscription_info",
    # Listing
    "create_listing",
    "get_user_listings",
    "get_listing_by_id",
    "update_listing",
    "delete_listing",
    "publish_listing",
    # Message
    "get_user_messages",
    "get_message_by_id",
    "mark_message_read",
    # AI
    "AIService",
]