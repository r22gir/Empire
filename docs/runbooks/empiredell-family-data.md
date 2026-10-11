# EmpireDell family-data runbook

Short ops notes for the host that stores family edition data under `/data`.
Install steps: [`deploy/README.md`](../../deploy/README.md).

## Trees that matter

| Path | Notes |
|---|---|
| `/data/amp` | AMP family edition |
| `/data/maxine` | Maxine; may hold `memory.md` / `conversations.db` |
| `/data/minimax-meter` | MiniMax meter state |
| `/data/family-help` | Family help; `memory.md` and `conversations.db` |

Nightly backup writes `$BACKUP_DIR/daily/family-data-*.tar.zst` (default
`/mnt/backup`), restore-tests the archive, keeps 14 dailies and 8 Sunday
weeklies, and copies offsite when `RCLONE_REMOTE` is set.

## Daily checks

```bash
systemctl --user status empire-family-backup.timer empire-disk-watch.timer
journalctl --user -u empire-family-backup.service -n 50 --no-pager
journalctl --user -u empire-disk-watch.service -n 50 --no-pager
df -h / /data /mnt/backup
ls -lt /mnt/backup/daily | head
```

Disk watch warns at 80% and is critical at 90% on `/` and `/data`. Cleanup
is list-only:

```bash
./deploy/disk_watch.sh --cleanup
```

Do not delete candidates until you have a current backup and have confirmed
they are caches or rebuildable artifacts.

## Restore one tree

1. Stop anything writing that tree (family-help / Maxine / AMP / meter).
2. Follow **Restore** in `deploy/README.md` (extract to `/tmp/family-restore` first).
3. `rsync -aH --delete` the staged tree onto `/data/<name>/`.
4. Confirm `memory.md` and `conversations.db` if those files belong to the tree.
5. Start services and spot-check a conversation or AMP record.

## Move `/data` to a larger drive

Do this on a maintenance window. Keep `/mnt/backup` on a **different** disk
than the new `/data` so a disk failure does not take both copies.

1. Attach the new disk, partition, and filesystem (example: `ext4` on `/dev/sdX1`).
2. Take a backup **and** wait for `empire-family-backup.service` to finish
   successfully (`systemctl --user status`).
3. Stop writers:

   ```bash
   systemctl --user stop empire-family-backup.timer
   # stop family / AMP / Maxine / meter units or containers that use /data
   ```

4. Mount the new filesystem and copy:

   ```bash
   sudo mkdir -p /mnt/data-new
   sudo mount /dev/sdX1 /mnt/data-new
   sudo rsync -aHAX --numeric-ids --info=progress2 /data/ /mnt/data-new/
   ```

5. Compare (sizes and a spot-check of `memory.md` / `conversations.db`):

   ```bash
   sudo du -s /data /mnt/data-new
   sudo find /data /mnt/data-new -name memory.md -o -name conversations.db
   ```

6. Point `/data` at the new disk. Prefer `/etc/fstab` + remount over a bind
   that you will forget:

   ```bash
   # record UUID
   sudo blkid /dev/sdX1
   # add: UUID=…  /data  ext4  defaults,nofail  0  2
   sudo mkdir -p /data.old
   sudo umount /mnt/data-new
   sudo mv /data /data.old
   sudo mkdir /data
   sudo mount /data
   df -h /data
   ```

7. Start services. Confirm AMP / Maxine / family-help / meter read and write.
8. Only after several good nightly backups, remove `/data.old`.
9. Re-enable the backup timer.

If `/` is the volume filling up, moving `/data` off it is the lasting fix.
Caches listed by `disk_watch.sh --cleanup` are a temporary reclaim only.

## If backup or restore-test fails

- The unit must stay failed (`systemctl --user status` non-zero). Do not mark it
  successful by hand.
- Common causes: `/mnt/backup` unmounted, `zstd` missing, a source tree
  vanished, rclone remote misconfigured.
- Fix the cause and run `BACKUP_DIR=/mnt/backup ./deploy/backup_family_data.sh`
  once interactively before re-enabling the timer.

## Alerts

Disk alerts go to Max (`/api/v1/notifications/internal`) and, when email is
configured, `empirebox2026@gmail.com`. If those mechanisms are down, the
watch script logs the condition and exits non-zero so the timer is visible
as failed.
