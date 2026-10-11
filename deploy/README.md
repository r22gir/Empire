# EmpireDell family-data ops

Host tooling for the EmpireDell box that stores family edition data under `/data`.
This directory is install-only. It does not deploy application code.

| Script | Purpose |
|---|---|
| `backup_family_data.sh` | Nightly encrypted `tar.zst` of family trees onto BACKUP1, restore-test, retention, optional rclone |
| `disk_watch.sh` | 80% warn / 90% critical on `/`, `/data`, and `/media/rg/BACKUP1`; dry-run cleanup list |

Systemd user units live in `systemd/user/`. The short host runbook is
[`docs/runbooks/empiredell-family-data.md`](../docs/runbooks/empiredell-family-data.md).

## BACKUP1 (the destination)

The host backup target is the external drive **BACKUP1**:

| | |
|---|---|
| Mount | `/media/rg/BACKUP1` |
| Size | ~931G |
| Filesystem | vfat / FAT32 |
| Backup dir | `/media/rg/BACKUP1/family-backups` (`BACKUP_DIR`) |

FAT32 constraints the script is written for:

- **May be unplugged.** If `/media/rg/BACKUP1` is not a real mount, the script
  exits non-zero and **does not write**. An unmounted `/media/rg/BACKUP1` is
  often an empty directory on `/` — writing there would fill the root disk.
- **No Unix permissions.** Dest files are not chmod/chown'd. Archives are
  **encrypted** (gpg symmetric, or age if the key is an age identity).
- **4GiB−1 max file size.** Larger encrypted blobs are split into
  `*.part00`, `*.part01`, … each ≤ 4294967295 bytes (`FAT_MAX_BYTES`).
- **No colons in filenames.** Stamps look like `20261011T031500`, not ISO
  timestamps with `:`.

## What is backed up

From `DATA_ROOT` (default `/data`):

- `amp/`
- `maxine/`
- `minimax-meter/`
- `family-help/` (including `memory.md` and `conversations.db` when present)

Also packed when they exist: `family-help/memory.md`, `family-help/conversations.db`,
`maxine/memory.md`, `maxine/conversations.db`.

Plain `tar.zst` is built in a local temp dir, encrypted, then copied onto
BACKUP1. Every `*.db` is snapshotted with `sqlite3 .backup` (or `VACUUM INTO`)
so a live backend cannot tear `conversations.db`. Restore-test decrypts the
dest file (re-joining parts if needed), lists contents, extracts to a
throwaway dir, and runs `PRAGMA integrity_check` on each restored database.

## Encryption key (never commit)

```bash
mkdir -p ~/.config/empire-backup
# gpg passphrase file (default). Do not put this in git.
openssl rand -base64 32 > ~/.config/empire-backup/key
chmod 600 ~/.config/empire-backup/key
```

Or an age identity (`AGE-SECRET-KEY-1...`) at the same path — the script
uses `age` when the file looks like an identity.

Override with `BACKUP_KEY_FILE`. The path is gitignored. If the key is
missing, the backup exits non-zero with setup instructions.

### One-time: copy the key to a second safe place

BACKUP1 is FAT32 (no Unix permissions) and can be lost or stolen. The
archive is only as safe as this key. **Once**, copy
`~/.config/empire-backup/key` somewhere that is **not** BACKUP1:

- a password manager
- paper in a safe
- a second encrypted USB that does not stay plugged into EmpireDell

Then record that you did it (the script only checks this marker; it does
not verify the second copy):

```bash
date -Iseconds > ~/.config/empire-backup/key-copied
```

If the marker is missing the backup still runs, but it logs a **WARN**.
Do not skip this step.

## Optional: personal Max / Workroom (off by default)

Family backups never include personal Max or Workroom data. To also write
a **separate** archive with a **separate** key:

```bash
openssl rand -base64 32 > ~/.config/empire-backup/max-key
chmod 600 ~/.config/empire-backup/max-key
# copy max-key off-box, then:
date -Iseconds > ~/.config/empire-backup/max-key-copied

# env (or pass --include-max)
BACKUP_INCLUDE_MAX=1
MAX_BACKUP_DIR=/media/rg/BACKUP1/max-backups
MAX_KEY_FILE=~/.config/empire-backup/max-key
MAX_DATA_ROOT=/data          # workroom, empire, max trees when present
MAX_DB_PATHS=~/empire-data/empire.db
```

That set goes to `/media/rg/BACKUP1/max-backups/` as `max-data-*.tar.zst.gpg`.
It is skipped unless `BACKUP_INCLUDE_MAX=1` or `--include-max`. The Max key
must not be the same file as the family key.

## Install (backup)

Dependencies: `tar`, `zstd`, `sqlite3`, `gpg` (or `age` + `age-keygen`). Optional: `rclone`.

```bash
# 1. Plug in BACKUP1 and confirm the mount (vfat, ~931G)
findmnt /media/rg/BACKUP1
# SOURCE … /media/rg/BACKUP1  vfat

# 2. Key (once). Never commit it. Then copy it off-box (see above).
mkdir -p ~/.config/empire-backup
openssl rand -base64 32 > ~/.config/empire-backup/key
chmod 600 ~/.config/empire-backup/key
# …copy ~/.config/empire-backup/key to a second safe place, then:
date -Iseconds > ~/.config/empire-backup/key-copied

# 3. Optional env (rclone). BACKUP_DIR already defaults correctly.
mkdir -p ~/.config/empire
cat > ~/.config/empire/family-backup.env <<'EOF'
BACKUP_DIR=/media/rg/BACKUP1/family-backups
# RCLONE_REMOTE=crypt:empire-family
EOF

# 4. User units (linger so timers fire while logged out)
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

Manual run (drive must be mounted):

```bash
./deploy/backup_family_data.sh
```

The script exits non-zero on any failure (drive absent, missing key, empty
archive, failed restore-test, failed rclone).

## Install (disk watch)

```bash
cp deploy/systemd/user/empire-disk-watch.service \
   deploy/systemd/user/empire-disk-watch.timer \
   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now empire-disk-watch.timer
```

Watches `/`, `/data`, and `/media/rg/BACKUP1`. If BACKUP1 is unplugged the
watch treats that as a **warning** (it will not `df` the empty stub on `/`).

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
| Daily | 14 newest | `$BACKUP_DIR/daily/family-data-YYYYMMDDTHHMMSS.tar.zst.gpg` (or `.age`; plus `.partNN` if split) |
| Weekly | 8 newest | `$BACKUP_DIR/weekly/` (promoted on Sunday) |

## Offsite (optional)

Local dest files are already encrypted. Set `RCLONE_REMOTE` if you also want
a copy off-box (a `crypt:` remote is still fine):

```bash
rclone config
echo 'RCLONE_REMOTE=crypt:empire-family' >> ~/.config/empire/family-backup.env
```

If `RCLONE_REMOTE` is set and rclone fails, the backup exits non-zero.

## Restore

Never restore on top of a live `/data` without a current extra copy.
Need the key file.

```bash
# 1. Confirm BACKUP1 is mounted
findmnt /media/rg/BACKUP1
ls -lt /media/rg/BACKUP1/family-backups/daily /media/rg/BACKUP1/family-backups/weekly

# 2. Decrypt (join parts first if you see .part00)
KEY=~/.config/empire-backup/key
SRC=/media/rg/BACKUP1/family-backups/daily/family-data-YYYYMMDDTHHMMSS.tar.zst.gpg
# cat "$SRC".part[0-9][0-9] > /tmp/assembled.gpg   # only if split
gpg --batch --pinentry-mode loopback --passphrase-file "$KEY" \
  --decrypt -o /tmp/family.tar.zst "$SRC"

# 3. Same checks the nightly job runs
zstd -t /tmp/family.tar.zst
tar --zstd -tf /tmp/family.tar.zst | less

# 4. Extract to a staging directory, not /data
mkdir -p /tmp/family-restore
tar --zstd -xf /tmp/family.tar.zst -C /tmp/family-restore

# 5. Confirm memory.md / conversations.db and SQLite integrity
find /tmp/family-restore -name memory.md -o -name conversations.db
find /tmp/family-restore -name '*.db' -exec sqlite3 {} 'PRAGMA integrity_check;' \;

# 6. Stop family services, then replace trees
#    (see docs/runbooks/empiredell-family-data.md)
rsync -aH --delete /tmp/family-restore/amp/ /data/amp/
# …repeat for maxine, minimax-meter, family-help
```

Age identity keys: `age -d -i ~/.config/empire-backup/key -o /tmp/family.tar.zst "$SRC"`.

From an rclone remote:

```bash
rclone copy crypt:empire-family /tmp/family-offsite-restore
# then decrypt as above
```

## Tests

Tests use temp dirs only and never touch `/data` or `/media/rg/BACKUP1`:

```bash
./deploy/tests/run.sh
```
