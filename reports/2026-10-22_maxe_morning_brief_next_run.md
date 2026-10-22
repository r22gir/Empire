# Max-e Morning Brief next_run port (from PR #198)

**Instance:** Max-e (Juan) · base `family/amp-live-20261014`  
**Source:** PR #198 / `cursor/maxine-morning-brief-next-run-3070` (Maxine)  
**Rule:** 8:00 AM America/New_York, forward recovery only, **no catch-up send**, at most one brief per ET day.

No live SMTP. Fake owner `juan.owner@example.com` only.

---

## Bug (same shape as Maxine)

`MaxScheduler.start()` registered Daily Morning Brief as `CronTrigger(hour=8, minute=0)` with **no timezone**. A persisted / computed `next_run` in the past (example: Oct 18 while the clock was Oct 21 10:40 PM ET) was kept. APScheduler’s 1s misfire window then dropped the job. The daily email may never fire — or a restart could catch up missed days.

## Fix (ported)

- `CronTrigger(..., timezone="America/New_York")`, `misfire_grace_time=1`, `coalesce=True`
- `next_morning_brief_run()` always returns the next **future** 8:00 AM ET slot
- Persist `{last_sent_date, next_run, timezone}` at `EMPIRE_DATA_DIR/scheduler/morning_brief.json`
- Stale `next_run` → recover forward, **do not send**
- `should_send_morning_brief()` is true only inside today’s 8:00 AM ET 60s window and only if not already sent today

## Proof: Oct 21 10:40 PM ET, stale next_run Oct 18

```
now        = 2026-10-21T22:40:00-04:00
stale      = 2026-10-18T08:00:00-04:00
recovered  = 2026-10-22T08:00:00-04:00
sent       = []
last_sent  = 2026-10-18   (unchanged — no catch-up)
```

Restart twice the same ET day after a real 8:00 AM send: still one email; `next_run` is the next morning.

## Test output (no real sends)

```
python3 -m pytest tests/test_morning_brief_schedule.py tests/test_max_scheduler.py -v --tb=short

tests/test_morning_brief_schedule.py::test_next_run_is_always_forward_in_et PASSED
tests/test_morning_brief_schedule.py::test_utc_now_does_not_shift_the_et_slot PASSED
tests/test_morning_brief_schedule.py::test_naive_datetime_is_treated_as_et_not_utc PASSED
tests/test_morning_brief_schedule.py::test_past_next_run_recovers_without_catch_up PASSED
tests/test_morning_brief_schedule.py::test_past_next_run_start_does_not_send_catch_up PASSED
tests/test_morning_brief_schedule.py::test_restart_twice_in_a_day_does_not_double_send PASSED
tests/test_morning_brief_schedule.py::test_missed_morning_slot_is_not_caught_up PASSED
tests/test_morning_brief_schedule.py::test_dst_spring_forward_lands_on_8am_edt PASSED
tests/test_morning_brief_schedule.py::test_dst_fall_back_lands_on_8am_est PASSED
tests/test_morning_brief_schedule.py::test_recover_after_dst_fall_back_ignores_stale_edt_next_run PASSED
tests/test_morning_brief_schedule.py::test_cron_trigger_uses_america_new_york PASSED
tests/test_max_scheduler.py::test_family_max_scheduler_still_registers_morning_brief PASSED
tests/test_max_scheduler.py::test_max_scheduler_starts_and_registers_jobs PASSED

======================== 13 passed, 2 warnings in 1.00s ========================
```

Sends are mocked. No live SMTP. Did not commit `.env`, `business.json`, or `client_aliases.json`.
