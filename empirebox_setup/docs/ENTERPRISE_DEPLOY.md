# EmpireBox Enterprise Deployment Guide

Bulk deployment of multiple EmpireBox Mini PC devices.

## Overview

For deployments of 5+ devices, the USB Auto-Config method provides zero-touch provisioning:

1. Create a master `empirebox-config.json` with your organization's settings.
2. Copy to USB drives (one per device, or use a shared image).
3. Plug USB into each device — setup runs automatically.
4. Devices report completion to `setup.empirebox.com/api/device/{ID}/complete`.

## Creating a Master Config

```json
{
  "licenseKey": "EMPIRE-XXXX-XXXX-XXXX-XXXX",
  "accountEmail": "admin@yourcompany.com",
  "accountToken": "long-lived-api-token",
  "selectedProducts": ["marketforge", "supportforge", "forgecrm", "empireassist"],
  "ollamaModels": ["llama3.1:8b", "nomic-embed-text"],
  "timezone": "America/Chicago",
  "enableCrypto": false
}
```

## Bulk USB Image

Flash multiple drives with the same config:

```bash
# Create config
cat > empirebox-config.json << 'EOF'
{ ... your config ... }
EOF

# Flash to USB (replace /dev/sdX with your drive)
sudo mkfs.fat -F 32 /dev/sdX
sudo mount /dev/sdX /mnt/usb
sudo cp empirebox-config.json /mnt/usb/
sudo umount /mnt/usb
```

## Network-Based Deployment

For large deployments on a managed network, use the API:

```bash
# Discover all EmpireBox devices on the network
avahi-browse -r _empirebox._tcp

# Push config to a specific device
curl -X POST http://EmpireBox-<SERIAL>.local:8080/api/configure \
  -H "Content-Type: application/json" \
  -d @master-config.json
```

## Monitoring Fleet Status

```bash
# Check all devices on the network
avahi-browse -apt | grep empirebox

# View logs on a specific device (SSH required)
ssh empirebox@EmpireBox-<SERIAL>.local
journalctl -u empirebox.service -f
```

## Rollback / Re-Deploy

To re-run setup on a device:

```bash
# SSH into the device
ssh empirebox@EmpireBox-<SERIAL>.local

# Remove the first-boot flag and re-run
sudo rm /var/lib/empirebox/first-boot-done
sudo systemctl start empirebox-usb-watch.service
```

## Support

- Documentation: https://docs.empirebox.com/enterprise
- Email: enterprise@empirebox.com
