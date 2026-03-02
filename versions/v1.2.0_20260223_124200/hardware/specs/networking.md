# Networking

## Recommended Setup

```
ISP Modem/Router
       │
       ├── Gigabit Switch (TP-Link TL-SG108 or similar)
       │         │
       │         ├── EmpireBox Mini PC (static IP)
       │         ├── Label Printer
       │         └── Other wired devices
       │
       └── Wi-Fi AP (for mobile devices, optional)
```

## Switches

| Model | Ports | Speed | Price |
|-------|-------|-------|-------|
| TP-Link TL-SG108 | 8 | Gigabit | ~$25 |
| TP-Link TL-SG116E | 16 | Gigabit managed | ~$60 |
| Netgear GS308 | 8 | Gigabit | ~$25 |

## Routers

| Model | Type | Price |
|-------|------|-------|
| TP-Link Archer AX55 | Wi-Fi 6 | ~$90 |
| ASUS RT-AX86U | Wi-Fi 6 gaming | ~$200 |
| UniFi Express | Professional | ~$149 |

## Static IP Configuration (Ubuntu 24.04)

Edit `/etc/netplan/00-installer-config.yaml`:

```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: false
      addresses: [192.168.1.100/24]
      gateway4: 192.168.1.1
      nameservers:
        addresses: [1.1.1.1, 8.8.8.8]
```

Apply: `sudo netplan apply`

## Firewall (UFW)

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 7878/tcp  # OpenClaw
sudo ufw enable
```
