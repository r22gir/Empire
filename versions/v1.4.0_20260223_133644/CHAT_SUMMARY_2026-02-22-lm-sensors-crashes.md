# Chat Summary: lm-sensors Installation & System Stability Issues

**Date:** 2026-02-22  
**System:** AZW EQ mini PC (EmpireBox)  
**User:** r22gir (rg@EmpireBox)

---

## System Specifications

| Component | Details |
|-----------|---------|
| Device | AZW EQ mini PC |
| CPU | AMD Ryzen 7 5825U with Radeon Graphics (Zen 3, Family 19h) |
| Kernel | 6.17.0-14-generic x86_64 |
| OS | Ubuntu Noble |

---

## Session Timeline

### 1. Initial Problem
User ran `sensors` command and got "command not found" - needed to install lm-sensors.

### 2. Installed lm-sensors
```bash
sudo apt install lm-sensors
```
✅ Completed successfully.

### 3. Ran sensors-detect — CAUSED SYSTEM CRASHES
```bash
sudo sensors-detect
```
- Scanned for embedded sensors — no matches (expected; CPU is Family 19h, not detected by older modules)
- Proceeded to Super I/O sensor scanning
- **⚠️ SYSTEM CRASHED TWICE**
- Required hard power-off (physically unplugging) both times
- **RECOMMENDATION: Do NOT run `sensors-detect` on this hardware**

### 4. Workaround — Manually Loaded k10temp
```bash
sudo modprobe k10temp
sensors
```
✅ Worked without crashing.

### 5. Current Sensor Readings (Healthy)
```
iwlwifi_1-virtual-0
Adapter: Virtual device
temp1:        +46.0°C  

nvme-pci-0300
Adapter: PCI adapter
Composite:    +34.9°C  (low  =  -0.1°C, high = +82.8°C)
                       (crit = +84.8°C)
Sensor 1:     +34.9°C  (low  = -273.1°C, high = +65261.8°C)

amdgpu-pci-0500
Adapter: PCI adapter
vddgfx:        1.07 V  
vddnb:       756.00 mV 
edge:         +41.0°C  
PPT:           9.00 W  

k10temp-pci-00c3
Adapter: PCI adapter
Tctl:         +43.1°C  
```

| Sensor | Reading | Status |
|--------|---------|--------|
| CPU (Tctl) | ~43°C | ✅ Normal |
| GPU (edge) | ~41°C | ✅ Normal |
| NVMe SSD | ~35°C | ✅ Normal |
| WiFi (iwlwifi) | ~46°C | ✅ Normal |

### 6. Made k10temp Persistent
```bash
echo "k10temp" | sudo tee -a /etc/modules
```
✅ Module will auto-load on boot.

---

## Outstanding Issue: System Instability

**User reports:** System has been crashing, possibly unrelated to sensors-detect. Suspects too many Docker containers.

### Not Yet Investigated
The following commands were suggested but not yet run:
```bash
docker ps -a          # List all containers
htop                  # Interactive resource monitor
top -o %MEM           # Process list sorted by memory
free -h               # Memory usage summary
journalctl -b -1 -p err   # Errors from previous boot
```

### Unknown Information
- Total RAM installed
- Number of containers running
- Container resource usage
- Logs from previous crashes

---

## Key Findings

1. **sensors-detect is dangerous on this hardware** — causes hard locks requiring power cycling
2. **Temperatures are healthy** — crashes are NOT heat-related
3. **Manual module loading works** — `sudo modprobe k10temp` is safe
4. **Kernel 6.17.0 is very new** — potential for driver bugs
5. **Suspected cause of crashes:** Resource exhaustion from too many Docker containers (unconfirmed)

---

## Useful Commands Reference

```bash
# Check CPU temp quickly
sensors | grep Tctl

# Continuous monitoring (updates every 2 seconds)
watch sensors

# Check memory
free -h

# Check containers
docker ps -a
docker stats

# Check logs from last crash
journalctl -b -1 -p err
```

---

## Next Steps for Follow-up Chat

1. Run `docker ps -a` and `docker stats` to assess container load
2. Run `free -h` to check RAM capacity and usage
3. Run `journalctl -b -1 -p err` to review crash logs
4. Identify and potentially reduce container count
5. Consider if kernel 6.17.0 has known issues with this hardware

---

## Tags
`lm-sensors` `ubuntu` `amd-ryzen` `azw-eq` `docker` `system-crash` `k10temp` `mini-pc`