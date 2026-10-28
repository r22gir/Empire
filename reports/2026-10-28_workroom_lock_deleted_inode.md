# Workroom lock — deleted-inode simulation (TEST ONLY)

This file is a **pytest simulation**, not a real-path check on
EmpireDell. A Dell real-path check comes later, after a backup
and Rafael's OK.

Simulates Oct 23 2026: tmp cleanup unlinked the lock name
while the holder kept flock on the old inode.

- naive `flock -n PATH true`: exit `0` (created new file: `True`)
- family guard + Workroom down: exit `0` (stderr: 'family lock path is not a Workroom lock; start does not wait on Workroom')

Naive flock creates a new unlocked file and can steal Workroom's
exclusive lock. The family guard never flocks Workroom's file
and does not wait on Workroom health.

{
  "test_only": true,
  "not_dell_real_path": true,
  "naive_flock_exit": 0,
  "naive_created_file": true,
  "guard_workroom_down": 0
}
