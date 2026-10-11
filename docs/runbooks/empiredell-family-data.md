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

Nightly backup writes encrypted archives to
`/media/rg/BACKUP1/family-backups` on the external **BACKUP1** drive
(~931G, vfat/FAT32). It restore-tests (decrypt + list + extract), keeps 14
dailies and 8 Sunday weeklies, and copies offsite when `RCLONE_REMOTE` is set.

BACKUP1 has no Unix permissions (so archives are encrypted with
`~/.config/empire-backup/key`), a 4GiB−1 file-size cap (large blobs are
split), and colon-free names. If the drive is unplugged, `/media/rg/BACKUP1`
is usually an empty directory on `/` — the backup **fails** instead of
writing onto the root disk.

## Daily checks

```bash
systemctl --user status empire-family-backup.timer empire-disk-watch.timer
journalctl --user -u empire-family-backup.service -n 50 --no-pager
journalctl --user -u empire-disk-watch.service -n 50 --no-pager
findmnt /media/rg/BACKUP1
df -h / /data /media/rg/BACKUP1
ls -lt /media/rg/BACKUP1/family-backups/daily | head
```

If `findmnt` shows nothing, plug BACKUP1 in and wait for the desktop/usbmount
to attach it. Do not `mkdir` backups under the empty stub.

Disk watch warns at 80% and is critical at 90% on `/`, `/data`, and
`/media/rg/BACKUP1`. An unmounted BACKUP1 is a warning (not a `df` of `/`).
Cleanup is list-only:

```bash
./deploy/disk_watch.sh --cleanup
```

Do not delete candidates until you have a current backup and have confirmed
they are caches or rebuildable artifacts.

## Restore one tree

1. Confirm BACKUP1 is mounted and you have `~/.config/empire-backup/key`.
2. Stop anything writing that tree (family-help / Maxine / AMP / meter).
3. Follow **Restore** in `deploy/README.md` (decrypt, then extract to
   `/tmp/family-restore` first). Join `.partNN` files with `cat` before decrypt
   if the archive was split for FAT32.
4. `rsync -aH --delete` the staged tree onto `/data/<name>/`.
5. Confirm `memory.md` and `conversations.db` if those files belong to the tree.
6. Start services and spot-check a conversation or AMP record.

## Move `/data` to a larger drive

Do this on a maintenance window. Keep BACKUP1 (`/media/rg/BACKUP1`) on a
**different** disk than the new `/data` so a disk failure does not take both
copies.

1. Attach the new disk, partition, and filesystem (example: `ext4` on `/dev/sdX1`).
   Prefer ext4/xfs for `/data` — not FAT32 (4GiB file cap, no Unix perms).
2. Confirm BACKUP1 is mounted. Take a backup **and** wait for
   `empire-family-backup.service` to finish successfully
   (`systemctl --user status`).
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
- Common causes: BACKUP1 unplugged/unmounted, missing
  `~/.config/empire-backup/key`, `zstd`/`gpg` missing, a source tree vanished,
  rclone remote misconfigured.
- Plug the drive in, `findmnt /media/rg/BACKUP1`, then run
  `./deploy/backup_family_data.sh` once interactively before re-enabling the
  timer.

## Alerts

Disk alerts go to Max (`/api/v1/notifications/internal`) and, when email is
configured, `empirebox2026@gmail.com`. If those mechanisms are down, the
watch script logs the condition and exits non-zero so the timer is visible
as failed.
