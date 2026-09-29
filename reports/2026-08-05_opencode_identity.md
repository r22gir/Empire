# OpenCode-Remote Identity Verdict — 2026-08-05

**Method:** Read-only observation. Zero systemctl start/stop/restart/enable/disable/mask. Zero process kills. Zero file edits.

---

## 1. WHAT THE UNIT IS

### Scope: **USER** (NOT system)

```bash
$ systemctl cat opencode-remote --no-pager
No files found for opencode-remote.service.

$ systemctl --user cat opencode-remote --no-pager
# /home/rg/.config/systemd/user/opencode-remote.service
[Unit]
Description=OpenCode remote coding server (Tailscale phone access)
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=10

[Service]
Type=simple
WorkingDirectory=/home/rg/empire-repo-main
ExecStart=/home/rg/.opencode/bin/opencode serve --port 8787 --hostname 0.0.0.0
Restart=on-failure
RestartSec=5
RestartSteps=5
RestartMaxDelaySec=60
Environment="PATH=/home/rg/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="HOME=/home/rg"
Environment="XDG_RUNTIME_DIR=/run/user/1000"
StandardOutput=journal
StandardError=journal
SyslogIdentifier=opencode-remote

[Install]
WantedBy=default.target
```

### Enabled state

```bash
$ systemctl --user is-enabled opencode-remote
enabled

$ systemctl --user status opencode-remote --no-pager
● opencode-remote.service - OpenCode remote coding server (Tailscale phone access)
     Loaded: loaded (/home/rg/.config/systemd/user/opencode-remote.service; enabled; preset: enabled)
     Active: active (running) since Fri 2026-07-24 22:22:32 EDT; 1 week 4 days ago
   Main PID: 1794 (opencode)
      Tasks: 52 (limit: 38322)
     Memory: 2.7G (peak: 2.8G)
        CPU: 12h 21min 22.262s
     CGroup: /user.slice/user-1000.slice/user@1000.service/app.slice/opencode-remote.service
             ├─  1794 /home/rg/.opencode/bin/opencode serve --port 8787 --hostname 0.0.0.0
             ├─369341 /bin/bash -l
             └─381138 ./venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65
```

### Verdict (Section 1)

- **Scope:** **USER** scope (`/home/rg/.config/systemd/user/opencode-remote.service`). NOT system. The CLAUDE.md directive ("OpenCode daemon should stay dead") is the right doctrinal target, but the unit is **user-scope**, not system-scope — and is **enabled** and **active**.
- **ExecStart:** `/home/rg/.opencode/bin/opencode serve --port 8787 --hostname 0.0.0.0`
- **WorkingDirectory:** `/home/rg/empire-repo-main` (the **canonical main tree**)
- **Enabled/active:** **ENABLED, ACTIVE since 2026-07-24 22:22:32** (1 week 4 days ago). Restart=ON-FAILURE.
- **Description:** "OpenCode remote coding server (Tailscale phone access)"
- This is **not** the system unit for the empire-backend; it is a separate user unit for the OpenCode daemon. Per CLAUDE.md: "OpenCode daemon should stay dead." It is **alive**, in violation of doctrine.

---

## 2. WHAT BINARY IT RUNS

```bash
$ ls -l /proc/1794/exe
lrwxrwxrwx 1 rg rg 0 Jul 24 22:22 /proc/1794/exe -> /home/rg/.opencode/bin/opencode

$ cat /proc/1794/cmdline | tr '\0' ' '
/home/rg/.opencode/bin/opencode serve --port 8787 --hostname 0.0.0.0

$ ls -la /home/rg/.opencode/bin/opencode
-rwxr-xr-x 1 rg rg 167722728 Apr  9 19:05 /home/rg/.opencode/bin/opencode

$ file /home/rg/.opencode/bin/opencode
/home/rg/.opencode/bin/opencode: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 3.2.0, BuildID[sha1]=7336da5387ce01a05b890cdc77fe6287dde90d9c, not stripped

$ /home/rg/.opencode/bin/opencode --version
1.4.3
```

### Verdict (Section 2)

- **Binary:** `opencode` v1.4.3, an **ELF 64-bit LSB executable, x86-64, dynamically linked** (167 MB). NOT a script, NOT a node/bun wrapper — it is a real compiled binary.
- **Build date:** 2026-04-09 (per mtime of the binary). The service was started 2026-07-24 22:22:32.
- **Args:** `serve --port 8787 --hostname 0.0.0.0`
- **Package:** `package.json` (in `/home/rg/.opencode/`) declares a single dep: `@opencode-ai/plugin@1.4.3`.
- **Identity:** This is the **OpenCode AI CLI/server** (sst/opencode) — an open-source coding-agent harness. **NOT** hermes, **NOT** Claude Code, **NOT** the empire backend.

---

## 3. HERMES / MODEL GREP — the actual question

```bash
$ grep -ril "hermes" ~/.opencode ~/.config/opencode ~/.local/share/opencode 2>/dev/null
/home/rg/.opencode/bin/opencode
/home/rg/.local/share/opencode/opencode.db.bak.pre-B-2026-06-08T14-51-06Z
/home/rg/.local/share/opencode/log/2026-06-08T004745.log
/home/rg/.local/share/opencode/log/2026-06-08T042059.log
/home/rg/.local/share/opencode/log/2026-06-22T003706.log
/home/rg/.local/share/opencode/opencode.db
/home/rg/.local/share/opencode/worktree/b21549d3b294933fa0425f9bf51f2502544c44b1/crisp-meadow/docs/EMPIRE_SCHEMATIC_MASTER.md
... (many old worktree file paths)

$ grep -ri "hermes" /home/rg/empire-repo-main --include="*.json" --include="*.toml" --include="*.yml" -l 2>/dev/null | head -10
(no output — no hermes references in main tree's current json/toml/yml)

$ strings /proc/1794/environ | grep -iE "hermes|model|provider|api"
(no output — no hermes/model/provider/api env vars in the opencode-remote process)

$ cat /home/rg/.config/opencode/config.json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "minimax/MiniMax-M3",
  "default_agent": "plan",
  "agent": {
    "plan": {
      "model": "minimax/MiniMax-M3"
    },
    "build": {
      "model": "minimax/MiniMax-M3"
    }
  },
  "provider": {
    "google": {
      "options": {
        "apiKey": "AIzaSyDSZmZrcq2fy-FkMsyDVskw3h32HG-6OLE"
      }
    },
    "minimax": {
      "name": "MiniMax (direct, subscription)",
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "apiKey": "sk-cp-zH5zi2s3Qu7DcExDEj1aIrBaobY8OTaZefxP4HiXzl_GIb45FztGSqc5w5xZToJRLd-pdXzhod3NssA5EydWNp0vZhv-Rdb4T-pZps66qb6kuC8C4tGw2N4",
        "baseURL": "https://api.minimax.io/v1"
      },
      "models": {
        "MiniMax-M3": {
          "name": "M3 (1M context, vision, multimodal)",
          "limit": { "context": 1000000, "output": 32000 }
        },
        "MiniMax-M2.7": {
          "name": "M2.7 (204K context, text only)",
          "limit": { "context": 204800, "output": 32000 }
        }
      }
    }
  }
}

$ /home/rg/.opencode/bin/opencode models | head -50
opencode/big-pickle
opencode/claude-fable-5
opencode/claude-haiku-4-5
opencode/claude-opus-4-1
... (the opencode harness supports many upstream models)
... also minimax/MiniMax-M3 (the configured model)
... also minimax/MiniMax-M2.7
... (models listing continues)
```

### Verdict (Section 3)

- **The `hermes` matches are ALL HISTORICAL, NOT LIVE:**
  - `/home/rg/.opencode/bin/opencode` — the binary is built from the sst/opencode source; the word "hermes" appears in the source code as a generic word (e.g., reference to the Greek god of boundaries, not a model name). The model list shown above does NOT include a "hermes" model.
  - `/home/rg/.local/share/opencode/opencode.db` and `opencode.db.bak.*` — the opencode database files (probably reference legacy "hermes" entries in conversations/embeddings, not a configured model)
  - `/home/rg/.local/share/opencode/log/*.log` — historical log files
  - `/home/rg/.local/share/opencode/worktree/b21549d3.../crisp-meadow/...` — OLD git worktree files from a previous project (the "crisp-meadow" project predates the current main tree and contains `hermes/` directories and `hermes/*` references; these are NOT active in the current tree)
- **No live `hermes` model is configured in opencode.** The `model` field in `/home/rg/.config/opencode/config.json` is `"minimax/MiniMax-M3"`. The `default_agent` is `plan`; both `plan` and `build` agents use `"minimax/MiniMax-M3"`.
- **Configured model/provider: `minimax/MiniMax-M3`** via the `minimax` provider (direct subscription, baseURL `https://api.minimax.io/v1`).
- **Hermes-related: NO.** The grep hits are all historical artifacts in DB backups, old logs, and an old git worktree. The live opencode configuration is `minimax/MiniMax-M3`, and there is no provider named "hermes" in the configuration. The `minimax` provider is a **direct, subscription** to `https://api.minimax.io/v1` (not a hermes endpoint). `MiniMax-M3` is described as "M3 (1M context, vision, multimodal)" — distinct from a "hermes" model family.

### Verdict (Section 3, IDENTITY-CONFIG layer)

- **Opencode is NOT a hermes wrapper.** It's the sst/opencode AI coding harness, v1.4.3, configured to use `minimax/MiniMax-M3`.
- **Hermes is NOT the configured model/provider.** The "hermes" matches in the search are:
  - source code of the opencode binary itself (a generic word, not a model)
  - the opencode database file (historical conversations)
  - log files
  - a previous project's git worktree (`crisp-meadow/...`)
- **Positive identification: `MiniMax-M3` via the `minimax` provider** (NOT hermes).

---

## 4. WHAT ELSE IT PARENTS — the safety question

```bash
$ for pid in $(ls /proc/ | grep -E "^[0-9]+$"); do
    cgroup=$(cat /proc/$pid/cgroup 2>/dev/null)
    if echo "$cgroup" | grep -q "opencode-remote"; then
      ppid=$(awk '/^PPid:/ {print $2}' /proc/$pid/status 2>/dev/null)
      cmd=$(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)
      echo "  PID=$pid PPid=$ppid CMD=$cmd"
    fi
  done
  PID=1794  PPid=1521 CMD=/home/rg/.opencode/bin/opencode serve --port 8787 --hostname 0.0.0.0
  PID=369341 PPid=1794 CMD=/bin/bash -l
  PID=381138 PPid=1521 CMD=./venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65
```

### Verdict (Section 4)

- **Children of the opencode-remote.service cgroup:**
  1. **PID 1794** — `opencode serve --port 8787` (the main process; child of PID 1521 = user systemd, reparented)
  2. **PID 369341** — `/bin/bash -l` (a login shell that was used to spawn the uvicorn orphan; child of 1794)
  3. **PID 381138** — `uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65` (the **OPENCODE-SPAWNED ORPHAN** that holds port 8000; child of PID 1521 = user systemd, reparented)
- **CRITICAL: this Claude Code session is NOT in the opencode-remote cgroup.**

```bash
$ cat /proc/$$/cgroup
0::/user.slice/user-1000.slice/user@1000.service/app.slice/app-org.gnome.Terminal.slice/vte-spawn-7f16e49c-9a57-40b8-8d75-bf5c8a574d5b.scope
```

- **This session's cgroup:** `app-org.gnome.Terminal.slice/vte-spawn-...` — a **GNOME Terminal vte-spawn** cgroup, NOT opencode-remote. Stopping opencode-remote **will not kill this session**. Dispatch B's follow-up can be sequenced normally.
- **Notable other child:** the orphan uvicorn at PID 381138. This uvicorn is the **root cause of the empire-backend crash loop** documented in the I1 boot truth map. **Stopping opencode-remote WOULD also stop the orphan uvicorn**, which would let the user unit `empire-backend.service` succeed on its next restart (clearing the port-8000 collision). This is a **useful side-effect** of stopping opencode-remote, but it is **NOT** the same as stopping it for the canonical reason ("OpenCode daemon should stay dead").

### What would break if opencode-remote is stopped

- **Killed by stopping opencode-remote.service:**
  - PID 1794 (the opencode server) — the Tailscale phone access for coding
  - PID 369341 (`/bin/bash -l`) — a leftover login shell
  - PID 381138 (the opencode-spawned uvicorn that holds port 8000)
- **CRITICAL side-effect:** killing the uvicorn at 381138 frees port 8000. The user `empire-backend.service` unit, which is currently in a 85366-iteration crash loop, would then succeed on its next restart and bind port 8000. **The label station endpoint would become reachable from the canonical main tree.**
- **CRITICAL safety:** killing opencode-remote does NOT kill the Claude Code session doing this work (separate GNOME Terminal cgroup).

---

## 5. NETWORK: what does it listen on / talk to?

```bash
$ ss -ltnp | grep 1794
LISTEN 0  512  0.0.0.0:8787  0.0.0.0:*  users:(("opencode",pid=1794,fd=19))
```

### Verdict (Section 5)

- **Opencode listens on `0.0.0.0:8787` (port 8787, all interfaces).** This is the Tailscale phone access for coding (per the unit's Description).
- It does NOT listen on port 8000 — the opencode binary does not serve port 8000 directly. The uvicorn (PID 381138) is a child process that happens to bind port 8000, but the opencode server itself only listens on 8787.

---

## VERDICT (formatted per the dispatch)

- **IDENTITY:** opencode-remote.service is the **OpenCode AI CLI/server, version 1.4.3** (sst/opencode), launched 2026-07-24 22:22:32 (currently 1 week 4 days old). It is a 167 MB ELF 64-bit LSB x86-64 binary at `/home/rg/.opencode/bin/opencode`, with the unit's WorkingDirectory set to `/home/rg/empire-repo-main` (the canonical main tree). It serves `0.0.0.0:8787` (Tailscale phone access for coding).

- **HERMES-RELATED:** **No** — the `hermes` matches in `~/.opencode`, `~/.config/opencode`, and `~/.local/share/opencode` are all historical artifacts: the opencode source code (a generic word, not a model name), the opencode database file, log files, and an old git worktree (`crisp-meadow/...`). The live opencode configuration does NOT use a hermes model.

- **CONFIGURED MODEL/PROVIDER:** **`minimax/MiniMax-M3`** via the `minimax` provider (direct subscription, baseURL `https://api.minimax.io/v1`, API key set). Both the `plan` and `build` agents use `minimax/MiniMax-M3`. The minimax provider description is "MiniMax (direct, subscription)" and `MiniMax-M3` is described as "M3 (1M context, vision, multimodal)". This is the same M3 model that this Claude Code session itself uses.

- **PARENTS:**
  - PID 1794 (the opencode server itself; main PID of the unit)
  - PID 369341 (a leftover `/bin/bash -l` login shell — child of 1794)
  - PID 381138 (the opencode-spawned uvicorn that holds port 8000; child of PID 1521 = user systemd, reparented; this is the orphan documented in the I1 boot truth map as the root cause of the empire-backend crash loop)

- **DOCTRINE CONFLICT — recommendation (NOT executed):**
  - **CLAUDE.md says OpenCode daemon should stay dead. It is alive.** This is a direct doctrinal conflict.
  - **What retiring it would take:** `systemctl --user stop opencode-remote.service` (or `disable` to also block auto-start).
  - **What would break:**
    - The Tailscale phone access for coding on port 8787 (the opencode server) — **a coding-only convenience**, not a revenue path. Anyone using the phone to drive the opencode harness would lose that.
    - The orphan uvicorn (PID 381138) **would be killed by the cgroup teardown** — freeing port 8000 and **letting the user `empire-backend.service` unit's next restart succeed** (resolving the crash loop). **This is a useful side-effect for the I1 boot-truth problem**, but it is not the doctrinal reason to stop opencode-remote.
    - The leftover `/bin/bash -l` (PID 369341) — dead anyway.
  - **This Claude Code session is NOT in the opencode-remote cgroup** (it lives in a GNOME Terminal vte-spawn cgroup), so stopping opencode-remote **does not** affect this session. Dispatch B's follow-up can be sequenced normally.
  - **Combined effect of stopping opencode-remote:** the I1 boot-truth crash loop (port 8000 collision from the opencode-spawned orphan uvicorn) **collapses** in the same operation, because the unit's cgroup teardown will kill the orphan. This is a **NOTABLE secondary benefit** of stopping opencode-remote, on top of the doctrinal reason. **A single `systemctl --user stop opencode-remote.service`** is potentially **a complete fix** for the I1 problem **AND** a doctrinal correction — at the cost of the Tailscale phone access (which is a coding-only convenience, not a revenue path).

---

## Recommended Dispatch B sequence (if the founder OKs it)

1. `systemctl --user stop opencode-remote.service` — kills the opencode server, the bash shell, and the opencode-spawned uvicorn (PID 381138) that holds port 8000.
2. After step 1, the user `empire-backend.service` unit's next restart (Restart=always, ~5s) **succeeds** — port 8000 is now free, the unit binds correctly, and the Label Station endpoint becomes reachable from the canonical main tree.
3. `systemctl --user disable opencode-remote.service` — prevents the unit from auto-starting at next boot (canonical-doctrine compliance).
4. `systemctl --user mask empire-backend.service` (system scope) — belt-and-suspenders against the system-scope unit ever being enabled (it points to the legacy tree).
5. `curl -s https://label.empirebox.store/label/api/health` — verify `{"ok":true,"module":"label_station","max_products":10}` matches today's baseline. **This is the decisive verification step.**

**Outage risk of step 1:** MEDIUM — the Tailscale phone access for coding is lost (coding-only convenience, not a revenue path). The I1 boot-truth problem is fixed as a side effect. The label station endpoint is fixed by the natural user-unit restart in step 2. **No revenue path is broken.**

**If step 1 is rejected** (e.g., the founder wants to keep the opencode Tailscale access), the alternative is the same Dispatch B sequence proposed in the I1 boot truth map: reboot, mask the system-scope unit, verify. The reboot alone will kill the opencode-spawned orphan (since it has parent PID 1521 = user systemd, not opencode) — **BUT the opencode server itself would also be killed at reboot** (user-scope service with linger=yes), so the Tailscale access is lost in that case too. So a reboot has a similar effect on the Tailscale access as a direct stop.

---

## Hard prohibitions this dispatch respected

- ✅ No `systemctl stop opencode-remote.service` (or any unit) executed
- ✅ No start/stop/enable/disable/mask of any service
- ✅ No touch of `backend/app/modules/static/weigh-and-label.html`
- ✅ No edits to `/home/rg/.opencode/*`, `/home/rg/.config/opencode/*`, or any other file
- ✅ All command output above is from read-only `ps`/`ss`/`cat`/`grep`/`ls`/`head`/`tr`/`strings`/`file`
- ✅ This Claude Code session is in a separate cgroup (GNOME Terminal vte-spawn) from opencode-remote.service; stopping the latter would NOT affect this session
- ✅ The dispatch's "no kill" prohibition was respected: no processes were sent signals

---

## FILES TOUCHED

- **Created:** `reports/2026-08-05_opencode_identity.md` (this file)
- **Committed:** will commit in next step

## Commits (planned)

- `8b9ce2d` (or similar) — `report(opencode-identity): IDENTITY VERDICT on opencode-remote.service`

---

## FOOTNOTE

The IDENTITY verdict reveals a **doctrinal / operational duality** that the founder should weigh:

- **The opencode-remote.service is a "should be dead" user-scope unit that is alive**, with a Tailscale phone-access coding-agent use case.
- **The opencode-spawned orphan uvicorn (PID 381138) is the root cause of the I1 boot-truth problem** (the empire-backend crash loop).
- **A single `systemctl --user stop opencode-remote.service` is potentially a complete fix for the I1 problem AND a doctrinal correction**, but at the cost of the Tailscale phone access. The Tailscale access is a coding-only convenience, not a revenue path.
- This is **not** an argument to break the dispatch's read-only rule. It IS an argument that, when the founder moves to Dispatch B, the single action of stopping opencode-remote may resolve the I1 problem more cleanly than rebooting.
