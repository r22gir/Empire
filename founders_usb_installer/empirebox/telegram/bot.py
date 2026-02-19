"""Main EmpireBox Telegram bot application."""

import logging
import os
from typing import Any

import yaml
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from handlers import BotHandlers
from notifications import NotificationService
from openclaw_client import OpenClawClient
from security import SecurityManager
from voice_handler import VoiceHandler

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def load_config(path: str) -> dict[str, Any]:
    """Load YAML config, with environment variable overrides."""
    with open(path) as fh:
        cfg = yaml.safe_load(fh)

    # Allow token override via environment
    token_env = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token_env:
        cfg.setdefault("telegram", {})["bot_token"] = token_env

    openclaw_host_env = os.environ.get("OPENCLAW_HOST")
    if openclaw_host_env:
        cfg.setdefault("openclaw", {})["host"] = openclaw_host_env

    return cfg


def main() -> None:
    config_path = os.environ.get("CONFIG_PATH", "/app/config.yaml")
    cfg = load_config(config_path)

    tg_cfg = cfg.get("telegram", {})
    oc_cfg = cfg.get("openclaw", {})

    bot_token: str = tg_cfg.get("bot_token", "")
    if not bot_token or bot_token == "YOUR_BOT_TOKEN_HERE":
        raise ValueError(
            "Telegram bot token is not set. "
            "Edit config.yaml or set the TELEGRAM_BOT_TOKEN environment variable."
        )

    security = SecurityManager(tg_cfg)
    openclaw = OpenClawClient(
        host=oc_cfg.get("host", "http://openclaw:7878"),
        timeout=oc_cfg.get("timeout", 30),
    )

    app = Application.builder().token(bot_token).build()

    notifications = NotificationService(
        bot=app.bot,
        config=tg_cfg.get("notifications", {}),
        allowed_users=tg_cfg.get("allowed_users", []),
    )

    handlers = BotHandlers(
        security=security,
        openclaw=openclaw,
        notifications=notifications,
    )

    # Voice handler
    voice_cfg = cfg.get("voice", {})
    voice_handler = VoiceHandler(
        openclaw=openclaw,
        voice_service_url=voice_cfg.get("service_url", "http://voice-service:8200"),
        voice_replies=voice_cfg.get("voice_replies", True),
        always_voice_reply=voice_cfg.get("always_voice_reply", False),
        show_transcript=voice_cfg.get("show_transcript", True),
        reply_voice=voice_cfg.get("reply_voice", "en_US-amy-medium"),
    )

    # Register command handlers
    app.add_handler(CommandHandler("start", handlers.cmd_start))
    app.add_handler(CommandHandler("help", handlers.cmd_help))
    app.add_handler(CommandHandler("status", handlers.cmd_status))
    app.add_handler(CommandHandler("list", handlers.cmd_list))
    app.add_handler(CommandHandler("start_product", handlers.cmd_start_product))
    app.add_handler(CommandHandler("stop_product", handlers.cmd_stop_product))
    app.add_handler(CommandHandler("bundle", handlers.cmd_bundle))
    app.add_handler(CommandHandler("logs", handlers.cmd_logs))
    app.add_handler(CommandHandler("health", handlers.cmd_health))
    app.add_handler(CommandHandler("backup", handlers.cmd_backup))
    app.add_handler(CommandHandler("voice", voice_handler.cmd_voice))

    # Voice message handler
    if voice_cfg.get("enabled", True):
        app.add_handler(
            MessageHandler(filters.VOICE, voice_handler.handle_voice_message)
        )

    # Fallback: forward plain text messages to OpenClaw
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message)
    )

    async def on_startup(application: Application) -> None:
        await notifications.start_monitoring()
        logger.info("EmpireBox Telegram bot started.")

    app.post_init = on_startup

    logger.info("Starting bot (polling)…")
    app.run_polling()


if __name__ == "__main__":
    main()
