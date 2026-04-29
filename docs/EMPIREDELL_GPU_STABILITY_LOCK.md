# EmpireDell GPU Stability Lock

**Machine:** EmpireDell (Intel Xeon E5-2650 v3, 32GB RAM, 20 cores, NVIDIA Quadro K600)
**Date of incident:** April 2026
**Status:** LOCKED — known-good state achieved

---

## Incident Summary

EmpireDell experienced a severe NVIDIA graphics/kernel breakage in April 2026.

**Root cause chain:**
1. Ubuntu promoted the machine to the HWE kernel (`6.17.x`), replacing `6.8.0-31-generic`
2. NVIDIA 470 DKMS failed to build against the new kernel
3. A subsequent attempt to install `nvidia-driver-470` (meta-package) pulled DKMS components
4. A version mismatch developed between the prebuilt NVIDIA kernel module (`470.239.06`) and the userspace driver (`470.256.02`)
5. The system entered a crash loop requiring full recovery

**Final stable fix:**
- Boot into kernel `6.8.0-31-generic` via GRUB
- Install the matching prebuilt NVIDIA 470 module package (`linux-modules-nvidia-470-6.8.0-31-generic`)
- Downgrade NVIDIA userspace to `470.239.06`
- Set GRUB default to boot `6.8.0-31-generic`
- Hold all NVIDIA 470 and kernel 6.8.0-31 packages

---

## Known-Good Stable Stack

| Component | Version |
|-----------|---------|
| Kernel | `6.8.0-31-generic` |
| NVIDIA driver/userspace | `470.239.06` |
| NVIDIA prebuilt module | `linux-modules-nvidia-470-6.8.0-31-generic` |
| GPU | NVIDIA Quadro K600 / GK107GL |
| Resolution | 2560x1080 |
| GRUB default | Advanced options for Ubuntu > Ubuntu, with Linux 6.8.0-31-generic |

---

## Exact Stable Package Stack (April 2026)

```
linux-image-6.8.0-31-generic         6.8.0-31.31
linux-modules-6.8.0-31-generic        6.8.0-31.31
linux-modules-extra-6.8.0-31-generic  6.8.0-31.31
linux-modules-nvidia-470-6.8.0-31-generic  (version from nvidia-470 meta)
linux-objects-nvidia-470-6.8.0-31-generic  (version from nvidia-470 meta)
linux-signatures-nvidia-6.8.0-31-generic   (version from nvidia-470 meta)
nvidia-utils-470                  470.239.06-0ubuntu2
nvidia-kernel-common-470          470.239.06-0ubuntu2
xserver-xorg-video-nvidia-470     470.239.06-0ubuntu2
libnvidia-*                       470.239.06-0ubuntu2
```

---

## Lockdown Mechanisms in Place

### APT Holds
```bash
sudo apt-mark hold linux-image-6.8.0-31-generic
sudo apt-mark hold linux-modules-6.8.0-31-generic
sudo apt-mark hold linux-modules-extra-6.8.0-31-generic
sudo apt-mark hold linux-modules-nvidia-470-6.8.0-31-generic
sudo apt-mark hold linux-objects-nvidia-470-6.8.0-31-generic
sudo apt-mark hold linux-signatures-nvidia-6.8.0-31-generic
sudo apt-mark hold nvidia-utils-470
sudo apt-mark hold nvidia-kernel-common-470
sudo apt-mark hold xserver-xorg-video-nvidia-470
```

### APT Pin File
**File:** `/etc/apt/preferences.d/99-empiredell-gpu-stability`
Prevents HWE kernel meta-packages from being installed.

### HWE Kernel Meta-Package Holds
```
linux-generic-hwe-24.04        (held)
linux-image-generic-hwe-24.04  (held)
linux-headers-generic-hwe-24.04 (held)
```

---

## Forbidden Commands

**NEVER run these on EmpireDell:**

| Command | Why |
|---------|-----|
| `sudo apt autoremove` | Removes kernel/modules required for NVIDIA 470 prebuilt |
| `sudo apt upgrade` | Upgrades kernel or NVIDIA packages |
| `sudo apt full-upgrade` | Same as above — full upgrade |
| `apt install nvidia-driver-470` | Meta/DKMS path caused crash loop |
| `apt install nvidia-dkms-470` | DKMS mismatch with prebuilt userspace |
| `apt install nvidia-kernel-source-470` | Pulls DKMS, causes mismatch |
| `apt install nvidia-kernel-common-470` | Same as above |
| `ubuntu-drivers autoinstall` | Installs DKMS-based NVIDIA driver |
| HWE kernel packages | `linux-generic-hwe-*`, `linux-image-generic-hwe-*` |
| `apt-mark unhold` | Removes the package holds |
| `update-initramfs -u` | Can break NVIDIA module initrd loading |
| `grub-set-default` / `grub-install` | Can change boot kernel away from 6.8.0-31 |
| `dkms remove/add/build` | Changes DKMS state — caused the original crash |
| `nvidia-smi --reset` | Can destabilize the driver |
| `modprobe -r nvidia` | Unloads driver, may not reload cleanly |
| `sensors-detect` | Crashes EmpireDell (also documented in Beelink stability guide) |

---

## Before Any Linux/NVIDIA/Package Changes

**Rule:** Always simulate first. Never run blind.

```bash
sudo apt update
sudo apt-get -s upgrade | grep -Ei "linux|nvidia|dkms|grub" || true
```

If the simulation output contains any of: `linux-image`, `linux-modules`, `nvidia`, `dkms`, `hwe`, `grub`, `kernel` — **STOP**. Do not proceed. Show the output to the founder and get explicit approval before running the actual upgrade.

---

## Verification Commands

Run these to verify the GPU stack is in the known-good state:

```bash
# 1. Kernel version — must be 6.8.0-31-generic
uname -r

# 2. NVIDIA driver — must show Driver Version 470.239.06
nvidia-smi

# 3. Loaded modules — should show nvidia, NOT nouveau
lsmod | grep -E "nvidia|nouveau"

# 4. Display — should show 2560x1080
xrandr | head -30

# 5. Held packages — should list all NVIDIA 470 and kernel 6.8.0-31 packages
apt-mark showhold | grep -E "nvidia|linux|hwe" || true

# 6. Package policy — candidates must remain at 470.239.06 / 6.8.0-31
apt-cache policy nvidia-utils-470 linux-image-6.8.0-31-generic nvidia-dkms-470 | sed -n '1,120p'
```

**Expected outputs:**
- `uname -r` = `6.8.0-31-generic`
- `nvidia-smi` works and shows `Driver Version 470.239.06`
- `lsmod` shows `nvidia` and no `nouveau`
- `xrandr` shows `2560x1080` active
- `nvidia-utils-470` candidate remains `470.239.06-0ubuntu2`
- `linux-image-6.8.0-31-generic` candidate remains `6.8.0-31.31`
- `nvidia-dkms-470` candidate remains absent or blocked

---

## Recovery Checklist

If the GPU stack breaks (black screen, crash loop, `nvidia-smi` fails):

1. **Boot into kernel 6.8.0-31-generic**
   - At GRUB menu: `Advanced options for Ubuntu` → `Ubuntu, with Linux 6.8.0-31-generic`

2. **Check what broke the stack:**
   ```bash
   apt-mark showhold | grep -E "nvidia|linux|hwe"
   apt-cache policy nvidia-utils-470
   uname -r
   ```

3. **If userspace is wrong version (e.g. 470.256.02):**
   ```bash
   sudo apt install nvidia-utils-470=470.239.06-0ubuntu2
   ```

4. **If kernel was upgraded:**
   ```bash
   sudo apt install linux-image-6.8.0-31-generic=6.8.0-31.31
   sudo apt install linux-modules-6.8.0-31-generic=6.8.0-31.31
   ```

5. **Reboot:**
   ```bash
   sudo reboot
   ```

6. **Verify:**
   ```bash
   uname -r        # must be 6.8.0-31-generic
   nvidia-smi      # must show 470.239.06
   ```

7. **Re-apply holds if needed:**
   ```bash
   sudo apt-mark hold linux-image-6.8.0-31-generic linux-modules-6.8.0-31-generic nvidia-utils-470
   ```

---

## How to Intentionally Unlock/Migrate the GPU Stack

The GPU stability lock must only be removed by explicit founder decision. Steps:

1. **Identify the target state** (new GPU, new driver version, new kernel, etc.)
2. **Read the current stable state** — `~/EMPIREDELL_GRAPHICS_STABLE_STATE.md`
3. **Remove the APT pin file:** `sudo rm /etc/apt/preferences.d/99-empiredell-gpu-stability`
4. **Unhold packages:** `sudo apt-mark unhold linux-image-6.8.0-31-generic linux-modules-6.8.0-31-generic nvidia-utils-470 ...`
5. **Test in simulation first:** `sudo apt-get -s upgrade`
6. **Boot into a recovery kernel** before making changes
7. **After any change**, verify with the verification commands above
8. **Re-apply locks** if the new stack is also fragile

**Warning:** NVIDIA driver/kernel migrations on this hardware have a history of causing crash loops with no remote recovery path. Ensure console/physical access before attempting any GPU stack migration.

---

## Local Truth Sources

- `~/EMPIREDELL_GRAPHICS_STABLE_STATE.md` — Recovery note kept on EmpireDell filesystem
- `/etc/apt/preferences.d/99-empiredell-gpu-stability` — APT pin file
- `apt-mark showhold` — Current package holds

---

## MAX Integration

The GPU stability lock is enforced in multiple layers:

1. **System prompt** (`backend/app/services/max/system_prompt.py`) — Full GPU lock section embedded in MAX's prompt; compact prompt includes abbreviated lock
2. **Guardrails** (`backend/app/services/max/guardrails.py`) — `check_gpu_safety()` function with `GPU_RISKY_PATTERNS` and `GPU_SAFETY_KEYWORDS`
3. **Router** (`backend/app/routers/max/router.py`) — `_maybe_handle_gpu_safety_request()` intercepts risky queries and returns a GPU safety response with `model_used="gpu-safety-guardrail"`
4. **Tool safety** (`backend/app/services/max/tool_safety.py`) — Dangerous commands (apt autoremove, NVIDIA DKMS installs, HWE packages) are blocked at the `validate_command()` level
5. **Memory** (`~/empire-box-memory/MEMORY.md`) — GPU stability lock is persisted in MAX's memory

MAX will **warn** (not block) on GPU/kernel/apt queries, providing verification commands and explaining the known-good stack. The warning is prepended to MAX's response with `model_used="gpu-safety-guardrail"`.

MAX will **block** (refuse to execute) any attempt to actually run a forbidden command via the tool safety system.
