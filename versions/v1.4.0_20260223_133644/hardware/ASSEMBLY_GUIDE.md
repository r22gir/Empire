# Assembly Guide

## Step 1 — Unbox and Inspect

1. Verify all components against the [Bill of Materials](BILL_OF_MATERIALS.md).
2. Check for physical damage before powering on.
3. Keep original packaging until the system is confirmed working.

## Step 2 — Initial Hardware Setup

1. Place the mini PC on a flat, ventilated surface or mount it with the included VESA bracket.
2. Connect the external SSD via USB 3.x (fastest available port).
3. Connect to your router via Ethernet (preferred over Wi-Fi for stability).
4. Connect the UPS, then plug the mini PC and any peripherals into the UPS outlets.
5. Connect a monitor, keyboard, and mouse (only needed for initial setup).

## Step 3 — Power On and BIOS Configuration

1. Power on the mini PC.
2. Press **Delete** or **F2** at the splash screen to enter BIOS.
3. Follow the [BIOS Settings Guide](configs/bios-settings.md) to optimise for 24/7 operation.
4. Save and exit.

## Step 4 — Install Ubuntu 24.04 LTS

Follow the [Ubuntu Installation Guide](configs/ubuntu-install.md).

Key steps:
- Flash Ubuntu 24.04 LTS onto a USB drive (use Balena Etcher or `dd`).
- Boot from USB and select **Minimal Install**.
- Create a single ext4 partition on the internal drive.
- Set a strong password and enable automatic security updates.

## Step 5 — Run Post-Install Script

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/r22gir/Empire/main/hardware/configs/post-install.sh)
```

Or if you have the repo cloned:

```bash
chmod +x hardware/configs/post-install.sh
sudo hardware/configs/post-install.sh
```

The script installs Docker, Docker Compose, and all EmpireBox dependencies.

## Step 6 — Deploy EmpireBox

```bash
git clone https://github.com/r22gir/Empire.git
cd Empire
cp .env.example .env
# Edit .env with your API keys and configuration
docker compose up -d
```

## Step 7 — Connect Peripherals

1. **Label Printer**: Connect via USB or Wi-Fi and install CUPS driver.
2. **Barcode Scanner**: Pair via Bluetooth or USB; configure in ShipForge settings.
3. **Receipt Printer**: Connect via USB or Ethernet; configure in MarketForge POS settings.

## Step 8 — Verify

```bash
# Check all containers are running
docker compose ps

# Run health check
curl http://localhost:8000/health

# Test OpenClaw
curl http://localhost:7878/health
```
