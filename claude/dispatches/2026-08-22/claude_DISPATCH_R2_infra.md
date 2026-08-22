# DISPATCH R2 — BACKUPS, ZOMBIE UNITS, THE 03:00 PROCESS
**Date:** 2026-08-22 · **To:** M3 (EmpireDell)
**Predecessor:** `R1_BRAIN_MIGRATION_2026-08-22.md` (complete, commit `e07881c`)
**Reference:** `EMPIREBOX_ORIENTATION_BRIEF_2026-08-22.md` §4, §5

Three independent parts. A and C are the valuable ones. **Stop-gated.**

---

## HARD RULES

1. **🛑 STOP after each part.** Report and wait. Do not chain.
2. **Do not restart `empire-backend.service`.** R1 just landed; the brain is
   writing canonical and tonight's 23:00 `brain_sync` is the verification.
   A restart is allowed ONLY if Part B explicitly requires it and you have
   said so and stopped first.
3. **Do not touch `~/empire-data/brain/*`** — R1 territory, finished.
4. `sqlite3` CLI is NOT installed; use `~/empire-repo-main/backend/venv/bin/python`.
5. Repo doctrine: `~/empire-repo-main` is THE repo. `~/empire-repo` is the
   PREVIOUS PRODUCTION LANE — now frozen except OpenClaw's heartbeat. Do not
   delete it. Do not "clean it up."
6. Known false alarm: `FOUNDER_PIN env var is UNSET` at import. The PIN is set.

---

## PART A — MAKE BACKUPS ACTUALLY WORK

`backup-daily.sh` has never run and points at the OLD LANE. It reads DBs from
`~/empire-repo/backend/data/` — which is frozen and stale. **It would not have
protected `~/empire-data/empire.db` (24 MB: 49 quotes, 32 invoices, 171
customers) even if it had been running every night.**

### A1 — Map what exists
```
ls -la ~/empire-repo/scripts/backup*
crontab -l 2>&1
systemctl --user list-timers --all
systemctl list-timers --all | grep -i backup
ls -la ~/backups/ | head -20
du -sh ~/backups/ 2>/dev/null
```
Report: is anything scheduled to run these today? Was one ever run?

### A2 — Write a NEW canonical script, do not patch the old one
Create `~/empire-repo-main/scripts/backup-canonical.sh`. Requirements:

- **Sources — canonical only:**
  - `~/empire-data/empire.db` (the corridor DB — the important one)
  - `~/empire-data/intake.db`
  - `~/empire-data/brain/{memories,token_usage,unified_messages}.db`
  - `~/empire-repo-main/max/memory.md`
- **SQLite-safe copies.** Never bare `cp` on a live DB. Use the venv python and
  the backup API, which is safe against concurrent writers:
  ```python
  src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
  dst = sqlite3.connect(dest)
  src.backup(dst); dst.close(); src.close()
  ```
- **Destination:** `~/backups/YYYY-MM-DD_HHMM/`
- **Verify after writing:** row count of one known table per DB, and
  `PRAGMA integrity_check`. Exit non-zero if any check fails.
- **NO DELETION.** Do not port the `-mtime +30 -exec rm -rf` retention from the
  old script. Retention gets designed later, deliberately. A backup script that
  deletes is a backup script that can lose data.
- **Log** to `~/backups/backup.log` with timestamp, per-file result, exit code.
- No `git stash`. No writes into any repo tree.

Print the script in full before running it.

### A3 — Run it and prove it
```
bash ~/empire-repo-main/scripts/backup-canonical.sh; echo "exit=$?"
ls -la ~/backups/$(date +%Y-%m-%d)*/
tail -20 ~/backups/backup.log
```
Then prove the backup is restorable — open the backed-up `empire.db` read-only
and count `quotes_v2`, `customers`, `invoices`. **Compare against the live DB.**
A backup nobody has read is not a backup.

### A4 — Retire the misleading script
Do NOT delete `~/empire-repo/scripts/backup-daily.sh` (old lane is frozen).
Instead note in the report that it targets a dead tree and must not be
scheduled. If A1 found it in a crontab or timer, **report that and stop** —
removing a schedule is a founder decision.

Commit the new script to `feature/drawing-standard`. Push.

🛑 **STOP.** Report: script content, run output, restore proof, commit hash.

---

## PART B — ZOMBIE AND MISPOINTED UNITS

Three systemd defects from `DB_TRUTH_FORK_2026-08-22B.md` Part C.

### B1 — Confirm current state first
```
systemctl status empire-openclaw.service --no-pager | head -20
systemctl show empire-openclaw.service -p NRestarts -p UnitFileState
journalctl -u empire-openclaw.service --since today --no-pager | wc -l
systemctl --user cat empire-backend-feature.service
systemctl --user is-enabled empire-backend-feature.service
systemctl --user is-active empire-backend-feature.service
```

### B2 — The zombie
System `empire-openclaw.service`: enabled, points at the old lane, fails
`EADDRINUSE` on 7878 forever because the **canonical user unit** holds the port.
~70,000 restart cycles.

```
sudo systemctl mask empire-openclaw.service
systemctl is-enabled empire-openclaw.service
```
Mask, not disable — mask makes it unstartable, which is
"make the wrong thing unreachable, not merely discouraged."

**Confirm the real OpenClaw is unaffected:**
```
systemctl --user is-active empire-openclaw.service
curl -s -m 5 http://localhost:7878/health
```
If the user unit is NOT the one holding 7878, **STOP immediately and report** —
the assumption is wrong and masking could take OpenClaw down.

### B3 — The mispointed feature unit
`empire-backend-feature.service` (:8020) runs the old-lane venv. Report whether
it is enabled/active. **If active, stop here and report** — something may depend
on :8020. If inactive and disabled, repoint ExecStart and PATH at
`~/empire-repo-main/backend/venv`. Do not start it.

### B4 — Move ExecStart out of the drop-in
The main user unit's `ExecStart` names the old-lane venv and is only saved by
`zz-canonical-venv.conf`. Remove the drop-in and it silently reverts to the old
venv. Fix the unit file itself so the canonical path is the default, and keep
the drop-in for env vars only.

**Do not `daemon-reload` or restart in this part.** Edit the file, show the
diff, and stop. The change takes effect on the next restart, which is a
separate decision.

🛑 **STOP.** Report each unit's before/after state.

---

## PART C — WHAT RUNS AT 03:00?

At 2026-08-22 03:00 something created `~/empire-repo/max/memory.md` with
**April 28 content** — a stale file written over a location that had been
updated at 23:00 the night before. Different inode, birth timestamp 03:00.
Unidentified. It is still running, and we do not know what else it touches.

**Read-only. Identify, do not change.**

```
crontab -l 2>&1
sudo crontab -l 2>&1
ls -la /etc/cron.d/ /etc/cron.daily/ /etc/cron.hourly/ 2>/dev/null
systemctl list-timers --all --no-pager
systemctl --user list-timers --all --no-pager
grep -rn '03:00\|"3"\|hour=3\|0 3 \* \* \*' ~/empire-repo-main/backend/app --include='*.py' | head -20
grep -rn 'CronTrigger\|add_job' ~/empire-repo-main/backend/app --include='*.py' | head -30
```

Anything with a 03:00 schedule — name it and say what it writes.

Then look for a restore/sync mechanism, since the file's content went *backwards*:
```
grep -rln 'rsync\|restore\|sync' ~/empire-repo-main/scripts ~/empire-repo/scripts 2>/dev/null | head
journalctl --since "2026-08-22 02:55" --until "2026-08-22 03:10" --no-pager | head -60
ls -la ~/empire-repo/max/
stat ~/empire-repo/max/memory.md
```

Check whether anything else got the same treatment overnight:
```
find ~/empire-repo ~/empire-repo-main -newermt '2026-08-22 02:55' \
  ! -newermt '2026-08-22 03:10' -type f 2>/dev/null | head -40
```
**That last one is the key probe** — a list of everything written in that
15-minute window names the process by its footprint.

🛑 **STOP.** State plainly: what runs at 03:00, what it wrote, and whether it
touches anything in scope. If undetermined, say **CANNOT DETERMINE** and list
what was ruled out.

---

## REPORT

`~/R2_INFRA_2026-08-22.md`, section per part, then:
```
## VERIFIED
## INFERRED
## COULD NOT PROBE
```
Print at the end:
```
BACKUP RUNS AND VERIFIES: YES/NO
BACKUP RESTORE PROVEN: YES/NO
ZOMBIE UNIT MASKED: YES/NO
REAL OPENCLAW UNAFFECTED: YES/NO
03:00 PROCESS IDENTIFIED: <name or CANNOT DETERMINE>
```
