import asyncio


def test_max_scheduler_starts_and_registers_jobs(monkeypatch):
    from app.services.max.scheduler import MaxScheduler

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
            }
        finally:
            scheduler.scheduler.shutdown(wait=False)

    asyncio.run(_run())
