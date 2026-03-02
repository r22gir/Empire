# Known Issues — EmpireBox

This document tracks confirmed bugs and workarounds for the EmpireBox platform.

---

## Hardware: AZW EQ / Beelink EQR5 Mini PC

### [CRITICAL] sensors-detect causes hard system lock

- **Affected hardware:** AZW EQ mini PC (AMD Ryzen 7 5825U, Family 19h)
- **Trigger:** Running `sudo sensors-detect`
- **Effect:** System freezes completely; requires hard power-off
- **Root cause:** `sensors-detect` probes legacy Super I/O ports (`sp5100_tco`,
  `w83627ehf`, `it87`, etc.) that are not present on this hardware; the probe
  causes the kernel to lock up
- **Fix applied:** `config/modprobe.d/empirebox-blacklist.conf` blacklists these modules
- **Workaround:** Use `sudo modprobe k10temp && sensors` for safe temperature reading
- **References:** `CHAT_SUMMARY_2026-02-22-lm-sensors-crashes.md`

### [HIGH] Docker OOM — too many containers exhaust RAM

- **Affected hardware:** All (32 GB RAM can still be exhausted by many large containers)
- **Trigger:** Starting all 13 product containers simultaneously without memory limits
- **Effect:** OOM killer terminates processes; system may become unstable
- **Fix applied:** `docker-compose.yml` now includes `deploy.resources.limits` for all services
- **Workaround:** Start containers gradually; monitor with `watch free -h`

### [LOW] Kernel 6.17.0 — potential driver regressions

- **Affected hardware:** AZW EQ mini PC
- **Details:** Kernel 6.17.0-14-generic is a very new release; driver bugs for
  AMD Ryzen hardware are possible
- **Status:** Under investigation; no confirmed kernel bug identified yet
- **Workaround:** If crashes persist after applying all fixes, consider pinning
  to an older LTS kernel (e.g., 6.8.x from Ubuntu 24.04 HWE)

---

## Software

### [INFO] `ebox bundle full` — not yet tested for stability

- Starting all 13 products at once has not been validated on 32 GB RAM
- Recommended: test with 3–4 services first, monitor memory, then scale up

---

## Resolved Issues

*(Move items here once confirmed fixed)*

---

## See Also

- `docs/BEELINK_STABILITY_GUIDE.md` — detailed stability guide and safe commands
- `docs/CRASH_RECOVERY_RUNBOOK.md` — step-by-step recovery after a crash
- `scripts/diagnostics/` — diagnostic data collection scripts
- `scripts/stability/` — health monitoring and emergency stop scripts
