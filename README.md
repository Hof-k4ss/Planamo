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
01_fetch_images.sh
01_debootstrap.sh
02_chroot_setup.sh
modules/ (01 → 14)
03_make_squashfs.sh
04_make_iso.sh
```

### Chroot Module Order

```bash
01_base_system.sh
02_user.sh
03_tools_mobile.sh
04_tools_network.sh
05_tools_disk.sh
06_tools_malware.sh
07_tools_osint.sh
08_dev_tools.sh
09_tools_nonapt.sh
10_tools_custom.sh
11_docker_load.sh
12_menu_structure.sh
13_documentation.sh
14_finalize.sh
```

---

## 🧰 Tool Management

All tools are defined centrally in:

```
scripts/chroot/tools_map.conf
```

From this single source:

* Desktop launchers are generated
* MkDocs documentation is generated
* Tool categories are structured
* Documentation pages are built automatically

### Categories

* Mobile Acquisition
* Mobile Analysis
* Malware & Reverse Engineering
* Disk & Filesystem
* Memory & Volatile Analysis
* Network & Traffic
* OSINT & Investigation
* Development & Scripting
* Docker & Services

---

## 🐳 Docker Integration

PLANAMO includes offline forensic containers:

* MobSF

### Live Mode

* Overlay filesystem
* Temporary Docker instance
* MobSF available

### Installed Mode

* Full Docker support
* All forensic images loaded
* Persistent environment

Available wrappers:

```bash
mobsf
planamo-docker-load
```

---

## 📚 Documentation System

Documentation is automatically generated during build.

Engine:

* MkDocs
* Material Theme

Output location:

```
/opt/planamo/docs/site/index.html
```

A desktop shortcut **PLANAMO Documentation** is automatically created.

---

## ⚙️ Build Requirements (Host)

Build must be performed on Debian or Ubuntu.

Install required packages:

```bash
sudo apt install debootstrap squashfs-tools xorriso \
grub-pc-bin grub-efi-amd64-bin mtools docker.io git
```

---

## 🔨 Build ISO

From project root:

```bash
bash build.sh
```

Build process:

1. Download Docker images
2. Bootstrap minimal Ubuntu
3. Install forensic toolchain
4. Generate documentation
5. Create SquashFS
6. Build bootable ISO

Output:

```
planamo.iso
```

---

## 🧪 Live Environment

* Xfce desktop
* Forensic toolchain
* Local HTML documentation
* Controlled Docker execution
* No Snap dependencies

---

## 💾 Installed System

* Persistent disk installation
* Full Docker environment
* Complete forensic stack
* Modular maintainability

---

## 🔐 Design Principles

* No Snap dependency
* Deterministic tool architecture
* Modular build system
* Offline-ready Docker images
* Auto-generated documentation
* Strict separation between:

  * APT tools
  * Non-APT tools
  * Custom tools
  * Docker services

---

## 📈 Roadmap

* Installer integration
* Advanced menu categorization
* Tool validation automation
* Versioned ISO releases
* GitLab CI build pipeline
* Integration docker images >4Go
---

## 🏷 Internal Project

Private professional GitLab repository.
Intended for forensic research, mobile investigations, and controlled lab environments.

---

© PLANAMO – Internal Development Project
