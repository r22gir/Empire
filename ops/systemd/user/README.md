# ops/systemd/user — host config overlays

This directory contains **host configuration** for systemd user units on
EmpireDell. The files here are version-controlled so the fixes are
recoverable; the live copies live under
`~/.config/systemd/user/<unit>.d/` and are not in any git repo.

## What lives here

| File | Drop-in path | Purpose |
|---|---|---|
| `empire-portal.service.d/rebuild-deps.conf` | `~/.config/systemd/user/empire-portal.service.d/rebuild-deps.conf` | Make `systemctl --user restart empire-portal.service` succeed from a fresh/pruned `node_modules` state without manual `npm install --include=dev` recovery. |

## How to install (or restore) a drop-in

```bash
# 1. Make sure the drop-in dir exists
mkdir -p ~/.config/systemd/user/empire-portal.service.d/

# 2. Copy the file
cp ops/systemd/user/empire-portal.service.d/rebuild-deps.conf \
   ~/.config/systemd/user/empire-portal.service.d/rebuild-deps.conf

# 3. Reload systemd so it picks up the new drop-in
systemctl --user daemon-reload

# 4. (Re)start the service to verify
systemctl --user restart empire-portal.service
systemctl --user status empire-portal.service
```

## How to verify the active drop-in matches the repo copy

```bash
diff -u \
  ops/systemd/user/empire-portal.service.d/rebuild-deps.conf \
  ~/.config/systemd/user/empire-portal.service.d/rebuild-deps.conf
# (no output = identical)
```

Or with sha256:

```bash
sha256sum \
  ops/systemd/user/empire-portal.service.d/rebuild-deps.conf \
  ~/.config/systemd/user/empire-portal.service.d/rebuild-deps.conf
```

## Why this directory exists

The Empire app code in this repo is portable. The systemd unit files
in `~/.config/systemd/user/` are host-specific. Small reliability
fixes (like the rebuild-deps drop-in) belong in BOTH places: applied
to the running host now, and tracked in the repo so a fresh clone or
a rebuilt machine can restore the fix with the four commands above.

The `README.md` in this directory is the install/restore procedure
for whichever drops-in we add later. Add new subdirs following the
same shape (`<unit>.service.d/<name>.conf`).

## Related reports

- `../../REPORT-portal-restart-hardening.md` — the audit, the two root
  causes, the verification, and the deferred follow-ups.
