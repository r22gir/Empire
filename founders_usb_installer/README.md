# EmpireBox Founders Unit - USB Installer

> ⚠️ **INTERNAL USE ONLY — MASTER CONTROL DEVICE**

This USB installer sets up the EmpireBox Founders Unit on a **Beelink EQR5** (Ryzen 7 5825U, 32GB RAM, 500GB NVMe). This is the MASTER CONTROL device — not for sale.

## What Gets Installed

| Component | Description |
|-----------|-------------|
| Ubuntu Server 24.04 | Base OS (unattended install) |
| Docker + Compose | Container runtime |
| Ollama | Local AI (llama3.1:8b, codellama:7b, nomic-embed-text) |
| OpenClaw | AI Agent with multi-model support (founders mode) |
| EmpireBox Core | PostgreSQL, Redis, API Gateway |
| Control Center | Fleet management for customer units |
| All 13 Products | On-demand startup via `ebox` CLI |
| Founders Dashboard | Web UI at port 80 |

## Hardware Requirements

- **Device**: Beelink EQR5
- **CPU**: AMD Ryzen 7 5825U
- **RAM**: 32GB DDR4
- **Storage**: 500GB NVMe SSD
- **USB**: 16GB+ USB drive

## USB Creation (Ventoy)

1. Download [Ventoy](https://www.ventoy.net) and install it to your USB drive
2. Download Ubuntu Server 24.04 ISO
3. Copy the ISO to the Ventoy USB drive
4. Copy this entire `founders_usb_installer/` directory to the USB drive
5. Boot the Beelink EQR5 from USB (press F7 for boot menu)
6. Select the Ubuntu ISO from Ventoy
7. When prompted for autoinstall, Ventoy will use `autoinstall/user-data`

## Installation Steps

1. **Boot from USB** — Beelink EQR5 → F7 → Select Ubuntu ISO
2. **Unattended Install** — Ubuntu installs automatically (~10-15 min)
3. **First Boot** — System runs `install-founders.sh` automatically (~20-30 min)
4. **Done** — Access dashboard at `http://empirebox.local`

## Post-Install Checklist

- [ ] Access dashboard: `http://empirebox.local` or `http://<ip>`
- [ ] Log in to OpenClaw: `http://empirebox.local:7878`
- [ ] Check Control Center: `http://empirebox.local:8001`
- [ ] Add AI API keys in OpenClaw UI (OpenAI, Anthropic, etc.)
- [ ] Test `ebox list` in terminal
- [ ] Run `ebox bundle full` to start all products

## Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Founders Dashboard | http://empirebox.local | — |
| OpenClaw | http://empirebox.local:7878 | admin / (see .env) |
| API Gateway | http://empirebox.local:8000 | Bearer token in .env |
| Control Center | http://empirebox.local:8001 | API key in .env |
| Portainer | http://empirebox.local:9000 | Set on first login |
| Ollama | http://empirebox.local:11434 | — |

## Default Credentials

All credentials are in `/opt/empirebox/.env` (chmod 600).

SSH access: `ssh empirebox@empirebox.local` (password: `founders2026`)

## Support

See `docs/TROUBLESHOOTING.md` for common issues.
