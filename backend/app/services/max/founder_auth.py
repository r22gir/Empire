"""
Central founder authentication resolver.
ALL guardrails and tool gates use this. One truth source.
"""
import os

FOUNDER_TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_FOUNDER_CHAT_ID", "")

def is_founder_channel(channel: str, user_context: dict = None) -> bool:
    """web_cc = always founder. telegram + founder chat ID = always founder."""
    if channel in ("web_cc", "web", "cc", "command_center", "command-center", ""):
        return True
    if channel == "telegram" and user_context:
        chat_id = str(user_context.get("chat_id", ""))
        if chat_id and chat_id == FOUNDER_TELEGRAM_CHAT_ID:
            return True
    return False

def get_access_level(channel: str, user_context: dict = None) -> str:
    if is_founder_channel(channel, user_context):
        return "founder"
    if user_context and user_context.get("pin_verified"):
        return "authenticated"
    return "anonymous"
