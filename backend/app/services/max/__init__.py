"""MAX AI Assistant Manager - Multi-model AI router with Telegram integration."""
from .ai_router import AIRouter
from .telegram_bot import TelegramBot
from .desk_manager import DeskManager

__all__ = ["AIRouter", "TelegramBot", "DeskManager"]
