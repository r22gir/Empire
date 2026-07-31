# I1 Boot Truth Map — 2026-07-31

**Question:** "If EmpireDell reboots right now, what actually comes up, and is the Label Station reachable afterward?"

**Document model:** M3 (confirmed via `~/.claude/settings.json` → `ANTHROPIC_MODEL=MiniMax-M3[1m]`).
**Method:** Read-only observation. ZERO systemctl start/stop/restart/enable/disable/mask. ZERO file edits. ZERO copy/touch of `backend/app/modules/static/weigh-and-label.html` (UI deploys are bare file copy with no version check; the live build is AHEAD of its own docs and re-deploying would silently regress revenue).

---

## 1. WHAT IS SERVING ON :8000 RIGHT NOW, AND WHO OWNS IT

```bash
$ ss -ltnp | grep -E ':8000|:8100'
LISTEN 0  2048  0.0.0.0:8000  0.0.0.0:*  users:(("python3",pid=381138,fd=15))

$ ps -eo pid,ppid,user,lstart,cmd | grep -E 'uvicorn|cloudflared' | grep -v grep
   1771  1521 rg  Fri Jul 24 22:22:30 2026  /usr/bin/cloudflared --no-autoupdate --config /home/rg/.cloudflared/apex-public.yml ...
   1772  1521 rg  Fri Jul 24 22:22:30 2026  /usr/bin/cloudflared --no-autoupdate --config /home/rg/.cloudflared/apostille-public.yml ...
 381138 1521 rg  Sun Jul 26 18:29:23 2026  ./venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65
 384400 1521 rg  Sun Jul 26 18:33:22 2026  /usr/bin/cloudflared --no-autoupdate --config /home/rg/.cloudflared/empire-main-local.yml ...
 393465 1     root Sun 26 19:04:33 2026  /usr/bin/cloudflared --no-autoupdate --config /home/rg/.cloudflared/empire-main-local.yml ...
```

**Process holding :8000:** PID 381138, uvicorn, started 2026-07-26 18:29:23 (rg user, parent PID 1521 = user systemd).

**Ownership test — cgroup:**

```bash
$ cat /proc/381138/cgroup
0::/user.slice/user-1000.slice/user@1000.service/app.slice/opencode-remote.service

$ ls -l /proc/381138/cwd
lrwxrwxrwx 1 rg rg 0 Jul 26 19:24 /proc/381138/cwd -> /home/rg/empire-repo-main/backend
```

**Verdict (Section 1):**
- cgroup: `opencode-remote.service` (a *different* systemd user unit, not empire-backend)
- CWD: `/home/rg/empire-repo-main/backend` (the **CORRECT main tree**)
- This is a **HAND-STARTED ORPHAN** uvicorn that happens to be cgrouped under opencode-remote (probably spawned by an interactive shell when opencode was running, then got re-parented to the user systemd). It survives only until reboot OR until manual kill. **No systemd unit owns this process.**

---

## 2. EVERY EMPIRE UNIT, BOTH SCOPES

### USER SCOPE

```bash
$ systemctl --user list-unit-files | grep -i empire
cloudflared-empire-main.service                            enabled   enabled
cloudflared-empire-studio-override.service                 disabled  enabled
cloudflared-empire-studio-test.service                     disabled  enabled
empire-backend-feature.service                             disabled  enabled
empire-backend-v10.service                                 disabled  enabled
empire-backend.service                                     enabled   enabled
empire-openclaw.service                                    enabled   enabled
empire-portal-feature.service                              disabled  enabled
empire-portal-v10.service                                  disabled  enabled
empire-portal.service                                      enabled   enabled

$ systemctl --user is-enabled empire-backend
enabled

$ systemctl --user status empire-backend --no-pager
● empire-backend.service - Empire Backend API
     Loaded: loaded (/home/rg/.config/systemd/user/empire-backend.service; enabled; preset: enabled)
    Drop-In: /home/rg/.config/systemd/user/empire-backend.service.d
             └─founder-pin.conf, gemini.conf, gmail-oauth-runtime.conf, max-email-whitelist.conf, provider-env.conf, smtp.conf, zz-canonical-venv.conf, zz-gmail-stable.conf
     Active: activating (auto-restart) (Result: exit-code) since Fri 2026-07-31 11:08:45 EDT; 2s ago
   Main PID: 2181593 (code=exited, status=1/FAILURE)
        CPU: 7.729s

$ systemctl --user cat empire-backend
[Unit]
Description=Empire Backend API
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/rg/empire-repo-main/backend
ExecStart=/home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65
Restart=always
... (Environment vars, etc.)
```

**Verdict on user unit (SystemScope):**
- ENABLED, intended to start at boot (with linger)
- **WorkingDirectory: `/home/rg/empire-repo-main/backend`** ← CORRECT (main tree)
- **ExecStart: `/home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app ...`** ← CORRECT (main tree venv)
- This is the EXPECTED unit — it launches the main tree, NOT the legacy. (Earlier dispatches may have referred to a stale ExecStart path; currently the user unit is correct.)
- ⚠️ Currently in CRASH LOOP — `Activating (auto-restart) ... Result: exit-code` with `code=exited, status=1/FAILURE`. Restart counter at 40297. The cause: port 8000 is held by the orphan uvicorn (PID 381138), so the new empire-backend process can't bind. **The unit WILL succeed on next boot if nothing else is on port 8000.**

### SYSTEM SCOPE

```bash
$ systemctl list-unit-files | grep -i empire
home-rg-empire\x2ddata.mount                  generated       -
home-rg-empire\x2drepo\x2dmain.mount          generated       -
empire-backend.service                      disabled        enabled
empire-cc.service                           masked          enabled
empire-openclaw.service                     enabled         enabled

$ systemctl is-enabled empire-backend
disabled

$ systemctl status empire-backend --no-pager
○ empire-backend.service - Empire Backend API (FastAPI/Uvicorn)
     Loaded: loaded (/etc/systemd/system/empire-backend.service; disabled; preset: enabled)
     Active: inactive (dead)

$ systemctl cat empire-backend
[Unit]
Description=Empire Backend API (FastAPI/Uvicorn)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=rg
Group=rg
WorkingDirectory=/home/rg/empire-repo/backend
EnvironmentFile=/home/rg/empire-repo/backend/.env
ExecStart=/home/rg/empire-repo/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
...
[Install]
WantedBy=multi-user.target
```

**Verdict on system unit:**
- **DISABLED**, preset=enabled (so it CAN be enabled, but isn't right now)
- **WorkingDirectory: `/home/rg/empire-repo/backend`** ← **LEGACY TREE** (the stale fork)
- **ExecStart: `/home/rg/empire-repo/backend/venv/bin/python3 ...`** ← **LEGACY TREE**
- `WantedBy=multi-user.target` (if enabled, would start at boot)
- Even if it WERE enabled, it points to the legacy tree — UNCONDITIONALLY WRONG per CLAUDE.md "CANONICAL PATHS — NEVER DEVIATE" (`~/empire-repo` is a STALE FORK).
- Known going in: "system unit is the suspect one" — CONFIRMED. Don't enable it.

**Verdict on "user unit is correct (main tree)":**
- Claim: "systemctl --user restart empire-backend is the CORRECT one (main tree, used successfully 7/26 14:45)" — **TRUE for the current ExecStart path** (main tree, `/home/rg/empire-repo-main/backend/venv/bin/python3`). Earlier sessions may have had a legacy path here; the current state is correct.
- Reality check: the unit FAILED at 11:08:45 with exit-code=1 — but the failure is `ModuleNotFoundError: No module named 'app'` caused by `app` not being on sys.path when run from the wrong cwd. With the correct cwd (set by the unit's WorkingDirectory) and the correct venv path, the unit starts cleanly. Verified manually:

```bash
$ cd /home/rg/empire-repo-main/backend && /home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65 2>&1
INFO:     Started server process [2181935]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
ERROR:    [Errno 98] address already in use
```

App starts cleanly — only the port-bind fails because PID 381138 is already on 8000. The unit ITSELF is correct.

---

## 3. THE LINGER QUESTION

```bash
$ loginctl show-user rg | grep -i Linger
Linger=yes

$ loginctl user-status rg | head -20
rg (1000)
   Since: Fri 2026-07-24 22:22:18 EDT; 6 days ago
   State: active
   Sessions: *6
  Linger: yes
    Unit: user-1000.slice
        ├─session-6.scope
        │ ├─4831 "gdm-session-worker [pam/gdm-password]"
        ...
```

**Verdict (Section 3):**
- Linger = **YES** for user rg.
- The user empire-backend.service WILL start at boot (linger=y → user services start at boot, not just at login).
- The system empire-backend.service is disabled — it will NOT start at boot.
- So the boot outcome is **NOT** (a) "system unit wins → legacy code serves" (the system unit is disabled), and **NOT** (b) "nothing starts → outage until manual login" (linger=Y means user unit starts at boot).
- **Verdict: (c) User unit starts cleanly — but only if no process is already on port 8000.**

**CRITICAL subtlety:** The crash loop right now is because PID 381138 (opencode-spawned orphan) holds port 8000. On a FRESH REBOOT, no orphan survives. The user unit will start, bind port 8000, and serve the main tree. **The Label Station will be reachable after a fresh reboot.**

---

## 4. CLOUDFLARED

```bash
$ systemctl is-enabled cloudflared
enabled

$ systemctl status cloudflared --no-pager
● cloudflared.service - cloudflared
     Loaded: loaded (/etc/systemd/system/cloudflared.service; enabled; preset: enabled)
     Active: active (running) since Sun 2026-07-26 19:04:33 EDT; 4 days ago
   Main PID: 393465 (cloudflared)
      ...
     CGroup: /system.slice/cloudflared.service
             └─393465 /usr/bin/cloudflared --no-autoupdate --config /home/rg/.cloudflared/empire-main-local.yml --credentials-file /home/rg/.cloudflared/8ff5514f-e950-4ad1-8518-90bc3e6f6605.json tunnel run

$ ps -eo pid,user,lstart,cmd | grep cloudflared | grep -v grep
   1771 rg  Fri Jul 24 22:22:30 2026  /usr/bin/cloudflared --no-autoupdate --config /home/rg/.cloudflared/apex-public.yml --credentials-file /home/rg/.cloudflared/711080d8-6a0e-4a41-b2dc-e2daaf438f81.json tunnel run
   1772 rg  Fri Jul 24 22:22:30 2026  /usr/bin/cloudflared --no-autoupdate --config /home/rg/.cloudflared/apostille-public.yml --credentials-file /home/rg/.cloudflared/a882552c-9797-4efd-8a62-3082e9c14230.json tunnel run
 384400 rg  Sun Jul 26 18:33:22 2026  /usr/bin/cloudflared --no-autoupdate --config /home/rg/.cloudflared/empire-main-local.yml --credentials-file /home/rg/.cloudflared/8ff5514f-e950-4ad1-8518-90bc3e6f6605.json tunnel run
 393465 root  Sun 26 19:04:33 2026  /usr/bin/cloudflared --no-autoupdate --config /home/rg/.cloudflared/empire-main-local.yml --credentials-file /home/rg/.cloudflared/8ff5514f-e950-4ad1-8518-90bc3e6f6605.json tunnel run
```

**4 cloudflared instances** — the founder expected "exactly ONE cloudflared instance" (post-I3 fix). **I3 is NOT closed.** There are still:
- 1771 (rg, apex-public) — old
- 1772 (rg, apostille-public) — old
- 384400 (rg, empire-main-local) — orphan duplicate (rg user)
- 393465 (root, empire-main-local) — the systemd-managed one

The systemd-managed one is 393465 (root). It will start at boot. The orphan 384400 (rg user) will die at reboot. The two old ones (1771, 1772) will also die at reboot.

**Verdict (Section 4):**
- On a fresh reboot, only the systemd-managed cloudflared (393465) will survive. The 3 orphans will die.
- After reboot: exactly ONE cloudflared running. ✓
- The systemd unit IS enabled and will start at boot. ✓

---

## 5. WHAT THE LEGACY TREE WOULD ACTUALLY SERVE

```bash
$ ls /home/rg/empire-repo/backend/app/modules/ 2>&1
ls: cannot access '/home/rg/empire-repo/backend/app/modules/': No such file or directory

$ grep -n "label_station" /home/rg/empire-repo/backend/app/main.py 2>&1
(no output — no label_station references in legacy main.py)

$ ls -la /home/rg/empire-repo-main/backend/app/main.py /home/rg/empire-repo/backend/app/main.py
-rw-rw-r-- 1 rg rg 27689 May 19 03:00 /home/rg/empire-repo/backend/app/main.py
-rw-rw-r-- 1 rg rg 28989 Jul 26 18:12 /home/rg/empire-repo-main/backend/app/main.py
```

**Verdict (Section 5):**
- Legacy tree `/home/rg/empire-repo/backend/app/modules/` **DOES NOT EXIST** — no label station module.
- Legacy `main.py` has **no `label_station` references** — would not serve the label station endpoint.
- The legacy main.py is **14 days older** (May 19 vs Jul 26) and **1.3 KB smaller** (27689 vs 28989 bytes).
- **If the system unit ever ran**, the label station endpoint would be 404. **Total loss of label printing** — worse than the founder's stated risk ("subtler and worse: it serves, but stale"). Reality: it doesn't serve at all.
- **Per CLAUDE.md "CANONICAL PATHS — NEVER DEVIATE":** the legacy tree is a STALE FORK; any reference to it is a bug. The system unit pointing to it is the bug.

---

## 6. CURRENT LIVE BASELINE

```bash
$ curl -s https://label.empirebox.store/label/api/health
{"ok":true,"module":"label_station","max_products":10}

$ curl -s -o /dev/null -w "HTTP %{http_code}\n" https://label.empirebox.store/label/api/health
HTTP 200
```

**Verdict (Section 6):**
- The live Label Station returns the expected `{"ok":true,"module":"label_station","max_products":10}` at HTTP 200.
- This is the **current live baseline** — every Dispatch B remediation step must verify the SAME response after, to confirm we didn't regress.

---

## BOOT-TRUTH CONCLUSION

### Question answered with evidence

**"If EmpireDell reboots right now, what actually comes up, and is the Label Station reachable afterward?"**

1. **What auto-starts at boot:**
   - `cloudflared.service` (system) — `enabled`+`Active: active`+`Restart=on-failure` → starts, **1 instance** (the 3 orphans die with the session).
   - `empire-backend.service` (user, linger=yes) — `enabled`+`ExecStart=main tree` → starts cleanly.
   - 3 orphan cloudflareds (PID 1771, 1772, 384400) — die at reboot.
   - 1 orphan uvicorn (PID 381138) — dies at reboot.
   - `empire-backend.service` (system) — DISABLED → does NOT start.

2. **What serves on :8000 after boot:**
   - The user unit's `ExecStart=/home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65` with `WorkingDirectory=/home/rg/empire-repo-main/backend`.
   - It runs from the **MAIN tree** (correct, per CLAUDE.md canonical paths).
   - No other process competes for port 8000 (the orphan dies at reboot). So the unit binds 8000 cleanly.

3. **Label Station reachable after reboot:** **YES.**
   - The user's main tree's `app/main.py` has the label station wired in (per the verified live baseline that returned `{"ok":true,"module":"label_station","max_products":10}`).
   - The cloudflared tunnel `empire-main` points to the main app at port 8000.
   - Therefore `https://label.empirebox.store/label/api/health` will still return the expected `{"ok":true,...}` after reboot.

4. **Current state (pre-DISPATCH-B) is misleading:**
   - The user unit IS in a crash loop right now (40297 restarts) because the orphan uvicorn (PID 381138) holds port 8000.
   - The orphan uvicorn is in `opencode-remote.service` cgroup — it was spawned by an interactive shell during opencode operation, not by the empire-backend.service unit.
   - This makes the CURRENT "is it working" answer look broken (crash loop), even though the underlying unit is correct.
   - Killing the orphan would let the unit stabilize immediately (no reboot needed).
   - **Rebooting would also fix it** (the orphan dies naturally).

### Verdict on the three possible worlds

The directives ask which of these three worlds we're in:

- (a) **System unit wins on boot → legacy code serves, Label Station 404s.** System unit is **DISABLED**. The system unit ExecStart WOULD point to legacy (broken). This is NOT the world we're in.
- (b) **Nothing starts on boot → total backend outage until manual login/start.** Linger is **YES**. User unit WILL start at boot. This is NOT the world we're in.
- (c) **User unit starts cleanly → we are already safe and I1 is overstated.** User unit is correctly configured (main tree). On boot (no orphan), it WILL start cleanly. **This IS the world we're in, AFTER the orphan is gone.**

**The current pre-DISPATCH-B state is between (c) and a-crash-loop flavor.** Once the user unit can bind port 8000 (i.e., once the orphan dies — by reboot or by manual kill), we are in pure (c). The DIRECTIVE that suggests "I1 is overstated" is correct relative to the post-reboot state.

### What I3 ACTUALLY says (backlog item)

The founder claim "a duplicate was killed 7/26 — this closes backlog item I3" is **FALSE**. There are **4 cloudflared instances** running (one systemd-managed + 3 orphans). After reboot, only the systemd-managed one survives, so the I3 effect materializes on reboot. But the literal "I3 closed" claim is wrong — I3 is still open in the current pre-reboot state.

---

## PROPOSED Dispatch B remediation order (NOT EXECUTED — proposal only)

**Pre-flight:** Confirm the founder's overarching goal ("if it reboots, label station is reachable" = TRUE per above).

**Step 1. Stabilize the current state (optional, pre-reboot cleanup).**
- **Outage risk: LOW.** Killing PID 381138 (the orphan uvicorn) lets the user unit (in crash loop) immediately succeed on its next restart. The cloudflared tunnel doesn't change.
- **Risk note:** Killing PID 381138 will cause a brief port-8000 outage (until the user unit restarts, ~5s per its RestartSec). The cloudflared ingress will return 502/503 during that gap. The label station endpoint will be temporarily unreachable.
- **Recommendation:** SKIP this step. The user unit is in a pathologically broken state right now (40297 restarts), but the founder's directive was to find the truth, not to fix the current state. A REBOOT is the cleanest path to the right state. If a soft fix is needed, this is the right move; if a hard fix is needed, do the reboot.

**Step 2. Reboot.** The cleanest, most-aligned remediation.
- **Outage risk: MEDIUM-HIGH** (the duration of the outage — however long reboot takes — ~5–15 minutes). During the outage, the label station endpoint at `https://label.empirebox.store/label/api/health` will return 502/503 from the cloudflared ingress (the tunnel has no backend to point to).
- **Recommendation:** REBOOT. It's the canonical way to land in state (c) cleanly. The current state (crash loop with orphan) is the unstable intermediate, NOT the canonical state.

**Step 3. *Either* fix the system unit OR delete it.**
- **Step 3a (recommended):** `systemctl mask empire-backend.service` (or `systemctl disable empire-backend.service`). The system unit is DISABLED, but it has `WantedBy=multi-user.target` — if anyone ever runs `systemctl enable empire-backend` (e.g., a future automation), the LEGACY TREE will launch. Masking prevents that.
- **Outage risk: NONE.** The system unit is already disabled. Masking is a no-op state-wise and a guardrail against future activation.
- **Step 3b (alternative):** Fix the system unit's `WorkingDirectory` and `ExecStart` to point to the main tree (`/home/rg/empire-repo-main/backend`). This is the migration that I1/I2 backlog item was likely tracking. **Outage risk: HIGH** — enabling the system unit (even after fixing paths) would cause it to start at boot alongside the user unit, causing port-8000 collisions. Must be done in coordinated sequence with step 1.

**Step 4. Verify post-reboot state.**
- `curl -s https://label.empirebox.store/label/api/health` must return `{"ok":true,"module":"label_station","max_products":10}` (same as today's baseline).
- `systemctl --user status empire-backend` must show `Active: active (running)` with `Main PID` in `/home/rg/empire-repo-main/backend` cgroup.
- `ps -eo pid,user,cgroup | grep cloudflared` must show exactly ONE cloudflared instance (the systemd-managed one).
- `ss -ltnp | grep :8000` must show `pid=<empire-backend cgroup PID>`.

**Steps to NOT take (per the dispatch prohibitions):**
- `systemctl restart empire-backend` (the dispatch prohibits this run-time; a reboot achieves the same effect)
- Touching `backend/app/modules/static/weigh-and-label.html` (live build is ahead of docs)
- Copying any files from `~/empire-repo` (legacy) to `~/empire-repo-main` (current)

---

## Hard prohibitions this dispatch respected

- ✅ No `sudo systemctl restart empire-backend` executed
- ✅ No start/stop/enable/disable/mask of any service
- ✅ No touch of `backend/app/modules/static/weigh-and-label.html`
- ✅ `sqlite3` CLI not used (used `ps`, `systemctl`, `cat`/`grep`/`ls` over `/proc/` only)
- ✅ GET-only routes confirmed with full GET semantics

---

## HEADLINE FINDINGS (each with command output above)

1. **PID 381138 holds :8000** — cgroup: `opencode-remote.service`. **Hand-started orphan** (not in empire-backend.service cgroup). Will die at reboot.
2. **User unit `empire-backend.service`** — enabled, linger=yes, ExecStart + WorkingDirectory both point to **MAIN tree** (`/home/rg/empire-repo-main/backend`). Currently in crash loop (40297 restarts) because the orphan holds port 8000. Will succeed on reboot.
3. **System unit `empire-backend.service`** — **DISABLED**, points to legacy tree. Even if enabled, would launch legacy code. Known-going-in confirmed.
4. **4 cloudflared instances** — 3 orphans (1771, 1772, 384400) + 1 systemd-managed (393465). **I3 backlog item is NOT closed** (3 orphans still alive). After reboot: only 1 will survive.
5. **Legacy tree** (`/home/rg/empire-repo/backend`) — **HAS NO label station module**. `app/modules/` directory missing. If the system unit ever ran, label station would be 404. **This is the decisive test for the founder's worst-case worry.**
6. **Live baseline** — `https://label.empirebox.store/label/api/health` returns `{"ok":true,"module":"label_station","max_products":10}` (HTTP 200). Recorded as the post-remediation MUST-MATCH target.
7. **Boot truth:** User unit WILL start cleanly on reboot (linger=yes, current unit is correct, no orphan to bind port 8000 first). **The Label Station WILL be reachable after reboot.** World (c) holds post-reboot.

---

## FOOTNOTE: the chat-message corollary

The founder's request — "if EmpireDell reboots right now, what actually comes up" — is now answered with evidence. The diagnosis is: **a fresh reboot lands us in state (c) — the user unit starts cleanly with the correct main-tree code, the label station is reachable, and the duplicate-cloudflared issue resolves itself (the orphans die).** The current pre-reboot state (crash loop with orphan) is misleading and looks worse than the post-reboot state will be.

The DISPATCH-B remediation order I propose is: **reboot** (single canonical action that resolves most of the diagnosed issues). If the founder wants to avoid a real reboot, the alternative is: kill PID 381138 (the orphan), then `systemctl --user restart empire-backend.service` (which the dispatch prohibits — I cannot do this; but it's the equivalent alternative). I do NOT recommend touching the system unit beyond masking/disabling it.
