# Beelink EQR5 / AZW EQ Stability Guide

## Hardware Specifications

| Component | Details |
|-----------|---------|
| Device | AZW EQ mini PC (Beelink EQR5) |
| CPU | AMD Ryzen 7 5825U with Radeon Graphics (Zen 3, Family 19h) |
| RAM | 32 GB DDR4 |
| Storage | 500 GB NVMe SSD |
| Kernel | 6.17.0-14-generic x86_64 |
| OS | Ubuntu Noble 24.04 |

---

## ⚠️ Known Issues

### 1. `sensors-detect` Causes Hard System Locks

**Severity:** CRITICAL  
**Status:** AVOID — do not run this command

Running `sudo sensors-detect` probes legacy Super I/O ports and the `sp5100_tco`
watchdog timer. On this hardware (Ryzen 5825U), these probes cause the system to
freeze completely, requiring a hard power-off.

**Safe alternative:**
```bash
sudo modprobe k10temp
sensors
```

The `k10temp` module is the correct AMD Ryzen temperature sensor and works without
causing any instability.

### 2. Docker Resource Exhaustion (Suspected OOM)

**Severity:** HIGH  
**Status:** Mitigated via `docker-compose.yml` resource limits

Running many Docker containers without memory limits can exhaust the 32 GB RAM,
triggering the OOM killer or causing system instability.

**Fix:** All services in `docker-compose.yml` now have `deploy.resources.limits`
set to prevent any single container from consuming unbounded memory.

### 3. Kernel 6.17.0 — Very New

**Severity:** LOW  
**Status:** Monitor for driver regressions

Kernel 6.17.0 is new and may have driver regressions for AMD Family 19h hardware.
If crashes continue after applying all fixes, consider pinning to a known-stable
kernel version.

---

## ✅ Safe Commands

```bash
# Check CPU temperature (safe)
sudo modprobe k10temp
sensors | grep Tctl

# Continuous temperature monitoring
watch sensors

# Memory usage
free -h

# Docker containers
docker ps -a
docker stats --no-stream

# Crash logs from previous boot
journalctl -b -1 -p err --no-pager
```

## ❌ Dangerous Commands — DO NOT RUN

```bash
# DO NOT RUN — causes hard lock requiring power-off
sudo sensors-detect
```

---

## Applying Stability Fixes

Run once as root to install all stability fixes:

```bash
sudo bash scripts/setup/apply_stability_fixes.sh
sudo update-initramfs -u
sudo reboot
```

This script:
1. Installs `/etc/modprobe.d/empirebox-blacklist.conf` — prevents dangerous module probing
2. Installs `/etc/modules-load.d/empirebox-sensors.conf` — auto-loads `k10temp` on boot
3. Creates `/var/log/empirebox/` log directory
4. Installs health-check cron job (runs every 5 minutes)

---

## Diagnostic Data Collection

To collect a full diagnostic snapshot for crash investigation:

```bash
bash scripts/diagnostics/collect_system_info.sh
cat /tmp/empirebox_diagnostics.txt
```

To package and share:

```bash
bash scripts/diagnostics/upload_diagnostics.sh
```

---

## Health Monitoring

A cron-based health check runs every 5 minutes at `/opt/empirebox/scripts/health_check.sh`.

- Logs to `/var/log/empirebox/health.log`
- Warns if memory exceeds 70%
- Restarts Docker daemon if memory exceeds 80%
- Stops all containers if memory exceeds 90% (emergency)

To view the health log:
```bash
tail -f /var/log/empirebox/health.log
```

---

## Emergency Recovery

If the system becomes unresponsive due to memory pressure:

```bash
# Stop non-essential containers (keeps postgres and redis)
sudo bash scripts/stability/emergency_stop.sh

# Stop ALL containers
sudo bash scripts/stability/emergency_stop.sh --all
```

See also: `docs/CRASH_RECOVERY_RUNBOOK.md`

---

## Normal Operating Temperatures

| Sensor | Normal Range | Alarm Threshold |
|--------|-------------|-----------------|
| CPU (Tctl / k10temp) | 35–55°C | > 85°C |
| GPU (amdgpu edge) | 35–55°C | > 85°C |
| NVMe SSD (Composite) | 30–50°C | > 82°C |
| WiFi (iwlwifi) | 40–55°C | > 70°C |
