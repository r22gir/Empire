"""MAX AI Assistant Manager - Multi-model AI router with Telegram integration."""
from .ai_router import AIRouter
from .telegram_bot import TelegramBot
from .desks import AIDeskManager

__all__ = ["AIRouter", "TelegramBot", "AIDeskManager"]
