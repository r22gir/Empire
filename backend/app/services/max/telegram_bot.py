"""
MAX Telegram Bot — Full-featured bot with voice, photo, and text support.
Routes all messages through the MAX AI router (Grok primary).
"""

import os
import logging
import asyncio
import tempfile
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path
import httpx

logger = logging.getLogger("max.telegram")


class TelegramBot:
    """Telegram bot for MAX <-> Founder communication with voice/photo/text."""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.founder_chat_id = os.getenv("TELEGRAM_FOUNDER_CHAT_ID")
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        self._running = False
        self._app = None
        self.upload_dir = Path.home() / "Empire" / "uploads"

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.founder_chat_id)

    # ── Outbound messaging ──────────────────────────────────────

    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict] = None,
    ) -> bool:
        if not self.is_configured:
            logger.warning("Telegram not configured, message not sent")
            return False
        target_chat = chat_id or self.founder_chat_id
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload: Dict[str, Any] = {"chat_id": target_chat, "text": text, "parse_mode": parse_mode}
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                resp = await client.post(f"{self.api_base}/sendMessage", json=payload)
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def send_task_update(self, task_name: str, status: str, details: Optional[str] = None, desk: Optional[str] = None):
        emoji = {"started": "🚀", "completed": "✅", "failed": "❌", "pending": "⏳", "needs_input": "❓"}.get(status, "📋")
        msg = f"{emoji} <b>Task Update</b>\n\n<b>Task:</b> {task_name}\n<b>Status:</b> {status.upper()}\n"
        if desk:
            msg += f"<b>Desk:</b> {desk}\n"
        if details:
            msg += f"\n<i>{details}</i>"
        await self.send_message(msg)

    async def send_daily_summary(self, summary: Dict[str, Any]):
        msg = "📊 <b>Daily Summary from MAX</b>\n\n"
        msg += f"<b>Completed:</b> {summary.get('completed', 0)}\n"
        msg += f"<b>Pending:</b> {summary.get('pending', 0)}\n"
        msg += f"<b>Failed:</b> {summary.get('failed', 0)}\n\n"
        if summary.get("highlights"):
            msg += "<b>Highlights:</b>\n" + "".join(f"• {h}\n" for h in summary["highlights"][:5])
        if summary.get("needs_attention"):
            msg += "\n<b>⚠️ Needs Attention:</b>\n" + "".join(f"• {i}\n" for i in summary["needs_attention"][:3])
        await self.send_message(msg)

    async def send_urgent_alert(self, title: str, message: str):
        alert = f"🚨 <b>URGENT: {title}</b>\n\n{message}"
        markup = {"inline_keyboard": [[{"text": "✅ Acknowledge", "callback_data": "ack_alert"}]]}
        await self.send_message(alert, reply_markup=markup)

    # ── Voice transcription ─────────────────────────────────────

    def _transcribe_audio(self, audio_path: Path) -> str:
        """Transcribe audio using Whisper."""
        try:
            result = subprocess.run(
                ["whisper", str(audio_path), "--model", "base", "--output_format", "txt",
                 "--output_dir", str(audio_path.parent)],
                capture_output=True, text=True, timeout=120,
            )
            out_file = audio_path.with_suffix(".txt")
            if out_file.exists():
                text = out_file.read_text().strip()
                out_file.unlink(missing_ok=True)
                return text
            return result.stdout.strip() or "Could not transcribe audio."
        except subprocess.TimeoutExpired:
            return "[Transcription timed out]"
        except Exception as e:
            logger.error(f"Whisper error: {e}")
            return f"[Transcription failed: {e}]"

    # ── Download file from Telegram ─────────────────────────────

    async def _download_telegram_file(self, file_id: str, suffix: str = ".ogg") -> Optional[Path]:
        """Download a file from Telegram and return local path."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{self.api_base}/getFile", params={"file_id": file_id})
                resp.raise_for_status()
                file_path = resp.json()["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
                file_resp = await client.get(file_url)
                file_resp.raise_for_status()
                tmp = Path(tempfile.mktemp(suffix=suffix))
                tmp.write_bytes(file_resp.content)
                return tmp
        except Exception as e:
            logger.error(f"Failed to download Telegram file: {e}")
            return None

    # ── Chat with MAX ───────────────────────────────────────────

    async def _chat_with_max(self, text: str, image_filename: Optional[str] = None) -> str:
        """Send message to MAX via the backend API."""
        try:
            payload: Dict[str, Any] = {"message": text, "history": []}
            if image_filename:
                payload["image_filename"] = image_filename
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post("http://localhost:8000/api/v1/max/chat", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    model = data.get("model_used", "")
                    response = data.get("response", "No response.")
                    return f"{response}\n\n<i>— via {model}</i>"
                else:
                    return f"Backend error: {resp.status_code}"
        except Exception as e:
            logger.error(f"MAX chat error: {e}")
            return f"Could not reach MAX: {e}"

    # ── Full bot with python-telegram-bot ────────────────────────

    async def start_bot(self):
        """Start the full Telegram bot using python-telegram-bot."""
        if not self.is_configured:
            logger.warning("Telegram not configured — bot not started")
            return

        try:
            from telegram import Update
            from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
        except ImportError:
            logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
            return

        allowed_ids = {int(self.founder_chat_id)} if self.founder_chat_id else set()

        def is_authorized(update: Update) -> bool:
            return update.effective_chat and update.effective_chat.id in allowed_ids

        # /start command
        async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_authorized(update):
                return
            await update.message.reply_html(
                "🏰 <b>MAX — Empire AI Assistant</b>\n\n"
                "Send me text, voice notes, or photos.\n\n"
                "<b>Commands:</b>\n"
                "/status — System health\n"
                "/desks — List active desks\n"
                "/tasks — Show open tasks\n"
                "/help — Show commands"
            )

        # /status command
        async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_authorized(update):
                return
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get("http://localhost:8000/api/v1/max/health")
                    data = resp.json()
                    msg = (
                        f"⚡ <b>System Status</b>\n\n"
                        f"<b>Service:</b> {data.get('service', 'MAX')}\n"
                        f"<b>Status:</b> {data.get('status', 'unknown')}\n"
                        f"<b>Desks Online:</b> {data.get('desks_online', 0)}\n"
                        f"<b>Telegram:</b> {'✅' if data.get('telegram_configured') else '❌'}"
                    )
                    await update.message.reply_html(msg)
            except Exception as e:
                await update.message.reply_text(f"Could not reach backend: {e}")

        # /desks command
        async def cmd_desks(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_authorized(update):
                return
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get("http://localhost:8000/api/v1/max/desks")
                    desks = resp.json().get("desks", [])
                    if not desks:
                        await update.message.reply_text("No desks configured.")
                        return
                    msg = "🏢 <b>Active Desks</b>\n\n"
                    for d in desks:
                        status_dot = "🟢" if d.get("status") == "idle" else "🟡"
                        msg += f"{status_dot} <b>{d.get('name', d.get('id'))}</b>\n"
                    await update.message.reply_html(msg)
            except Exception as e:
                await update.message.reply_text(f"Error: {e}")

        # /tasks command
        async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_authorized(update):
                return
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get("http://localhost:8000/api/v1/max/tasks", params={"status": "in_progress"})
                    tasks = resp.json().get("tasks", [])
                    if not tasks:
                        await update.message.reply_text("No active tasks.")
                        return
                    msg = "📋 <b>Active Tasks</b>\n\n"
                    for t in tasks[:10]:
                        msg += f"• <b>{t.get('title')}</b> — {t.get('status', 'unknown')}\n"
                    await update.message.reply_html(msg)
            except Exception as e:
                await update.message.reply_text(f"Error: {e}")

        # /help command
        async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_authorized(update):
                return
            await update.message.reply_html(
                "🏰 <b>MAX Commands</b>\n\n"
                "/start — Welcome message\n"
                "/status — System health check\n"
                "/desks — List active desks\n"
                "/tasks — Show open tasks\n"
                "/help — Show this message\n\n"
                "You can also send:\n"
                "💬 <b>Text</b> — Chat with MAX\n"
                "🎤 <b>Voice</b> — Transcribed and sent to MAX\n"
                "📷 <b>Photo</b> — Analyzed with AI vision"
            )

        # Handle text messages
        async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_authorized(update):
                return
            text = update.message.text
            await update.message.reply_chat_action("typing")
            response = await self._chat_with_max(text)
            # Telegram HTML max is 4096 chars
            if len(response) > 4000:
                response = response[:4000] + "\n\n<i>[truncated]</i>"
            await update.message.reply_html(response)

        # Handle voice messages
        async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_authorized(update):
                return
            voice = update.message.voice or update.message.audio
            if not voice:
                return
            await update.message.reply_chat_action("typing")
            await update.message.reply_text("🎤 Transcribing voice...")
            audio_path = await self._download_telegram_file(voice.file_id, suffix=".ogg")
            if not audio_path:
                await update.message.reply_text("Failed to download audio.")
                return
            try:
                transcript = self._transcribe_audio(audio_path)
                await update.message.reply_html(f"📝 <b>Transcript:</b>\n<i>{transcript}</i>")
                response = await self._chat_with_max(transcript)
                if len(response) > 4000:
                    response = response[:4000] + "\n\n<i>[truncated]</i>"
                await update.message.reply_html(response)
            finally:
                audio_path.unlink(missing_ok=True)

        # Handle photo messages
        async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_authorized(update):
                return
            photo = update.message.photo[-1] if update.message.photo else None
            if not photo:
                return
            await update.message.reply_chat_action("typing")
            await update.message.reply_text("📷 Analyzing image...")
            photo_path = await self._download_telegram_file(photo.file_id, suffix=".jpg")
            if not photo_path:
                await update.message.reply_text("Failed to download photo.")
                return
            try:
                # Save to uploads
                dest = self.upload_dir / "images" / f"telegram_{photo_path.name}"
                dest.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.move(str(photo_path), str(dest))
                caption = update.message.caption or "Describe this image in detail."
                response = await self._chat_with_max(caption, image_filename=dest.name)
                if len(response) > 4000:
                    response = response[:4000] + "\n\n<i>[truncated]</i>"
                await update.message.reply_html(response)
            except Exception as e:
                await update.message.reply_text(f"Photo analysis failed: {e}")

        # Build and run the bot
        app = Application.builder().token(self.bot_token).build()
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("status", cmd_status))
        app.add_handler(CommandHandler("desks", cmd_desks))
        app.add_handler(CommandHandler("tasks", cmd_tasks))
        app.add_handler(CommandHandler("help", cmd_help))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

        self._app = app
        self._running = True
        logger.info("🤖 MAX Telegram Bot starting...")

        try:
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            logger.info("🤖 MAX Telegram Bot is running!")
            # Keep running until stopped
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            if app.updater.running:
                await app.updater.stop()
            await app.stop()
            await app.shutdown()
            logger.info("🤖 MAX Telegram Bot stopped")

    def stop_bot(self):
        self._running = False

    # Legacy aliases for backward compat
    async def start_polling(self):
        await self.start_bot()

    def stop_polling(self):
        self.stop_bot()


# Global instance
telegram_bot = TelegramBot()
