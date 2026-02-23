# BIOS Settings

Optimal BIOS configuration for 24/7 EmpireBox operation on mini PCs.

## Access BIOS

- Press **Delete**, **F2**, or **F12** at the splash screen (varies by manufacturer).

## Recommended Settings

### Power Management

| Setting | Recommended Value | Reason |
|---------|------------------|--------|
| AC Power Recovery | **Power On** | Auto-restart after power loss |
| Wake on LAN | **Enabled** | Remote management |
| ErP / S5 State | **Disabled** | Allow Wake on LAN |
| USB Wake | **Disabled** | Prevent accidental wake |
| CPU Performance Mode | **Balanced** | Lower heat, adequate speed |

### Boot

| Setting | Recommended Value |
|---------|------------------|
| Secure Boot | **Disabled** | Required for Ubuntu/Docker |
| Boot Mode | **UEFI** | Faster boot |
| Fast Boot | **Enabled** | Faster startup |
| Boot Device Priority | USB first, then NVMe | For installation |

### Storage

| Setting | Recommended Value |
|---------|------------------|
| SATA Mode | **AHCI** (not RAID) | Required for Linux |
| NVMe Power Management | **Enabled** | Better efficiency |

## After Installation

Change Boot Device Priority back to **NVMe only** to prevent accidental USB boot.

## Manufacturer-Specific Notes

- **Beelink**: BIOS accessed via **Delete** key; AC Recovery is under "Chipset → PCH-IO Configuration".
- **Intel NUC**: BIOS accessed via **F2**; Advanced → Power → After Power Failure → **Power On**.
- **MINISFORUM**: BIOS accessed via **Delete**; similar layout to AMI BIOS.
