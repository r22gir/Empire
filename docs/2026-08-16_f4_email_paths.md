# F4-B Document — Gmail OAuth Drop-In Path Fix

**Date:** 2026-08-16
**Branch:** `feature/drawing-standard`
**Commit:** F4 (companion to fix(h48)+F4 — email tooling)
**Scope:** `/home/rg/.config/systemd/user/empire-backend.service.d/gmail-oauth-runtime.conf`

## The fix

The `gmail-oauth-runtime.conf` drop-in pointed `GMAIL_TOKEN_PATH` and
`GMAIL_CREDENTIALS_PATH` to the stale fork:

```
Environment=GMAIL_TOKEN_PATH=/home/rg/empire-repo/backend/token.json
Environment=GMAIL_CREDENTIALS_PATH=/home/rg/empire-repo/backend/credentials.json
```

This is a CLAUDE.md doctrine violation — `~/empire-repo` is the
STALE FORK. The active repo is `~/empire-repo-main`. The companion
`zz-gmail-stable.conf` (systemd `zz-` prefix loads last) was already
overriding these at runtime, but the primary drop-in still referenced
the stale path.

The fix repoints both to the canonical config dir:

```
Environment=GMAIL_TOKEN_PATH=/home/rg/.config/empirebox/gmail/token.json
Environment=GMAIL_CREDENTIALS_PATH=/home/rg/.config/empirebox/gmail/credentials.json
```

The `/.config/empirebox/gmail/` dir already existed (Apr–Jun 2026) with
live `credentials.json` (406 bytes) and `token.json` (743 bytes).

## Why this is a runtime-only edit (not a git commit)

The systemd drop-in lives outside the repo at
`/home/rg/.config/systemd/user/`. It is a host-level configuration
file, not project code. The fix is applied on the live host only.

## Verification (live end-to-end)

After the fix, `systemctl --user restart empire-backend` was issued
and the new env vars were verified in the running process:

```
PID=1957439
GMAIL_TOKEN_PATH=/home/rg/.config/empirebox/gmail/token.json
GMAIL_CREDENTIALS_PATH=/home/rg/.config/empirebox/gmail/credentials.json
```

A real `send_email` was dispatched through the live chat:

```
POST /api/v1/max/chat
  message: "Send me a quick email saying F4-B path verification hello."
  → tool: send_email success=True
  → result: {"sent_to": "empirebox2026@gmail.com", "subject": "F4-B path verification hello",
             "attachments_sent": 0, "body_verified": true}
```

(Founder confirmed: "the 'hello' email ARRIVED in the founder inbox
(2:00 PM) — send path is proven live end-to-end.")

## Stale-fork grep — REMAINING references (REPORT, NOT FIXED)

The user requested a grep of ALL drop-ins and `.conf` files for
`~/empire-repo/`. Reports below; only the email-related ones were
fixed in this commit.

### Live drop-ins (canonical repo behavior)

| File | Line | Status | Action |
|------|------|--------|--------|
| `~/.config/systemd/user/empire-backend.service.d/gmail-oauth-runtime.conf` | 2, 3 | **FIXED** | Both env vars now point to `~/.config/empirebox/gmail/` |
| `~/.config/systemd/user/empire-backend.service.d/zz-gmail-stable.conf` | 4, 5 | Already canonical | (kept as belt-and-suspenders override) |
| `~/.config/systemd/user/empire-backend.service.d/zz-canonical-venv.conf` | 5, 6 | Canonical | (already on `~/empire-repo-main/`) |
| `~/.config/systemd/user/empire-backend.service.d/founder-pin.conf` | — | n/a | FOUNDER_PIN only |
| `~/.config/systemd/user/empire-backend.service.d/gemini.conf` | 2 | Canonical | `~/.config/empirebox/gemini.env` |
| `~/.config/systemd/user/empire-backend.service.d/max-email-whitelist.conf` | — | n/a | Allowlist only |
| `~/.config/systemd/user/empire-backend.service.d/provider-env.conf` | 2 | Canonical | `~/.config/empirebox/empire-backend.env` |
| `~/.config/systemd/user/empire-backend.service.d/smtp.conf` | 2 | Canonical | `~/.config/empirebox/empire-backend-smtp.env` |

### Inactive/legacy service files (NOT live, NOT fixed)

| File | Lines | Status |
|------|-------|--------|
| `~/.config/systemd/user/empire-backend.service` | 8 (`ExecStart`), 11 (`PATH`) | **LEGACY** — superseded by `zz-canonical-venv.conf` |
| `~/.config/systemd/user/empire-backend-feature.service` | 8, 11 | **DEAD** — feature branch service, not active |
| `~/.config/systemd/user/empire-openclaw.service.bak.20260708_233448` | 8, 9 | **BACKUP** — old backup |
| `~/.config/systemd/user/empire-backend.service.bak.20260607T152051` | 8, 11 | **BACKUP** — old backup |

These are not in the active systemd unit chain. The `zz-` drop-ins
override the legacy `empire-backend.service` ExecStart/PATH, so the
stale paths in the legacy file are not actually used. Cleaning them
up is a separate housekeeping task.

### Backend code references (deferred to F4+ work)

The repo's `backend/app/**` contains the following stale-fork refs:

| File | Line | Purpose |
|------|------|---------|
| `app/services/max/system_prompt.py` | 471, 535 | Self-heal reference (read-only) |
| `app/services/max/self_heal.py` | 9 | `REPO_PATH` default (used by Code Mode healing) |
| `app/services/max/monitor.py` | 157 | Local `inbox/` filesystem scan (not Gmail) |
| `app/services/max/scheduler.py` | 118, 345 | Local `inbox/` filesystem scan |
| `app/services/quote_engine/mockup_matcher.py` | 391 | Generated mockup path |
| `app/services/drawing/canonical_path.py` | many | The canonical-path **guard** — actively rejects stale-fork writes; not a leak |

These are NOT in the F4 scope per the brief ("fix only email-related
ones this commit"). They are tracked for a future dispatch.

## Doctrine notes

- The brief explicitly scoped F4-B to email paths only. Non-email
  stale-fork references are reported but not fixed in this commit.
- The `~/.config/systemd/user/...` drop-ins are HOST-level config,
  not project code. The doctrine treats them as out-of-scope for git.
- The fix is durable: the canonical paths are now the primary source,
  and `zz-gmail-stable.conf` reasserts them defensively.
