"""
MAX Telegram Bot - 2-way communication with Founder.
"""

import os
import logging
import asyncio
from typing import Optional, Callable, Dict, Any
import httpx

logger = logging.getLogger("max.telegram")


class TelegramBot:
    """
    Telegram bot for MAX <-> Founder communication.
    Supports sending updates and receiving commands.
    """
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.founder_chat_id = os.getenv("TELEGRAM_FOUNDER_CHAT_ID")
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        
    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token and self.founder_chat_id)
    
    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict] = None
    ) -> bool:
        """Send a message to the Founder or specified chat."""
        if not self.is_configured:
            logger.warning("Telegram not configured, message not sent")
            return False
        
        target_chat = chat_id or self.founder_chat_id
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "chat_id": target_chat,
                    "text": text,
                    "parse_mode": parse_mode
                }
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                    
                response = await client.post(
                    f"{self.api_base}/sendMessage",
                    json=payload
                )
                response.raise_for_status()
                logger.info(f"Telegram message sent to {target_chat}")
                return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def send_task_update(
        self,
        task_name: str,
        status: str,
        details: Optional[str] = None,
        desk: Optional[str] = None
    ):
        """Send a formatted task update to Founder."""
        status_emoji = {
            "started": "🚀",
            "completed": "✅",
            "failed": "❌",
            "pending": "⏳",
            "needs_input": "❓"
        }.get(status, "📋")
        
        message = f"{status_emoji} <b>Task Update</b>\n\n"
        message += f"<b>Task:</b> {task_name}\n"
        message += f"<b>Status:</b> {status.upper()}\n"
        if desk:
            message += f"<b>Desk:</b> {desk}\n"
        if details:
            message += f"\n<i>{details}</i>"
        
        await self.send_message(message)
    
    async def send_daily_summary(self, summary: Dict[str, Any]):
        """Send daily summary to Founder."""
        message = "📊 <b>Daily Summary from MAX</b>\n\n"
        
        message += f"<b>Tasks Completed:</b> {summary.get('completed', 0)}\n"
        message += f"<b>Tasks Pending:</b> {summary.get('pending', 0)}\n"
        message += f"<b>Tasks Failed:</b> {summary.get('failed', 0)}\n\n"
        
        if summary.get('highlights'):
            message += "<b>Highlights:</b>\n"
            for highlight in summary['highlights'][:5]:
                message += f"• {highlight}\n"
        
        if summary.get('needs_attention'):
            message += "\n<b>⚠️ Needs Attention:</b>\n"
            for item in summary['needs_attention'][:3]:
                message += f"• {item}\n"
        
        await self.send_message(message)
    
    async def send_urgent_alert(self, title: str, message: str):
        """Send urgent alert to Founder."""
        alert = f"🚨 <b>URGENT: {title}</b>\n\n{message}"
        
        # Send with inline keyboard for quick actions
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Acknowledge", "callback_data": "ack_alert"},
                    {"text": "📞 Call Me", "callback_data": "call_founder"}
                ]
            ]
        }
        
        await self.send_message(alert, reply_markup=reply_markup)
    
    def register_handler(self, command: str, handler: Callable):
        """Register a command handler."""
        self._handlers[command] = handler
        logger.info(f"Registered Telegram handler for /{command}")
    
    async def start_polling(self):
        """Start polling for updates (run in background task)."""
        if not self.is_configured:
            logger.warning("Telegram not configured, polling not started")
            return
        
        self._running = True
        offset = 0
        
        logger.info("Starting Telegram polling...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while self._running:
                try:
                    response = await client.get(
                        f"{self.api_base}/getUpdates",
                        params={"offset": offset, "timeout": 20}
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        await self._process_update(update)
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Telegram polling error: {e}")
                    await asyncio.sleep(5)
    
    async def _process_update(self, update: Dict):
        """Process incoming Telegram update."""
        message = update.get("message", {})
        callback_query = update.get("callback_query")
        
        if callback_query:
            # Handle button clicks
            callback_data = callback_query.get("data", "")
            logger.info(f"Received callback: {callback_data}")
            # TODO: Handle callbacks
            return
        
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        
        # Only process messages from Founder
        if str(chat_id) != str(self.founder_chat_id):
            logger.warning(f"Ignoring message from unauthorized chat: {chat_id}")
            return
        
        if text.startswith("/"):
            # Command handling
            parts = text[1:].split(" ", 1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            handler = self._handlers.get(command)
            if handler:
                await handler(args, chat_id)
            else:
                await self.send_message(f"Unknown command: /{command}")
        else:
            # Regular message - treat as instruction to MAX
            handler = self._handlers.get("message")
            if handler:
                await handler(text, chat_id)
    
    def stop_polling(self):
        """Stop the polling loop."""
        self._running = False


# Global instance
telegram_bot = TelegramBot()
