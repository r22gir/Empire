"""
MAX Telegram Bot — Full-featured bot with voice, photo, and text support.
Routes all messages through the MAX AI router (Grok primary).
"""

import os
import json as _json
import logging
import asyncio
import tempfile
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path
import httpx

logger = logging.getLogger("max.telegram")

# ── Per-chat conversation history — persisted to disk ──
_MAX_HISTORY = 30  # Keep last 30 exchanges per chat (was 10)
_TELEGRAM_CHAT_DIR = Path.home() / "Empire" / "backend" / "data" / "chats" / "telegram"
_TELEGRAM_CHAT_DIR.mkdir(parents=True, exist_ok=True)


def _load_telegram_history(chat_id: str) -> list[dict]:
    """Load conversation history from disk for a chat."""
    path = _TELEGRAM_CHAT_DIR / f"{chat_id}.json"
    if path.exists():
        try:
            data = _json.loads(path.read_text())
            return data.get("messages", [])
        except Exception as e:
            logger.warning(f"Failed to load telegram history for {chat_id}: {e}")
    return []


def _save_telegram_history(chat_id: str, messages: list[dict]):
    """Persist conversation history to disk."""
    path = _TELEGRAM_CHAT_DIR / f"{chat_id}.json"
    try:
        data = {"chat_id": chat_id, "updated_at": __import__('datetime').datetime.utcnow().isoformat(), "messages": messages}
        path.write_text(_json.dumps(data, indent=2, default=str))
    except Exception as e:
        logger.warning(f"Failed to save telegram history for {chat_id}: {e}")


# In-memory cache (loaded from disk on first access per chat)
_telegram_history: dict[str, list[dict]] = {}


def _get_history(chat_id: str) -> list[dict]:
    """Get history for a chat — loads from disk if not in memory."""
    if chat_id not in _telegram_history:
        _telegram_history[chat_id] = _load_telegram_history(chat_id)
    return _telegram_history[chat_id]


def _append_and_save(chat_id: str, role: str, content: str):
    """Add a message to history and persist to disk."""
    history = _get_history(chat_id)
    history.append({"role": role, "content": content})
    # Trim to bounded size
    if len(history) > _MAX_HISTORY * 2:
        history[:] = history[-_MAX_HISTORY * 2:]
    _telegram_history[chat_id] = history
    _save_telegram_history(chat_id, history)


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
                if resp.status_code == 400 and "parse entities" in resp.text.lower():
                    # HTML parse failed (unsupported tags) — retry as plain text
                    payload.pop("parse_mode", None)
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

    async def send_document(
        self,
        file_path: str,
        caption: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> bool:
        """Send a document/file via Telegram."""
        if not self.is_configured:
            logger.warning("Telegram not configured, document not sent")
            return False
        target_chat = chat_id or self.founder_chat_id
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(file_path, "rb") as f:
                    files = {"document": (os.path.basename(file_path), f)}
                    data: Dict[str, Any] = {"chat_id": target_chat}
                    if caption:
                        data["caption"] = caption
                        data["parse_mode"] = "HTML"
                    resp = await client.post(
                        f"{self.api_base}/sendDocument",
                        data=data,
                        files=files,
                    )
                    resp.raise_for_status()
                    return True
        except Exception as e:
            logger.error(f"Failed to send Telegram document: {e}")
            return False

    # ── PDF safety net ─────────────────────────────────────────

    @staticmethod
    def _find_latest_pdf() -> Optional[str]:
        """Find the most recently created PDF (quote or presentation)."""
        pdf_dirs = [
            Path.home() / "Empire" / "data" / "quotes" / "pdf",
            Path.home() / "Empire" / "data" / "presentations",
            Path.home() / "Empire" / "data" / "reports",
        ]
        latest = None
        latest_mtime = 0
        for d in pdf_dirs:
            if d.exists():
                for f in d.glob("*.pdf"):
                    mt = f.stat().st_mtime
                    if mt > latest_mtime:
                        latest_mtime = mt
                        latest = str(f)
        # Only return if created within the last 10 minutes (likely from this conversation)
        import time
        if latest and (time.time() - latest_mtime) < 600:
            return latest
        return None

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

    # ── Inbox + Intent Classification ──────────────────────────

    async def _classify_and_store(self, text: str, telegram_message_id: Optional[int] = None) -> Dict[str, Any]:
        """Classify message intent via AI and store in inbox."""
        import json as _json

        # Classify intent
        classify_prompt = (
            "Classify this message from a business founder into exactly one category. "
            "Respond with ONLY a JSON object, no other text:\n"
            '{"intent": "task|question|instruction|note", '
            '"desk_target": "workroomforge|marketforge|socialforge|amp|recoveryforge|support|null", '
            '"priority": 1-10, '
            '"summary": "one-line summary"}\n\n'
            f"Message: {text}"
        )

        intent_data = {"intent": "note", "desk_target": None, "priority": 5, "summary": text[:100]}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "http://localhost:8000/api/v1/max/chat",
                    json={"message": classify_prompt, "history": []},
                )
                if resp.status_code == 200:
                    raw = resp.json().get("response", "")
                    # Extract JSON from response
                    start = raw.find("{")
                    end = raw.rfind("}") + 1
                    if start >= 0 and end > start:
                        parsed = _json.loads(raw[start:end])
                        intent_data.update({
                            "intent": parsed.get("intent", "note"),
                            "desk_target": parsed.get("desk_target"),
                            "priority": min(10, max(1, int(parsed.get("priority", 5)))),
                            "summary": parsed.get("summary", text[:100]),
                        })
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")

        # Store in inbox
        inbox_msg = {
            "text": text,
            "source": "telegram",
            "telegram_message_id": telegram_message_id,
            **intent_data,
            "ai_summary": intent_data["summary"],
            "status": "received",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post("http://localhost:8000/api/v1/inbox", json=inbox_msg)
                if resp.status_code == 200:
                    inbox_msg = resp.json().get("message", inbox_msg)
        except Exception as e:
            logger.error(f"Inbox storage failed: {e}")

        # If it's a task, create it in the task engine
        if intent_data["intent"] == "task":
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    task_payload = {
                        "title": intent_data["summary"],
                        "description": text,
                        "desk_id": intent_data.get("desk_target") or "operations",
                        "priority": intent_data["priority"],
                    }
                    resp = await client.post("http://localhost:8000/api/v1/max/tasks", json=task_payload)
                    if resp.status_code == 200:
                        task_data = resp.json()
                        inbox_msg["linked_task_id"] = task_data.get("task", {}).get("id")
            except Exception as e:
                logger.error(f"Task creation failed: {e}")

        return intent_data

    # ── Chat with MAX ───────────────────────────────────────────

    async def _chat_with_max(
        self, text: str, image_filename: Optional[str] = None, chat_id: Optional[str] = None,
    ) -> tuple[str, str, list]:
        """Send message to MAX via the backend API with conversation memory.

        Returns (html_response, plain_text, tool_results) — html for Telegram display, plain for TTS, tool results list.
        """
        cid = str(chat_id or self.founder_chat_id or "default")
        history = _get_history(cid)[-_MAX_HISTORY:]
        try:
            payload: Dict[str, Any] = {"message": text, "history": history, "conversation_id": f"telegram-{cid}"}
            if image_filename:
                payload["image_filename"] = image_filename
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post("http://localhost:8000/api/v1/max/chat", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    model = data.get("model_used", "")
                    response = data.get("response", "No response.")
                    tool_results = data.get("tool_results", [])
                    # Persist to disk
                    _append_and_save(cid, "user", text)
                    _append_and_save(cid, "assistant", response)
                    html = f"{response}\n\n<i>— via {model}</i>"
                    return html, response, tool_results
                else:
                    err = f"Backend error: {resp.status_code}"
                    return err, err, []
        except Exception as e:
            logger.error(f"MAX chat error: {e}")
            err = f"Could not reach MAX: {e}"
            return err, err, []

    async def _send_voice_reply(self, update, plain_text: str):
        """Generate TTS audio from plain text and send as Telegram voice note.

        Every response MUST include a voice note — founder listens while driving.
        """
        try:
            from app.services.max.tts_service import tts_service
            if not tts_service.is_configured:
                logger.warning("TTS not configured (OPENAI_API_KEY missing) — voice reply skipped")
                return
            audio_path = await tts_service.synthesize_for_telegram(plain_text)
            if audio_path and audio_path.exists():
                try:
                    await update.message.reply_voice(voice=open(audio_path, "rb"))
                finally:
                    audio_path.unlink(missing_ok=True)
            else:
                logger.warning("TTS synthesis returned no audio — voice reply skipped")
        except Exception as e:
            logger.error(f"TTS voice reply failed: {e}")

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

        # Handle text messages — respond naturally, classify silently in background
        async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_authorized(update):
                return
            text = update.message.text
            msg_id = update.message.message_id

            await update.message.reply_chat_action("typing")

            # Get natural MAX response (always shown to user)
            chat_id = str(update.effective_chat.id) if update.effective_chat else None
            html_response, plain_text, tool_results = await self._chat_with_max(text, chat_id=chat_id)
            if len(html_response) > 4000:
                html_response = html_response[:4000] + "\n\n<i>[truncated]</i>"
            await update.message.reply_html(html_response)

            # Send any documents/files produced by tool execution (deduplicate by path)
            sent_files = set()
            for tr in tool_results:
                if tr.get("success") and tr.get("result"):
                    res = tr["result"]
                    file_path = res.get("file_path") or res.get("pdf_path")
                    if file_path and os.path.exists(file_path) and file_path not in sent_files:
                        caption = res.get("caption", f"📎 {os.path.basename(file_path)}")
                        await self.send_document(file_path, caption=caption, chat_id=chat_id)
                        sent_files.add(file_path)
                    image_url = res.get("image_url") or res.get("url")
                    if image_url and image_url.startswith("http"):
                        try:
                            await update.message.reply_photo(photo=image_url, caption=res.get("caption", ""))
                        except Exception as img_err:
                            logger.warning(f"Failed to send image via Telegram: {img_err}")

            # Safety net: if user asked for a PDF but AI didn't use tools, find and send the latest PDF
            if not sent_files:
                text_lower = text.lower()
                resp_lower = plain_text.lower()
                wants_pdf = any(kw in text_lower for kw in ["pdf", "quote", "send me", "document", "estimate"])
                ai_claims_sent = any(kw in resp_lower for kw in ["sent the pdf", "sending the pdf", "sent to your telegram", "delivered"])
                if wants_pdf or ai_claims_sent:
                    latest_pdf = self._find_latest_pdf()
                    if latest_pdf:
                        logger.info(f"Safety net: sending latest PDF {latest_pdf}")
                        await self.send_document(
                            latest_pdf,
                            caption=f"📎 {os.path.basename(latest_pdf)}",
                            chat_id=chat_id,
                        )
                        sent_files.add(latest_pdf)

            # Send voice reply (TTS)
            await self._send_voice_reply(update, plain_text)

            # Classify and store in inbox silently (background, never shown to user)
            try:
                await self._classify_and_store(text, telegram_message_id=msg_id)
            except Exception as e:
                logger.warning(f"Background classification failed: {e}")

        # Handle voice messages — transcribe then send transcript text to Grok
        async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_authorized(update):
                return
            voice = update.message.voice or update.message.audio
            if not voice:
                return
            await update.message.reply_chat_action("typing")
            await update.message.reply_text("🎤 Transcribing voice...")

            # 1. Download audio file
            audio_path = await self._download_telegram_file(voice.file_id, suffix=".ogg")
            if not audio_path:
                await update.message.reply_text("Failed to download audio.")
                return

            try:
                # 2. Transcribe audio → text (run in thread to avoid blocking event loop)
                loop = asyncio.get_event_loop()
                transcript = await loop.run_in_executor(None, self._transcribe_audio, audio_path)

                # Guard: if transcription failed, tell user and stop
                if not transcript or transcript.startswith("["):
                    await update.message.reply_text(f"Transcription issue: {transcript or 'empty result'}")
                    return

                # 3. Show transcript to user
                await update.message.reply_html(f"📝 <b>Transcript:</b>\n<i>{transcript}</i>")

                # 4. Send transcript TEXT to Grok (same as if user typed it)
                await update.message.reply_chat_action("typing")
                voice_chat_id = str(update.effective_chat.id) if update.effective_chat else None
                html_response, plain_text, _ = await self._chat_with_max(transcript, chat_id=voice_chat_id)
                if len(html_response) > 4000:
                    html_response = html_response[:4000] + "\n\n<i>[truncated]</i>"

                # 5. Send Grok's text response back to Telegram
                await update.message.reply_html(html_response)

                # 5b. Send Grok's response as voice note (TTS)
                await self._send_voice_reply(update, plain_text)

                # 6. Silent background classification
                try:
                    await self._classify_and_store(transcript, telegram_message_id=update.message.message_id)
                except Exception as e:
                    logger.warning(f"Voice classification failed: {e}")
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
                caption = update.message.caption or (
                    "Analyze this image. If it shows a window, window treatment, curtain, drape, "
                    "or furniture that might need upholstery or a window treatment quote, "
                    "estimate the dimensions, identify the treatment type, and use the photo_to_quote tool "
                    "to create a quote and send the PDF. "
                    "If it's not related to windows or furniture, just describe what you see."
                )
                photo_chat_id = str(update.effective_chat.id) if update.effective_chat else None

                # Validate image file (basic magic bytes check)
                try:
                    with open(dest, 'rb') as img_f:
                        header = img_f.read(8)
                    valid_sigs = [b'\xff\xd8\xff', b'\x89PNG', b'RIFF', b'GIF8']
                    if not any(header.startswith(sig) for sig in valid_sigs):
                        await update.message.reply_text("⚠️ Invalid image file. Upload rejected.")
                        dest.unlink(missing_ok=True)
                        return
                except Exception:
                    pass  # If check fails, proceed anyway

                html_response, plain_text, tool_results = await self._chat_with_max(caption, image_filename=dest.name, chat_id=photo_chat_id)
                if len(html_response) > 4000:
                    html_response = html_response[:4000] + "\n\n<i>[truncated]</i>"
                await update.message.reply_html(html_response)

                # Send any documents/files produced by tool execution (deduplicate by path)
                sent_files = set()
                for tr in tool_results:
                    if tr.get("success") and tr.get("result"):
                        res = tr["result"]
                        file_path = res.get("file_path") or res.get("pdf_path")
                        if file_path and os.path.exists(file_path) and file_path not in sent_files:
                            doc_caption = res.get("caption", f"📎 {os.path.basename(file_path)}")
                            await self.send_document(file_path, caption=doc_caption, chat_id=photo_chat_id)
                            sent_files.add(file_path)
                        image_url = res.get("image_url") or res.get("url")
                        if image_url and isinstance(image_url, str) and image_url.startswith("http"):
                            try:
                                await update.message.reply_photo(photo=image_url, caption=res.get("caption", ""))
                            except Exception as img_err:
                                logger.warning(f"Failed to send image via Telegram: {img_err}")

                # Send voice reply (TTS) — every response gets a voice note
                await self._send_voice_reply(update, plain_text)
            except Exception as e:
                await update.message.reply_text(f"Photo analysis failed: {e}")

        # Build and run the bot — increase timeouts for reliability
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=45.0,
            write_timeout=30.0,
            pool_timeout=15.0,
            connection_pool_size=8,
        )
        get_updates_request = HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=90.0,
            write_timeout=30.0,
            pool_timeout=15.0,
        )
        app = (
            Application.builder()
            .token(self.bot_token)
            .request(request)
            .get_updates_request(get_updates_request)
            .build()
        )
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

        # Clear any stale webhook/polling before starting
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.api_base}/deleteWebhook",
                    json={"drop_pending_updates": False},
                )
        except Exception:
            pass

        # Retry startup up to 3 times (previous instance may still hold connection)
        for attempt in range(3):
            try:
                await app.initialize()
                await app.start()
                await app.updater.start_polling(
                    drop_pending_updates=False,
                    allowed_updates=["message", "callback_query"],
                )
                logger.info("🤖 MAX Telegram Bot is running!")
                while self._running:
                    await asyncio.sleep(1)
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"🤖 Telegram Bot attempt {attempt+1}/3 failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(5)
                else:
                    logger.error(f"🤖 Telegram Bot failed after 3 attempts: {e}")
                    print(f"❌ Telegram Bot error: {e}")
                    return
        try:
            if app.updater and app.updater.running:
                await app.updater.stop()
            if app.running:
                await app.stop()
            await app.shutdown()
        except Exception:
            pass
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
