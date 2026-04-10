# EmpireBox Resilience & Recovery Hardening Report

## Architecture Overview

### Recovery/Control Path

```
┌─────────────────────────────────────────────────────────────────────┐
│                     RECOVERY ACCESS POINTS                          │
├─────────────────────────────────────────────────────────────────────┤
│  1. API Endpoint (backend must be alive):                          │
│     GET  http://localhost:8000/api/v1/recovery-core/status         │
│     POST http://localhost:8000/api/v1/recovery-core/restart/<svc>   │
│     GET  http://localhost:8000/api/v1/recovery-core/ports           │
│     GET  http://localhost:8000/api/v1/recovery-core/connectivity   │
│     POST http://localhost:8000/api/v1/recovery-core/pairing/start   │
│                                                                     │
│  2. CLI Script (backend must be alive):                             │
│     /home/rg/bin/empire-recovery status                             │
│     /home/rg/bin/empire-recovery restart <service>                  │
│                                                                     │
│  3. SSH Access (OS must be alive):                                  │
│     ssh rg@hostname                                                 │
│     systemctl --user status empire-backend                           │
│     systemctl --user restart empire-backend                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Service Architecture

| Service | Port | systemd Service | Restart Policy | Enabled |
|---------|------|-----------------|----------------|---------|
| Backend API | 8000 | empire-backend.service | always | yes |
| Studio Portal | 3005 | empire-portal.service | always | yes |
| Cloudflare Tunnel | - | cloudflared-studio.service | always | yes |
| OpenClaw AI | 7878 | empire-openclaw.service | always | yes |
| Ollama LLM | 11434 | (manual) | N/A | N/A |
| Pairing Server | 8787 | (backend managed) | N/A | N/A |

### Routing (Preserved)
- `studio.empirebox.store` → `localhost:3005` (frontend)
- `api.empirebox.store` → `localhost:8000` (backend)

---

## Implementation Summary

### 1. Recovery/Control Router (`/api/v1/recovery-core/*`)

**New file:** `/home/rg/empire-repo/backend/app/routers/recovery_control.py`

Endpoints:
- `GET /recovery-core/status` - Full system status (services, ports, connectivity, processes)
- `POST /recovery-core/restart/{backend,frontend,cloudflared,openclaw}` - Restart specific service
- `POST /recovery-core/restart/all` - Restart all services in proper order
- `GET /recovery-core/ports` - Show port status for all key ports
- `GET /recovery-core/connectivity` - Check studio/api reachability
- `GET /recovery-core/processes` - Show running processes with uptime
- `GET/POST /recovery-core/pairing/{status,start,stop}` - Manage pairing server

### 2. CLI Tool

**New file:** `/home/rg/bin/empire-recovery`

Usage:
```bash
empire-recovery status              # Full status
empire-recovery restart backend     # Restart backend
empire-recovery ports              # Port status
empire-recovery pairing start      # Start pairing
```

### 3. OpenClaw Service

**New file:** `/home/rg/.config/systemd/user/empire-openclaw.service`

- Enabled for boot
- Restart=always policy
- Now active and running on port 7878

### 4. Service Verification

All four core services are:
- Enabled for boot start (`systemctl --user enable <service>`)
- Configured with `Restart=always`
- User lingering is enabled (services start without login)

---

## What Can Be Restarted/Recovered Remotely

### Via API or CLI (backend must be alive):
- ✅ Backend API (port 8000)
- ✅ Frontend/Studio Portal (port 3005)
- ✅ Cloudflared tunnel
- ✅ OpenClaw AI server (port 7878)
- ✅ Pairing server (port 8787)

### Via SSH (OS must be alive):
- ✅ All of the above via systemctl
- ✅ System-level diagnostics
- ✅ Log inspection (`journalctl --user -u empire-backend -f`)

---

## What Still Fails If Machine Freezes

### Complete Machine Freeze (Hardware/OS hang)
**Software cannot recover from this.** When the entire machine is frozen:
- No software running can execute
- No API calls possible
- No SSH possible
- **Only hardware-level recovery can help**

### Services That Are NOT Protected:
| Service | Limitation |
|---------|------------|
| Ollama | Not a systemd service, must be started manually |
| Pairing Server | Managed by backend, stops if backend stops |

---

## Hardware/Out-of-Band Requirements

### Critical (Needed for Frozen Computer Recovery)

1. **Smart Plug / Remote Power Switch**
   - **Purpose:** Power cycle the machine remotely when frozen
   - **Recommendation:** TP-Link Kasa Smart Plug (KP115) or similar
   - **Setup Required:** Enable "restore on power loss" in BIOS/UEFI
   - **Why:** Software cannot reboot a frozen machine; need physical power cycle

2. **BIOS/UEFI Configuration**
   - **Setting:** "Restore on AC Power Loss" → "Power On"
   - **Purpose:** Machine auto-boots when power is restored
   - **Location:** BIOS/UEFI → Power Management → AC Power Recovery
   - **Status:** ⚠️ NEEDS MANUAL VERIFICATION

3. **Out-of-Band (OOB) Management**
   - **Recommendation:** Dell iDRAC, Intel vPro, or hardware IPMI
   - **Purpose:** Remote KVM, virtual media, power control
   - **Why:** Strongest recovery option for remote management

### Recommended (Enhances Recovery)

4. **Dedicated Remote Access**
   - AnyDesk (already installed at `/home/rg/Downloads/anydesk-8.0.0-arm64/`)
   - Works when machine is alive but GUI is unresponsive
   - Requires machine to be at login screen

5. **Network Configuration**
   - Ensure router is configured to always assign same IP to EmpireBox
   - Configure port forwarding if accessing from outside local network

---

## Manual Setup Checklist

### BIOS/UEFI Settings
- [ ] **"Restore on AC Power Loss"** → Set to "Power On" or "Last State"
- [ ] Verify boot order includes primary hard drive
- [ ] Disable "Fast Boot" if experiencing wake issues

### Smart Plug Setup
- [ ] Purchase compatible smart plug (TP-Link Kasa, Wemo, etc.)
- [ ] Install vendor app and configure remote access
- [ ] Configure "auto-on" behavior on power restore
- [ ] Test: Unplug machine, verify it boots when power is restored

### Optional: IPMI/OOB Setup
- [ ] If Dell server/workstation: Enable iDRAC
- [ ] Configure IPMI over LAN
- [ ] Set up administrative credentials
- [ ] Test remote power operations

---

## Boot Recovery Verification

After this implementation, services will auto-start on reboot IF:
1. ✅ User services are enabled (verified)
2. ✅ `loginctl show-user rg | grep Linger` shows `Linger=yes` (verified)
3. ⚠️ BIOS "Restore on AC Power Loss" is set to "Power On" (**needs manual verification**)
4. ⚠️ Smart plug configured to restore power (**needs hardware setup**)

---

## Recovery Command Reference

### From Remote Machine (via API)
```bash
# Full status
curl http://localhost:8000/api/v1/recovery-core/status

# Restart backend
curl -X POST http://localhost:8000/api/v1/recovery-core/restart/backend

# Check ports
curl http://localhost:8000/api/v1/recovery-core/ports

# Start pairing
curl -X POST http://localhost:8000/api/v1/recovery-core/pairing/start
```

### From SSH (host-level)
```bash
# Check all services
systemctl --user status empire-backend empire-portal cloudflared-studio empire-openclaw

# Restart a service
systemctl --user restart empire-backend

# View logs
journalctl --user -u empire-backend -f

# Full recovery status
empire-recovery status
```

### From Browser
```
http://localhost:8000/api/v1/recovery-core/status
http://studio.empirebox.store (if cloudflared is running)
http://api.empirebox.store (if cloudflared is running)
```

---

## Files Changed

### New Files
1. `/home/rg/empire-repo/backend/app/routers/recovery_control.py` - Recovery API router
2. `/home/rg/.config/systemd/user/empire-openclaw.service` - OpenClaw systemd service
3. `/home/rg/bin/empire-recovery` - Recovery CLI script

### Modified Files
1. `/home/rg/empire-repo/backend/app/main.py` - Added recovery_control router loading

### Unchanged (Preserved)
- studio.empirebox.store → 3005 routing
- api.empirebox.store → 8000 routing
- Empire Workroom, Woodcraft/CraftForge, ApostApp, studio.empirebox.store frontend

---

## Highest Remaining Risk

**Risk:** Complete machine freeze with no software-based recovery possible

**Likelihood:** Medium (depends on hardware reliability, OS stability, power quality)

**Mitigation:** Requires hardware intervention (smart plug or OOB management)

**Next Step:** Purchase and configure a smart plug, verify BIOS settings

---

## Verification Commands

```bash
# Verify all services are enabled
systemctl --user list-unit-files --type=service | grep empire

# Verify user lingering
loginctl show-user rg | grep Linger

# Test recovery API
curl http://localhost:8000/api/v1/recovery-core/status | python3 -m json.tool

# Test CLI
empire-recovery status

# Verify openclaw is running
ss -tlnp | grep 7878

# Verify pairing is running
ss -tlnp | grep 8787
```
