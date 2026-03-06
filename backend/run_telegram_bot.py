#!/usr/bin/env python3
"""
Standalone launcher for MAX Telegram Bot.

Usage:
  cd ~/empire-repo/backend
  source ~/empire-repo/backend/venv/bin/activate
  python run_telegram_bot.py

Required env vars:
  TELEGRAM_BOT_TOKEN       — From @BotFather
  TELEGRAM_FOUNDER_CHAT_ID — Your Telegram user/chat ID
"""

import os
import sys
import asyncio
import signal
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent / ".env")

# Ensure the app package is importable
sys.path.insert(0, str(Path(__file__).parent))

from app.services.max.telegram_bot import telegram_bot


def main():
    if not telegram_bot.bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not set in .env")
        print("   Get one from @BotFather on Telegram")
        sys.exit(1)

    if not telegram_bot.founder_chat_id:
        print("❌ TELEGRAM_FOUNDER_CHAT_ID not set in .env")
        print("   Get your chat ID from @userinfobot on Telegram")
        sys.exit(1)

    print("🤖 Starting MAX Telegram Bot...")
    print(f"   Token: ...{telegram_bot.bot_token[-8:]}")
    print(f"   Chat ID: {telegram_bot.founder_chat_id}")
    print(f"   Backend: http://localhost:8000")
    print()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown(sig, frame):
        print("\n🛑 Stopping bot...")
        telegram_bot.stop_bot()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        loop.run_until_complete(telegram_bot.start_bot())
    except KeyboardInterrupt:
        telegram_bot.stop_bot()
    finally:
        loop.close()
        print("👋 Bot stopped.")


if __name__ == "__main__":
    main()
