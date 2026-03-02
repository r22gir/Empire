"""
API routers for EmpireBox.
"""
# Import routers with error handling for missing modules
try:
    from app.routers import licenses
except ImportError:
    licenses = None

try:
    from app.routers import shipping
except ImportError:
    shipping = None

try:
    from app.routers import preorders
except ImportError:
    preorders = None

try:
    from app.routers import auth
except ImportError:
    auth = None

try:
    from app.routers import users
except ImportError:
    users = None

try:
    from app.routers import listings
except ImportError:
    listings = None

try:
    from app.routers import messages
except ImportError:
    messages = None

try:
    from app.routers import marketplaces
except ImportError:
    marketplaces = None

try:
    from app.routers import webhooks
except ImportError:
    webhooks = None

try:
    from app.routers import ai
except ImportError:
    ai = None

__all__ = [
    "licenses",
    "shipping",
    "preorders",
    "auth",
    "users",
    "listings",
    "messages",
    "marketplaces",
    "webhooks",
    "ai"
]