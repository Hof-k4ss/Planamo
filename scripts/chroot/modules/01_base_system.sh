#!/bin/bash
set -e

# ============================================================
# PLANAMO - Base system installation
# Ubuntu 26.04 / Resolute
# ============================================================

export DEBIAN_FRONTEND=noninteractive
unset LANG LANGUAGE LC_ALL LC_CTYPE LC_MESSAGES
export DEBIAN_FRONTEND=noninteractive

# Ne pas laisser les signaux de job-control suspendre le script
# pendant l'exécution du build dans le chroot.
trap '' TSTP TTIN TTOU

# Désactiver l'utilisation du pseudo-terminal par dpkg.
APT_GET="apt-get -o Dpkg::Use-Pty=0"

echo "=== Base system installation ==="

# -----------------------
# Dépôts Ubuntu
# -----------------------
cat <<EOF > /etc/apt/sources.list
deb http://fr.archive.ubuntu.com/ubuntu resolute main restricted universe multiverse
deb http://fr.archive.ubuntu.com/ubuntu resolute-updates main restricted universe multiverse
deb http://fr.archive.ubuntu.com/ubuntu resolute-security main restricted universe multiverse
EOF

echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

$APT_GET update

# -----------------------
# Locale de base
# -----------------------
echo "=== Installation de locales ==="

$APT_GET install -y locales

echo "=== Activation de en_US.UTF-8 ==="

grep -qxF 'en_US.UTF-8 UTF-8' /etc/locale.gen || \
    echo 'en_US.UTF-8 UTF-8' >> /etc/locale.gen

locale-gen en_US.UTF-8

echo "=== Vérification locale ==="

locale -a

grep -qx 'en_US.utf8' < <(locale -a) || {
    echo "ERROR: en_US.UTF-8 absente"
    exit 1
}

cat > /etc/default/locale <<'EOF'
LANG=en_US.UTF-8
LANGUAGE=en_US:en
EOF

export LANG=en_US.UTF-8
export LANGUAGE=en_US:en

# -----------------------
# Paquets de base
# -----------------------
$APT_GET install -y \
    ubuntu-standard \
    sudo \
    systemd-sysv \
    casper \
    initramfs-tools \
    linux-image-generic \
    linux-headers-generic \
    dbus-x11 \
    polkitd \
    pkexec \
    network-manager \
    network-manager-gnome \
    iproute2 \
    ethtool \
    iw \
    wpasupplicant \
    linux-firmware \
    ca-certificates \
    htop \
    kpartx \
    xfce4 \
    xfce4-goodies \
    xfce4-terminal \
    thunar \
    thunar-archive-plugin \
    thunar-volman \
    gvfs \
    gvfs-backends \
    lightdm \
    lightdm-gtk-greeter \
    libreoffice \
    open-vm-tools \
    open-vm-tools-desktop

# -----------------------
# Display manager : LightDM
# -----------------------
systemctl disable gdm3.service 2>/dev/null || true
rm -f /etc/systemd/system/display-manager.service
systemctl enable lightdm.service

# -----------------------
# Hostname
# -----------------------
echo "planamo" > /etc/hostname

cat <<EOF > /etc/hosts
127.0.0.1   localhost
127.0.1.1   planamo

::1         localhost ip6-localhost ip6-loopback
fe00::0     ip6-localnet
ff00::0     ip6-mcastprefix
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
EOF

# -----------------------
# Keyboard AZERTY
# -----------------------
cat <<EOF > /etc/default/keyboard
XKBMODEL="pc105"
XKBLAYOUT="fr"
XKBVARIANT=""
XKBOPTIONS=""
BACKSPACE="guess"
EOF

# -----------------------
# Remove ifupdown
# -----------------------
$APT_GET purge -y ifupdown || true

cat <<EOF > /etc/NetworkManager/NetworkManager.conf
[main]
plugins=keyfile

[device]
wifi.scan-rand-mac-address=no
EOF

# -----------------------
# Enable NetworkManager
# -----------------------
systemctl enable NetworkManager

# -----------------------
# Upgrade
# -----------------------
$APT_GET upgrade -y

# -----------------------
# Nettoyage APT
# -----------------------
$APT_GET clean

echo "=== Base system done ==="
