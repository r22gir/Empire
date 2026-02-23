# EmpireBox Headless Setup System

Complete headless setup system for EmpireBox Mini PC devices (Ryzen 7). Allows first-time configuration without a monitor — users can set up their device using a phone, tablet, or another computer.

## Discovery Methods

| Method | Description |
|--------|-------------|
| **QR Code** | Physical sticker on device links to `setup.empirebox.com/device/{DEVICE_ID}` |
| **mDNS** | Device broadcasts as `EmpireBox-{SERIAL}.local` on local network |
| **Bluetooth LE** | Eddystone URL beacon even before network is configured |
| **USB Config** | Drop `empirebox-config.json` on USB drive for zero-touch setup |

## Quick Start

### Option 1 — QR Code (Easiest)
1. Scan the QR sticker on the bottom of your EmpireBox
2. Open the URL on your phone or computer
3. Follow the setup wizard

### Option 2 — Network Discovery
1. Connect EmpireBox to your network via Ethernet
2. Open `http://EmpireBox-<SERIAL>.local:8080` in your browser
3. Follow the setup wizard

### Option 3 — USB Auto-Config
1. Create `empirebox-config.json` (see `docs/USB_CONFIG.md`)
2. Copy to a USB drive
3. Plug USB into EmpireBox — setup starts automatically

## Installation

```bash
chmod +x scripts/*.sh
sudo ./scripts/bulk-install.sh
```

## Directory Structure

```
empirebox_setup/
├── scripts/        # Shell scripts for each discovery method
├── services/       # systemd service unit files
├── config/         # mDNS and JSON schema configs
├── setup-portal/   # Next.js web setup portal
└── docs/           # User and deployment documentation
```

## Documentation

- [Headless Setup Guide](docs/HEADLESS_SETUP.md)
- [USB Configuration](docs/USB_CONFIG.md)
- [Enterprise Deployment](docs/ENTERPRISE_DEPLOY.md)

## Design

- Color scheme: Gold `#C9A84C` / Charcoal `#2C2C2C`
- Responsive for phone, tablet, and desktop
