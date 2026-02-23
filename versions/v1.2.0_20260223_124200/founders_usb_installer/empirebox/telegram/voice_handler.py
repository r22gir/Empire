"""Telegram voice message handler for EmpireBox."""

import logging
import os
from typing import Optional

import aiohttp
from telegram import Update, Voice
from telegram.ext import ContextTypes

from openclaw_client import OpenClawClient

logger = logging.getLogger(__name__)

_voice_enabled_users: set[int] = set()


class VoiceHandler:
    """Handles incoming Telegram voice messages and optional voice replies."""

    def __init__(
        self,
        openclaw: OpenClawClient,
        voice_service_url: str = "http://voice-service:8200",
        voice_replies: bool = True,
        always_voice_reply: bool = False,
        show_transcript: bool = True,
        reply_voice: str = "en_US-amy-medium",
    ):
        self._openclaw = openclaw
        self._voice_url = voice_service_url.rstrip("/")
        self._voice_replies = voice_replies
        self._always_voice_reply = always_voice_reply
        self._show_transcript = show_transcript
        self._reply_voice = reply_voice

    # ── Public handlers ─────────────────────────────────────────────────────

    async def handle_voice_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Process an incoming Telegram voice message end-to-end."""
        message = update.message
        voice: Optional[Voice] = message.voice

        if voice is None:
            return

        await message.reply_text("🎙 Transcribing your voice message…")

        # 1. Download .ogg from Telegram
        try:
            tg_file = await context.bot.get_file(voice.file_id)
            ogg_bytes = await tg_file.download_as_bytearray()
        except Exception as exc:
            logger.exception("Failed to download voice file: %s", exc)
            await message.reply_text("⚠️ Could not download voice message.")
            return

        # 2. Send to voice-service /stt
        transcript_result = await self._transcribe(bytes(ogg_bytes))
        if transcript_result is None:
            await message.reply_text("⚠️ Transcription failed.")
            return

        transcript = transcript_result.get("text", "").strip()
        language = transcript_result.get("language", "en")

        if not transcript:
            await message.reply_text("🤷 Could not understand the audio.")
            return

        if self._show_transcript:
            await message.reply_text(f"📝 *Transcript:* {transcript}", parse_mode="Markdown")

        # 3. Send transcript to OpenClaw
        await message.reply_text("🤔 Asking OpenClaw…")
        ai_response = await self._openclaw.chat(transcript)

        user_id = message.from_user.id if message.from_user else None
        should_voice = self._should_send_voice(user_id)

        if should_voice:
            # 4. Convert AI response to speech
            audio_bytes = await self._synthesise(ai_response, language)
            if audio_bytes:
                await message.reply_voice(audio_bytes)
                return

        # Fallback: text reply
        await message.reply_text(ai_response)

    async def cmd_voice(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Toggle voice replies: /voice on | /voice off."""
        user_id = update.effective_user.id if update.effective_user else None
        if user_id is None:
            return

        arg = context.args[0].lower() if context.args else ""

        if arg == "on":
            _voice_enabled_users.add(user_id)
            await update.message.reply_text("🔊 Voice replies *enabled* for you.", parse_mode="Markdown")
        elif arg == "off":
            _voice_enabled_users.discard(user_id)
            await update.message.reply_text("🔇 Voice replies *disabled* for you.", parse_mode="Markdown")
        else:
            status = "on" if user_id in _voice_enabled_users else "off"
            await update.message.reply_text(
                f"Voice replies are currently *{status}*.\n"
                "Use `/voice on` or `/voice off` to change.",
                parse_mode="Markdown",
            )

    # ── Private helpers ─────────────────────────────────────────────────────

    def _should_send_voice(self, user_id: Optional[int]) -> bool:
        """Return True when this user should receive a voice reply."""
        if not self._voice_replies:
            return False
        if self._always_voice_reply:
            return True
        if user_id is not None and user_id in _voice_enabled_users:
            return True
        return False

    async def _transcribe(self, audio_bytes: bytes) -> Optional[dict]:
        """Call the voice service STT endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field(
                    "file",
                    audio_bytes,
                    filename="voice.ogg",
                    content_type="audio/ogg",
                )
                async with session.post(
                    f"{self._voice_url}/stt",
                    data=form,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        logger.error("STT request failed: HTTP %s", resp.status)
                        return None
                    return await resp.json()
        except Exception as exc:
            logger.exception("STT request error: %s", exc)
            return None

    async def _synthesise(self, text: str, language: str = "en") -> Optional[bytes]:
        """Call the voice service TTS endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field("text", text)
                form.add_field("voice", self._reply_voice)
                async with session.post(
                    f"{self._voice_url}/tts",
                    data=form,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        logger.error("TTS request failed: HTTP %s", resp.status)
                        return None
                    return await resp.read()
        except Exception as exc:
            logger.exception("TTS request error: %s", exc)
            return None
