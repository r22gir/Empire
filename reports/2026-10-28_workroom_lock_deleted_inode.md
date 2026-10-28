# Workroom lock — deleted-inode proof

Simulates Oct 23 2026: tmp cleanup unlinked the lock name
while the holder kept flock on the old inode.

- old inode (held after unlink): `340652`
- naive `flock -n PATH true`: exit `0` (created new file: `True`)
- new guard + health up: exit `0` (stderr: 'Workroom lock path missing or unlocked; 127.0.0.1:8000 is healthy')
- new guard + health down: exit `1` (stderr: "curl: (7) Failed to connect to 127.0.0.1 port 9 after 0 ms: Couldn't connect to server\nWorkroom not holding primary lock yet and 127.0.0.1:8000 is not healthy")
- Workroom refresh rebound path: `True` new inode `340653` held `True`

Naive flock creates a new unlocked file and would refuse family start.
The new guard does not create the Workroom lock. Health on loopback
is enough. Workroom re-takes the path so later flock checks see a holder.

{
  "naive_flock_exit": 0,
  "naive_created_file": true,
  "guard_health_up": 0,
  "guard_health_down": 1,
  "refresh_rebound": true,
  "lock_held_after_refresh": true
}
