#!/bin/bash
set -e

echo "=== Installing Calamares installer ==="

export DEBIAN_FRONTEND=noninteractive

# Calamares + dépendances nécessaires
apt install -y \
  calamares \
  squashfs-tools \
  rsync \
  parted \
  dosfstools \
  e2fsprogs \
  btrfs-progs \
  grub-pc-bin \
  grub-efi-amd64-bin \
  efibootmgr \
  os-prober \
  policykit-1

echo "=== Calamares installed ==="

# Dossiers de config
mkdir -p /etc/calamares/modules

# Settings Calamares (workflow basique)
cat > /etc/calamares/settings.conf <<'EOF'
modules-search: [ local ]

sequence:
  - show:
      - welcome
      - locale
      - keyboard
      - partition
      - users
      - summary

  - exec:
      - partition
      - mount
      - unpackfs
      - machineid
      - fstab
      - locale
      - keyboard
      - users
      - grubcfg
      - bootloader
EOF

# Module unpackfs : copie le système live depuis casper
cat > /etc/calamares/modules/unpackfs.conf <<'EOF'
unpack:
  - source: "/cdrom/casper/filesystem.squashfs"
    sourcefs: "squashfs"
    destination: ""
EOF

# IMPORTANT: s'assurer que Calamares a au moins un branding (sinon UI parfois vide)
# On met un branding minimal local
mkdir -p /etc/calamares/branding/planamo
cat > /etc/calamares/branding/planamo/branding.desc <<'EOF'
---
componentName: planamo
welcomeStyleCalamares: true
strings:
  productName: "PLANAMO"
  version: "Live"
  shortProductName: "PLANAMO"
  shortVersion: "Live"
  versionedName: "PLANAMO Live"
EOF

# Dire à calamares d’utiliser ce branding
# (si la clé existe déjà ailleurs, cette ligne suffit)
if ! grep -q '^branding:' /etc/calamares/settings.conf; then
  sed -i '1ibranding: planamo\n' /etc/calamares/settings.conf
fi

# Icône bureau (SKEL ONLY) : une seule, pas de copie depuis /usr/share/applications
echo "=== Desktop icon: Install PLANAMO (skel only) ==="
mkdir -p /etc/skel/Desktop

cat > /etc/skel/Desktop/Install-PLANAMO.desktop <<'EOF'
[Desktop Entry]
Name=Install PLANAMO
Exec=pkexec calamares
Icon=system-software-install
Terminal=false
Type=Application
EOF

chmod +x /etc/skel/Desktop/Install-PLANAMO.desktop

# Optionnel : garder aussi un launcher dans le menu (pas obligatoire, mais utile)
cat > /usr/share/applications/install-planamo.desktop <<'EOF'
[Desktop Entry]
Name=Install PLANAMO
Exec=pkexec calamares
Icon=system-software-install
Terminal=false
Type=Application
Categories=System;
OnlyShowIn=XFCE;
EOF
chmod 644 /usr/share/applications/install-planamo.desktop

echo "=== Calamares installer configured ==="

apt clean
