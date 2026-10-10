"""MAX AI Assistant Manager - Multi-model AI router with Telegram integration."""
from .ai_router import AIRouter

try:
    from .telegram_bot import TelegramBot
except ImportError:
    TelegramBot = None

try:
    from .desks import AIDeskManager
except ImportError:
    AIDeskManager = None

__all__ = ["AIRouter", "TelegramBot", "AIDeskManager"]

