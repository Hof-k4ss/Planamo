# 🛡 PLANAMO (Plateforme d'Analyse Mobile)
### Mobile Forensics & Incident Response Live Distribution

![Ubuntu](https://img.shields.io/badge/Base-Ubuntu%2024.04%20\(Noble\)-E95420?logo=ubuntu)
![Build](https://img.shields.io/badge/Build-debootstrap-blue)
![Desktop](https://img.shields.io/badge/Desktop-Xfce-lightgrey)
![License](https://img.shields.io/badge/License-Private-red)
![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen)

---

## 🎯 Overview

**PLANAMO** is a custom Ubuntu-based forensic live distribution built entirely from scratch using:

* `debootstrap`
* Automated modular chroot system
* Custom tool mapping architecture
* Offline Docker forensic environments

It is designed for:

* 📱 Mobile Forensics (Android / iOS)
* 🧪 Malware & Reverse Engineering
* 💽 Disk & Filesystem Analysis
* 🧠 Memory & Volatile Analysis
* 🌐 Network Forensics
* 🔍 OSINT & Threat Investigation
* 🐳 Offline forensic Docker containers

---

## 🏗 System Architecture

PLANAMO is modular and deterministic.

### Build Pipeline

```bash
scripts/docker/01_fetch_images.sh     # Pull Docker forensic images
01_debootstrap.sh                     # Bootstrap minimal Ubuntu Noble rootfs
02_chroot_setup.sh                    # Mount pseudo-fs, inject modules, run main.sh
scripts/chroot/main.sh                # Execute chroot modules 01 → 16
03_make_squashfs.sh                   # Build SquashFS (zstd) + extract kernel/initrd
04_make_iso.sh                        # Assemble bootable ISO via grub-mkrescue
```

### Chroot Module Order

```bash
01_base_system.sh       # APT base packages, locale, timezone
02_user.sh              # analyste user, sudo, password
03_tools_mobile.sh      # Mobile acquisition & analysis tools
04_tools_network.sh     # Network forensics tools
05_tools_disk.sh        # Disk & filesystem tools
06_tools_malware.sh     # Malware & reverse engineering tools
07_tools_osint.sh       # OSINT tools (incl. Tor Browser)
08_tools_dev.sh         # Development tools
09_tools_nonapt.sh      # Tools compiled from source (Rizin, etc.)
10_tools_custom.sh      # Custom scripts & wrappers
11_docker_load.sh       # Load offline Docker images
12_menu_structure.sh    # Generate .desktop launchers from tools_map.conf
13_menu_planamo.sh      # XFCE menu XML structure
14_documentation.sh     # MkDocs documentation generation
15_installer.sh         # bash+dialog installer (planamo-install)
16_finalize.sh          # LightDM autologin, wallpaper, desktop icons, trusted launchers
```

---

## 🧰 Tool Management

All tools are defined centrally in:

```
scripts/chroot/tools_map.conf
```

Format: `name|command|categories|type(gui/terminal)`

From this single source of truth:

* Desktop launchers are generated automatically
* MkDocs documentation pages are built
* XFCE menu categories are structured
* Tool type (GUI vs terminal) is determined

### Categories

| Category | XFCE Menu |
|---|---|
| Mobile Acquisition | X-PLANAMO-MOBILE-ACQ |
| Mobile Analysis | X-PLANAMO-MOBILE-ANALYSIS |
| Malware & Reverse Engineering | X-PLANAMO-MALWARE |
| Disk & Filesystem | X-PLANAMO-DISK |
| Memory & Volatile Analysis | X-PLANAMO-MEMORY |
| Network & Traffic | X-PLANAMO-NETWORK |
| OSINT & Investigation | X-PLANAMO-OSINT |
| Development & Scripting | X-PLANAMO-DEV |
| Docker & Services | X-PLANAMO-DOCKER |

---

## 🐳 Docker Integration

PLANAMO includes offline forensic containers pre-loaded at build time.

**Available images:**
* MobSF (Mobile Security Framework)

**Live Mode:**
* Overlay filesystem (changes lost on reboot)
* Temporary Docker instance
* MobSF available via `mobsf` wrapper

**Installed Mode:**
* Full persistent Docker environment
* All forensic images loaded at boot
* Persistent storage

**Available wrappers:**
```bash
mobsf                    # Launch MobSF container
planamo-docker-load      # Reload all Docker images
```

> Docker images >4GB are split at build time and reassembled on first run.

---

## 📚 Documentation System

Documentation is automatically generated during the build from `tools_map.conf`.

* Engine: **MkDocs** with Material Theme
* Output: `/opt/planamo/docs/site/index.html`
* Launcher: Desktop shortcut **PLANAMO Documentation** → `rtfm` or `planamo-doc`

```bash
rtfm          # Open documentation in Firefox
planamo-doc   # Alias for rtfm
```

---

## 💾 Installer

PLANAMO includes a custom bash+dialog installer (`planamo-install`) replacing Calamares.

**Features:**
* GPT partitioning (BIOS + UEFI support)
* Auto-detect EFI or legacy mode
* unsquashfs-based system copy
* Kernel copied from live casper/
* GRUB installed and configured
* Desktop install icon auto-removes after installation

**Launch:**
```bash
sudo planamo-install          # CLI
# or double-click desktop icon (live only)
```

---

## ⚙️ Build Requirements (Host)

Build must be performed on **Debian or Ubuntu**.

```bash
sudo apt install debootstrap squashfs-tools xorriso \
  grub-pc-bin grub-efi-amd64-bin mtools docker.io git
```

---

## 🔨 Build ISO

```bash
bash build.sh
```

**Build steps:**
1. Pull Docker forensic images
2. Bootstrap minimal Ubuntu Noble rootfs
3. Run 16 chroot modules (toolchain, menu, docs, installer, finalize)
4. Generate SquashFS with zstd compression
5. Assemble bootable ISO

**Output:** `planamo.iso`

**Logs:** `logs/build_YYYYMMDD_HHMMSS.log`

---

## 🧪 Live Environment

* Xfce desktop with autologin (`analyste`)
* Full forensic toolchain
* Local HTML documentation (`rtfm`)
* PLANAMO Applications menu
* Controlled Docker execution
* Install to disk via desktop icon
* No Snap dependencies

**Credentials:** `analyste / P@ssw0rd`

---

## 🔐 Design Principles

* No Snap dependency
* Deterministic modular build
* Single source of truth (`tools_map.conf`)
* Offline-ready Docker images
* Auto-generated documentation
* Strict separation:
  * APT tools (`01`–`08`)
  * Non-APT / compiled tools (`09`)
  * Custom scripts (`10`)
  * Docker services (`11`)

---

## 📈 Roadmap

* [x] Modular build system
* [x] Custom bash+dialog installer
* [x] XFCE menu with PLANAMO categories
* [x] Auto-generated MkDocs documentation
* [x] Docker offline image support (split >4GB)
* [x] iOS acquisition support
* [ ] Tool validation automation
* [ ] Versioned ISO releases
* [ ] GitLab CI build pipeline

---

## 🏷 Internal Project

Private professional GitLab repository.
Intended for forensic research, mobile investigations, and controlled lab environments.

---

© PLANAMO – Internal Development Project
