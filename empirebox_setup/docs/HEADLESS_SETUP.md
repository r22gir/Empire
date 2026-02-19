# EmpireBox Headless Setup Guide

This guide explains how to set up your EmpireBox Mini PC without a monitor.

## Prerequisites

- EmpireBox Mini PC (Ryzen 7)
- Phone, tablet, or laptop for the setup wizard
- Internet connection (Ethernet cable recommended for first setup)

---

## Method 1: QR Code (Recommended)

1. **Find the QR sticker** on the bottom of your EmpireBox.
2. **Scan it** with your phone's camera or a QR app.
3. The setup portal opens automatically at `https://setup.empirebox.com/device/{DEVICE_ID}`.
4. Complete the 5-step wizard:
   - **Account** – sign in or create an EmpireBox account
   - **License** – enter your license key
   - **Products** – choose which apps to install
   - **AI Models** – select Ollama models
   - **Install** – watch real-time progress

---

## Method 2: Local Network (mDNS)

1. Connect EmpireBox to your router with an Ethernet cable.
2. Power on the device.
3. On a phone or computer on the same network, open:
   ```
   http://EmpireBox-<SERIAL>.local:8080
   ```
   Replace `<SERIAL>` with the serial number on the bottom label.
4. Complete the setup wizard.

> **Tip:** On Windows, install [Bonjour Print Services](https://support.apple.com/kb/DL999) if `.local` names don't resolve.

---

## Method 3: Bluetooth LE Beacon

Your EmpireBox broadcasts a Bluetooth Low Energy beacon before any network is configured.

1. Enable Bluetooth on your phone.
2. Open a BLE scanner app (e.g., nRF Connect, LightBlue).
3. Look for `EmpireBox-<SERIAL>` advertising an Eddystone-URL.
4. Tap the URL to open the setup portal.

---

## Method 4: USB Auto-Config

See [USB_CONFIG.md](USB_CONFIG.md) for full details.

**Quick summary:**
1. Create `empirebox-config.json` on a USB drive.
2. Plug it in — setup starts automatically within 30 seconds.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| QR code not scanning | Use the device serial at `setup.empirebox.com` instead |
| `.local` address not found | Use the IP address shown on the router's admin page |
| BLE beacon not visible | Ensure Bluetooth is enabled and you're within 10 meters |
| USB not detected | Ensure the drive is FAT32 or exFAT formatted |
| Setup wizard stuck | Refresh the page; the device retries automatically |

---

## After Setup

- All services start automatically on every boot.
- Access your apps at `http://EmpireBox-<SERIAL>.local`
- Logs: `journalctl -u empirebox.service -f`
