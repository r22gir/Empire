# EmpireDell family-data ops

Host tooling for the EmpireDell box that stores family edition data under `/data`.
This directory is install-only. It does not deploy application code.

| Script | Purpose |
|---|---|
| `backup_family_data.sh` | Nightly `tar.zst` of family trees, restore-test, retention, optional rclone |
| `disk_watch.sh` | 80% warn / 90% critical on `/` and `/data`; dry-run cleanup list |

Systemd user units live in `systemd/user/`. The short host runbook is
[`docs/runbooks/empiredell-family-data.md`](../docs/runbooks/empiredell-family-data.md).

## What is backed up

From `DATA_ROOT` (default `/data`):

- `amp/`
- `maxine/`
- `minimax-meter/`
- `family-help/` (including `memory.md` and `conversations.db` when present)

Also packed when they exist: `family-help/memory.md`, `family-help/conversations.db`,
`maxine/memory.md`, `maxine/conversations.db`.

## Install (backup)

Dependencies: `tar`, `zstd`. Optional offsite: `rclone` plus a **crypt** remote.

```bash
# 1. Local backup volume (USB, NAS mount, second disk)
sudo mkdir -p /mnt/backup
sudo chown "$USER:$USER" /mnt/backup

# 2. Optional env (BACKUP_DIR, RCLONE_REMOTE)
mkdir -p ~/.config/empire
cat > ~/.config/empire/family-backup.env <<'EOF'
BACKUP_DIR=/mnt/backup
# Use a crypt remote so the offsite copy is encrypted at rest.
# RCLONE_REMOTE=crypt:empire-family
EOF

# 3. User units (linger so timers fire while logged out)
mkdir -p ~/.config/systemd/user
cp deploy/systemd/user/empire-family-backup.service \
   deploy/systemd/user/empire-family-backup.timer \
   ~/.config/systemd/user/
loginctl enable-linger "$USER"
systemctl --user daemon-reload
systemctl --user enable --now empire-family-backup.timer
systemctl --user list-timers empire-family-backup.timer
```

If the clone is not `~/empire-repo`, edit `ExecStart` / `WorkingDirectory` in the
installed unit before enabling.

Manual run:

```bash
BACKUP_DIR=/mnt/backup ./deploy/backup_family_data.sh
```

The script exits non-zero on any failure (missing tools, empty archive,
failed restore-test, failed rclone).

## Install (disk watch)

```bash
cp deploy/systemd/user/empire-disk-watch.service \
   deploy/systemd/user/empire-disk-watch.timer \
   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now empire-disk-watch.timer
```

Alerts use the existing Max notification API
(`POST /api/v1/notifications/internal`) and, when `SENDGRID_API_KEY` or
`SMTP_USER`/`SMTP_PASSWORD` are set, Max `EmailService`. The only production
recipient is `empirebox2026@gmail.com`. If neither mechanism is available the
script logs the alert and exits non-zero.

Cleanup is dry-run only:

```bash
./deploy/disk_watch.sh --cleanup
```

It lists known growers (`node_modules`, npm caches, `.next`, pip cache,
journald, `/tmp`, `uploads`) and never deletes files.

## Retention

| Class | Keep | Location |
|---|---|---|
| Daily | 14 newest | `$BACKUP_DIR/daily/family-data-YYYYMMDDTHHMMSS.tar.zst` |
| Weekly | 8 newest | `$BACKUP_DIR/weekly/` (promoted on Sunday) |

## Offsite (optional, encrypted)

Set `RCLONE_REMOTE` to an rclone **crypt** remote (not a plaintext bucket):

```bash
rclone config   # create a crypt: remote wrapping gdrive/s3/sftp
echo 'RCLONE_REMOTE=crypt:empire-family' >> ~/.config/empire/family-backup.env
```

If `RCLONE_REMOTE` is set and rclone fails, the backup exits non-zero.

## Restore

Never restore on top of a live `/data` without a current extra copy.

```bash
# 1. Pick an archive (daily or weekly)
ls -lt /mnt/backup/daily /mnt/backup/weekly

# 2. Integrity check (same checks the nightly job runs)
zstd -t /mnt/backup/daily/family-data-YYYYMMDDTHHMMSS.tar.zst
tar --zstd -tf /mnt/backup/daily/family-data-YYYYMMDDTHHMMSS.tar.zst | less

# 3. Extract to a staging directory, not /data
mkdir -p /tmp/family-restore
tar --zstd -xf /mnt/backup/daily/family-data-YYYYMMDDTHHMMSS.tar.zst \
  -C /tmp/family-restore

# 4. Confirm memory.md / conversations.db
find /tmp/family-restore -name memory.md -o -name conversations.db

# 5. Stop family services, then replace trees
#    (see docs/runbooks/empiredell-family-data.md)
rsync -aH --delete /tmp/family-restore/amp/ /data/amp/
# …repeat for maxine, minimax-meter, family-help
```

From an rclone crypt remote:

```bash
rclone copy crypt:empire-family /tmp/family-offsite-restore
```

## Tests

Tests use temp dirs only and never touch `/data` or `/mnt/backup`:

```bash
./deploy/tests/run.sh
```
