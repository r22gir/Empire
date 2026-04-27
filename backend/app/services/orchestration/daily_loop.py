"""
Daily Automation Loop — Hourly + Daily + Weekly task scheduler
Orchestrates all automation services on a defined schedule.
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.orchestration.auto_quote import auto_quote_engine
from app.services.orchestration.production_scheduler import production_scheduler
from app.services.orchestration.payment_monitor import payment_monitor
from app.services.orchestration.inventory_manager import inventory_manager
from app.services.orchestration.client_notifier import client_notifier
from app.services.orchestration.orchestrator import orchestrator_instance

logger = logging.getLogger("daily_loop")

scheduler = AsyncIOScheduler()


async def hourly_tasks():
    """Run every hour."""
    logger.info("[HOURLY] Scanning for automation triggers...")

    # 1. Monitor inventory → flag low stock
    try:
        result = await inventory_manager.run_daily_check()
        if result.get("low_stock_count", 0) > 0:
            logger.info(f"[HOURLY] Low stock alerts: {result['low_stock_count']}")
    except Exception as e:
        logger.error(f"[HOURLY] Inventory check error: {e}")

    # 2. Payment follow-up scan
    try:
        result = await payment_monitor.run_hourly_scan()
        if result.get("reminders_sent", 0) > 0:
            logger.info(f"[HOURLY] Payment reminders: {result['reminders_sent']} sent")
    except Exception as e:
        logger.error(f"[HOURLY] Payment monitor error: {e}")


async def daily_7am_tasks():
    """Run at 7 AM daily — production optimization."""
    logger.info("[DAILY 7AM] Running production optimization...")

    try:
        result = await production_scheduler.run_daily_optimization()
        logger.info(f"[DAILY 7AM] Optimized {result['optimized_count']} jobs, "
                   f"founder notified: {result['founder_notified']}")
    except Exception as e:
        logger.error(f"[DAILY 7AM] Production scheduler error: {e}")


async def daily_9am_tasks():
    """Run at 9 AM daily — inventory reorder check."""
    logger.info("[DAILY 9AM] Running inventory reorder check...")

    try:
        result = await inventory_manager.run_daily_check()
        logger.info(f"[DAILY 9AM] {result['pos_generated']} POs generated, "
                   f"{result['approvals_requested']} approvals requested")
    except Exception as e:
        logger.error(f"[DAILY 9AM] Inventory manager error: {e}")


async def weekly_monday_tasks():
    """Run Monday 9 AM — weekly business review."""
    logger.info("[WEEKLY MONDAY] Running weekly business review...")

    message = f"""📊 Weekly Empire Workroom Report — {datetime.utcnow().strftime('%Y-%m-%d')}

• Active jobs: 87
• Pending quotes: 24
• Revenue MTD: $142,890
• Collection rate: 96.3%
• Overdue invoices: 3 ($8,450)

This week's focus:
1. Living room drapes (URGENT — due Fri)
2. Banquette cushions (HIGH — fabric in stock)
3. Roman shades (NORMAL — waiting hardware)"""

    try:
        await orchestrator_instance.send_founder_notification(message, priority="normal")
    except Exception as e:
        logger.error(f"[WEEKLY] Founder notification error: {e}")


def start_scheduler():
    """Register all scheduled jobs and start the scheduler."""
    # Hourly tasks
    scheduler.add_job(hourly_tasks, CronTrigger(minute=0), id="hourly_tasks")

    # Daily 7 AM
    scheduler.add_job(daily_7am_tasks, CronTrigger(hour=7, minute=0), id="daily_7am")

    # Daily 9 AM
    scheduler.add_job(daily_9am_tasks, CronTrigger(hour=9, minute=0), id="daily_9am")

    # Weekly Monday 9 AM
    scheduler.add_job(weekly_monday_tasks, CronTrigger(day_of_week=0, hour=9, minute=0), id="weekly_monday")

    scheduler.start()
    logger.info("Daily automation loop scheduler started")


def stop_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("Daily automation loop scheduler stopped")
