# Family start while Workroom is down (TEST ONLY)

This file is a **pytest simulation**, not a real-path check on
EmpireDell. A Dell real-path check comes later, after a backup
and Rafael's OK. Nothing here was deployed or restarted.

Workroom lock missing, health on 127.0.0.1:9 (down).
Family edition remaps EMPIRE_WORKER_LOCK onto /data/<instance>/run,
the ExecStartPre guard exits 0, the instance lock is taken, and
primary-only jobs stay off.

- guard exit: `0`
- family lock created: `True`
- Workroom lock created: `False`
- should_start_primary_jobs(True): `False`

{
  "test_only": true,
  "not_dell_real_path": true,
  "workroom_down": true,
  "guard_exit": 0,
  "family_lock": true,
  "workroom_lock_created": false,
  "primary_jobs": false
}
