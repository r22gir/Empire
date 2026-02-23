# Ubuntu 24.04 LTS Installation Guide

## 1. Download Ubuntu 24.04 LTS

```
https://ubuntu.com/download/server
```

Choose **Ubuntu Server 24.04 LTS** (minimal, no GUI needed).

## 2. Create Bootable USB

### On macOS/Linux
```bash
# Replace /dev/sdX with your USB drive
sudo dd if=ubuntu-24.04-live-server-amd64.iso of=/dev/sdX bs=4M status=progress && sync
```

### On Windows
Use [Rufus](https://rufus.ie) or [Balena Etcher](https://etcher.balena.io).

## 3. Boot from USB

1. Insert USB drive.
2. Power on the mini PC.
3. Press the boot menu key (**F12**, **F11**, or **Esc**).
4. Select the USB drive.

## 4. Installation Steps

1. **Language**: English
2. **Keyboard**: Your locale
3. **Installation type**: Ubuntu Server (minimized)
4. **Network**: Configure Ethernet (set static IP if needed — see [Networking](../specs/networking.md))
5. **Storage**: Use entire disk → set up as LVM (optional but recommended)
6. **Profile**: Create a user account (e.g., `empirebox`)
7. **SSH**: ✅ Install OpenSSH server
8. **Snaps**: Skip (deselect all)

## 5. First Boot

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git htop unzip

# Run post-install script
sudo bash hardware/configs/post-install.sh
```

## 6. Enable Automatic Security Updates

```bash
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

## 7. Set Timezone

```bash
sudo timedatectl set-timezone America/New_York  # Adjust to your timezone
```

## 8. Enable Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw enable
```
