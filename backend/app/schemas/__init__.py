"""
Pydantic schemas for EmpireBox API.
"""
# License schemas
try:
    from app.schemas.license import (
        LicenseBase,
        LicenseCreate,
        LicenseResponse,
        LicenseValidation,
        LicenseActivation,
        LicenseActivationResponse
    )
except ImportError:
    LicenseBase = LicenseCreate = LicenseResponse = None
    LicenseValidation = LicenseActivation = LicenseActivationResponse = None

# Shipment schemas
try:
    from app.schemas.shipment import (
        Address,
        Parcel,
        ShippingRate,
        RateRequest,
        RateResponse,
        LabelPurchaseRequest,
        ShipmentLabel,
        TrackingEvent,
        TrackingInfo,
        EmailLabelRequest
    )
except ImportError:
    Address = Parcel = ShippingRate = RateRequest = RateResponse = None
    LabelPurchaseRequest = ShipmentLabel = TrackingEvent = TrackingInfo = None
    EmailLabelRequest = None

# Pre-order schemas
try:
    from app.schemas.preorder import (
        PreOrderBase,
        PreOrderCreate,
        PreOrderResponse,
        PreOrderUpdate
    )
except ImportError:
    PreOrderBase = PreOrderCreate = PreOrderResponse = PreOrderUpdate = None

# Auth schemas
try:
    from app.schemas.auth import (
        LoginRequest,
        SignupRequest,
        Token,
        TokenRefreshRequest,
        TokenData
    )
except ImportError:
    LoginRequest = SignupRequest = Token = TokenRefreshRequest = TokenData = None

# User schemas
try:
    from app.schemas.user import (
        UserCreate,
        UserUpdate,
        UserResponse,
        SubscriptionInfo,
        SubscriptionUpgrade
    )
except ImportError:
    UserCreate = UserUpdate = UserResponse = SubscriptionInfo = SubscriptionUpgrade = None

# Listing schemas
try:
    from app.schemas.listing import (
        ListingCreate,
        ListingUpdate,
        ListingResponse,
        PublishRequest,
        PublishResponse
    )
except ImportError:
    ListingCreate = ListingUpdate = ListingResponse = PublishRequest = PublishResponse = None

# Message schemas
try:
    from app.schemas.message import (
        MessageResponse,
        SendMessageRequest,
        AIMessageDraftResponse
    )
except ImportError:
    MessageResponse = SendMessageRequest = AIMessageDraftResponse = None

__all__ = [
    # License
    "LicenseBase",
    "LicenseCreate",
    "LicenseResponse",
    "LicenseValidation",
    "LicenseActivation",
    "LicenseActivationResponse",
    # Shipment
    "Address",
    "Parcel",
    "ShippingRate",
    "RateRequest",
    "RateResponse",
    "LabelPurchaseRequest",
    "ShipmentLabel",
    "TrackingEvent",
    "TrackingInfo",
    "EmailLabelRequest",
    # Pre-order
    "PreOrderBase",
    "PreOrderCreate",
    "PreOrderResponse",
    "PreOrderUpdate",
    # Auth
    "LoginRequest",
    "SignupRequest",
    "Token",
    "TokenRefreshRequest",
    "TokenData",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "SubscriptionInfo",
    "SubscriptionUpgrade",
    # Listing
    "ListingCreate",
    "ListingUpdate",
    "ListingResponse",
    "PublishRequest",
    "PublishResponse",
    # Message
    "MessageResponse",
    "SendMessageRequest",
    "AIMessageDraftResponse",
]