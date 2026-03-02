# Quick Start — EmpireBox Founders Unit

## TL;DR

```bash
# 1. Create USB (on your laptop)
# Install Ventoy on USB → copy Ubuntu 24.04 ISO + this folder

# 2. Boot Beelink EQR5 from USB (F7 boot menu)
# Ubuntu installs automatically — wait ~15 min

# 3. First boot runs install script automatically — wait ~30 min

# 4. Access your control center
open http://empirebox.local
```

## After Install — Key Commands

```bash
# SSH into the box
ssh empirebox@empirebox.local

# List all products
ebox list

# Start a bundle
ebox bundle full          # All 13 products
ebox bundle reseller      # MarketForge + ShipForge + RelistApp + ForgeCRM
ebox bundle contractor    # ContractorForge + LuxeForge + LeadForge + ForgeCRM
ebox bundle support       # SupportForge + ForgeCRM + EmpireAssist

# Start/stop individual products
ebox start marketforge
ebox stop marketforge
ebox logs marketforge

# Check what's running
ebox status
```

## Key URLs

| What | Where |
|------|-------|
| Dashboard | http://empirebox.local |
| OpenClaw AI | http://empirebox.local:7878 |
| Control Center | http://empirebox.local:8001 |
| Portainer | http://empirebox.local:9000 |
| Ollama | http://empirebox.local:11434 |

## Credentials

```bash
cat /opt/empirebox/.env
```
