# EmpireBox Crash Recovery Runbook

## When to Use This Runbook

Use this guide after the EmpireBox (AZW EQ / Beelink EQR5) experiences:
- A complete system freeze requiring hard power-off
- Docker services becoming unresponsive
- Out-of-memory (OOM) events
- Any unplanned restart

---

## Step 1: Hard Power-Off (Last Resort)

If the system is completely unresponsive (no keyboard, no mouse):

1. **Hold the power button** for 5+ seconds until the unit powers off
2. **Wait 10 seconds**
3. **Press power button** to restart

> ⚠️ Hard power-off risks filesystem corruption. After restart, run `sudo fsck` if prompted.

---

## Step 2: Collect Logs Immediately After Reboot

Run these commands **before starting any services** to capture the crash context:

```bash
# Errors from the previous (crashed) boot session
journalctl -b -1 -p err --no-pager > /tmp/crash_errors.txt

# Full kernel log from previous boot
journalctl -b -1 --no-pager > /tmp/crash_full.txt

# OOM events
dmesg | grep -i "oom\|out of memory\|killed process" > /tmp/oom_events.txt

# Run the full diagnostic collector
bash /path/to/Empire/scripts/diagnostics/collect_system_info.sh
```

---

## Step 3: Diagnose the Cause

### Check for OOM Kill

```bash
grep -i "killed process\|out of memory" /tmp/crash_errors.txt
```

If OOM is confirmed:
- Note which process was killed
- Review Docker container memory usage before restarting
- Consider reducing the number of running containers

### Check for Kernel Panics

```bash
grep -i "panic\|oops\|bug:" /tmp/crash_errors.txt
```

If a kernel panic is found, record the module name and report it as a bug.

### Check for Hardware Errors

```bash
grep -i "hardware error\|mce\|uncorrected" /tmp/crash_errors.txt
```

Hardware errors may indicate failing RAM or NVMe. Run a memtest if suspected.

---

## Step 4: Restart Services Safely

**Do not start all services at once.** Bring them up gradually:

```bash
cd /path/to/Empire

# Start data services first
docker compose up -d postgres redis

# Wait for them to be healthy
docker compose ps

# Then start backend
docker compose up -d backend

# Then frontend
docker compose up -d frontend
```

Monitor memory as each service starts:
```bash
watch free -h
```

---

## Step 5: Verify Stability

```bash
# Confirm all containers are running
docker ps

# Watch memory over time
watch free -h

# Check health log
tail -f /var/log/empirebox/health.log
```

If memory climbs above 80% within a few minutes, stop non-essential containers:

```bash
sudo bash scripts/stability/emergency_stop.sh
```

---

## Step 6: Share Diagnostics (If Issue Persists)

```bash
bash scripts/diagnostics/upload_diagnostics.sh
```

Open a GitHub issue at https://github.com/r22gir/Empire/issues and attach the
generated archive.

---

## Common Failure Modes & Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Hard freeze during `sensors-detect` | Dangerous module probe | Never run `sensors-detect`; use `k10temp` |
| System freeze after starting many containers | OOM | Apply memory limits in docker-compose.yml |
| Containers stop responding | Docker daemon crash | `sudo systemctl restart docker` |
| High memory, system sluggish | Too many containers | Run `emergency_stop.sh` |
| Filesystem errors on boot | Hard power-off | `sudo fsck /dev/nvme0n1pX` (replace with correct partition) |

---

## Do Not Run After a Crash

```bash
# This will crash the system again
sudo sensors-detect
```

---

## Contact / Escalation

- GitHub Issues: https://github.com/r22gir/Empire/issues
- See also: `docs/BEELINK_STABILITY_GUIDE.md`, `docs/KNOWN_ISSUES.md`
