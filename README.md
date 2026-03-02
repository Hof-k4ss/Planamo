# 🛡 PLANAMO – Forensic Live Distribution

Planamo is a custom Ubuntu-based forensic live distribution focused on:

- 📱 Mobile Forensics
- 🌐 Network Forensics
- 💽 Disk & Memory Analysis
- 🧪 Malware Analysis
- 🔍 OSINT
- 🐳 Offline Docker Forensic Environments

Built from scratch using debootstrap + custom chroot automation.

---

# ⚙️ Requirements (Build Machine)

Build must be done on Debian or Ubuntu with:

- debootstrap
- squashfs-tools
- xorriso
- grub-pc-bin
- grub-efi-amd64-bin
- mtools
- docker.io
- git

Install dependencies:

```bash
sudo apt install debootstrap squashfs-tools xorriso \
grub-pc-bin grub-efi-amd64-bin mtools docker.io git
