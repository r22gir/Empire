# Workroom lock — deleted-inode simulation (TEST ONLY)

This file is a **pytest simulation**, not a real-path check on
EmpireDell. A Dell real-path check comes later, after a backup
and Rafael's OK.

Simulates Oct 23 2026: tmp cleanup unlinked the lock name
while the holder kept flock on the old inode.

- naive `flock -n PATH true`: exit `0` (created new file: `True`)
- new guard + health up: exit `0` (stderr: 'Workroom lock path missing or unlocked; 127.0.0.1:8000 is healthy')
- new guard + health down: exit `1` (stderr: "curl: (7) Failed to connect to 127.0.0.1 port 9 after 0 ms: Couldn't connect to server\nWorkroom not holding primary lock yet and 127.0.0.1:8000 is not healthy")

Naive flock creates a new unlocked file and can steal Workroom's
exclusive lock. The family guard never flocks Workroom's file.
Health on loopback is enough when the name is gone.

{
  "test_only": true,
  "not_dell_real_path": true,
  "naive_flock_exit": 0,
  "naive_created_file": true,
  "guard_health_up": 0,
  "guard_health_down": 1
}
