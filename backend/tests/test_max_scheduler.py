import asyncio
import importlib
import sys
import types
from datetime import datetime
from pathlib import Path


def test_max_scheduler_starts_and_registers_jobs(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    max_dir = Path(__file__).resolve().parents[1] / "app" / "services" / "max"
    if "app.services.max" not in sys.modules or not getattr(
        sys.modules.get("app.services.max"), "__file__", None
    ):
        import app.services  # noqa: F401
        pkg = types.ModuleType("app.services.max")
        pkg.__path__ = [str(max_dir)]
        pkg.__package__ = "app.services.max"
        sys.modules["app.services.max"] = pkg
    sched = importlib.import_module("app.services.max.scheduler")
    MaxScheduler = sched.MaxScheduler
    MORNING_BRIEF_TZ = sched.MORNING_BRIEF_TZ

    scheduler = MaxScheduler()

    async def _noop():
        return None

    for name in [
        "send_daily_brief",
        "check_overdue_tasks",
        "run_sales_followup",
        "send_weekly_report",
        "brain_sync",
        "expire_crypto_payments",
        "nightly_drive_export",
    ]:
        monkeypatch.setattr(scheduler, name, _noop)

    async def _run():
        await scheduler.start()
        try:
            assert scheduler.scheduler.running is True
            assert {job.id for job in scheduler.scheduler.get_jobs()} == {
                "daily_brief",
                "check_tasks",
                "sales_followup",
                "weekly_report",
                "brain_sync",
                "expire_crypto_payments",
                "nightly_drive_export",
            }
            brief = scheduler.scheduler.get_job("daily_brief")
            assert brief.next_run_time is not None
            assert brief.next_run_time > datetime.now(MORNING_BRIEF_TZ)
        finally:
            scheduler.scheduler.shutdown(wait=False)

    asyncio.run(_run())
