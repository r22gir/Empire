import asyncio
from datetime import datetime


def test_max_scheduler_starts_and_registers_jobs(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    from app.services.max.scheduler import MaxScheduler, MORNING_BRIEF_TZ

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
