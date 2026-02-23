"""Command handlers for the EmpireBox Telegram bot."""

import logging
import subprocess

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from openclaw_client import OpenClawClient
from notifications import NotificationService
from security import SecurityManager

logger = logging.getLogger(__name__)

HELP_TEXT = r"""
*EmpireBox Bot Commands*

/start – Welcome message and setup
/status – Show running products and resources
/list – List all products with status
/start\_product \<name\> – Start a product
/stop\_product \<name\> – Stop a product
/bundle \<name\> – Start a bundle (reseller, contractor, support, full)
/logs \<product\> – Get recent logs (last 50 lines)
/health – Full system health check
/backup – Trigger database backup
/help – Show this message

You can also send a natural language message and the bot will forward it to OpenClaw AI.
"""

WELCOME_TEXT = (
    "👋 *Welcome to EmpireBox Bot!*\n\n"
    "I can help you manage your EmpireBox system remotely.\n"
    "Type /help to see all available commands."
)


def _run_ebox(args: list[str], timeout: int = 30) -> str:
    """Run an `ebox` CLI command and return its output."""
    cmd = ["ebox"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr.strip():
            output = (output + "\n" + result.stderr.strip()).strip()
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "⚠️ Command timed out."
    except FileNotFoundError:
        return "⚠️ `ebox` CLI not found. Is EmpireBox installed?"


class BotHandlers:
    """Registers and handles all Telegram commands."""

    def __init__(
        self,
        security: SecurityManager,
        openclaw: OpenClawClient,
        notifications: NotificationService,
    ):
        self._security = security
        self._openclaw = openclaw
        self._notifications = notifications

    # ── Auth guard ─────────────────────────────────────────────────────────

    async def _guard(self, update: Update) -> bool:
        """Return True if the update should be processed, False otherwise."""
        user = update.effective_user
        if user is None:
            return False
        if not self._security.is_allowed(user.id):
            logger.warning("Blocked user %s (%s)", user.id, user.username)
            await update.message.reply_text("⛔ Access denied.")
            return False
        if not self._security.check_rate_limit(user.id):
            await update.message.reply_text(
                "⏱ Rate limit exceeded. Please wait before sending more commands."
            )
            return False
        return True

    async def _pin_guard(
        self, update: Update, command: str
    ) -> bool:
        """Return True if PIN check passes (or is not required)."""
        user = update.effective_user
        if not self._security.pin_required(command):
            return True
        if self._security.is_pin_verified(user.id):
            return True
        await update.message.reply_text(
            "🔒 This command requires PIN verification.\n"
            "Reply with your PIN code."
        )
        return False

    # ── Command handlers ───────────────────────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        await update.message.reply_text(WELCOME_TEXT, parse_mode=ParseMode.MARKDOWN)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        output = _run_ebox(["status"])
        await update.message.reply_text(f"```\n{output}\n```", parse_mode=ParseMode.MARKDOWN)

    async def cmd_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        output = _run_ebox(["list"])
        await update.message.reply_text(f"```\n{output}\n```", parse_mode=ParseMode.MARKDOWN)

    async def cmd_start_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        if not context.args:
            await update.message.reply_text(r"Usage: /start\_product \<name\>", parse_mode=ParseMode.MARKDOWN)
            return
        product = context.args[0].lower()
        output = _run_ebox(["start", product])
        await update.message.reply_text(f"```\n{output}\n```", parse_mode=ParseMode.MARKDOWN)

    async def cmd_stop_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        if not context.args:
            await update.message.reply_text(r"Usage: /stop\_product \<name\>", parse_mode=ParseMode.MARKDOWN)
            return
        product = context.args[0].lower()
        if not await self._pin_guard(update, "stop_product"):
            return
        output = _run_ebox(["stop", product])
        await update.message.reply_text(f"```\n{output}\n```", parse_mode=ParseMode.MARKDOWN)

    async def cmd_bundle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        if not context.args:
            await update.message.reply_text(
                "Usage: /bundle \\<name\\>\nBundles: reseller, contractor, support, full",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        bundle = context.args[0].lower()
        output = _run_ebox(["bundle", bundle])
        await update.message.reply_text(f"```\n{output}\n```", parse_mode=ParseMode.MARKDOWN)

    async def cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: /logs \\<product\\>", parse_mode=ParseMode.MARKDOWN)
            return
        product = context.args[0].lower()
        output = _run_ebox(["logs", product], timeout=20)
        # Telegram message limit is 4096 chars
        if len(output) > 3800:
            output = output[-3800:]
        await update.message.reply_text(f"```\n{output}\n```", parse_mode=ParseMode.MARKDOWN)

    async def cmd_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        output = _run_ebox(["health"], timeout=30)
        if len(output) > 3800:
            output = output[-3800:]
        await update.message.reply_text(f"```\n{output}\n```", parse_mode=ParseMode.MARKDOWN)

    async def cmd_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        if not await self._pin_guard(update, "backup"):
            return
        await update.message.reply_text("⏳ Running backup…")
        output = _run_ebox(["backup"], timeout=120)
        success = "error" not in output.lower() and "fail" not in output.lower()
        await self._notifications.notify_backup_complete(success, output[:200])
        await update.message.reply_text(f"```\n{output}\n```", parse_mode=ParseMode.MARKDOWN)

    # ── Natural language fallback ──────────────────────────────────────────

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        text = update.message.text or ""
        await update.message.reply_text("🤔 Asking OpenClaw…")
        response = await self._openclaw.chat(text)
        await update.message.reply_text(response)
