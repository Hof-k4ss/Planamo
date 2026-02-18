#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== Base system installation ==="

# Dépôts Ubuntu
cat <<EOF > /etc/apt/sources.list
deb http://fr.archive.ubuntu.com/ubuntu noble main restricted universe multiverse
deb http://fr.archive.ubuntu.com/ubuntu noble-updates main restricted universe multiverse
deb http://fr.archive.ubuntu.com/ubuntu noble-security main restricted universe multiverse
EOF

echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
apt update

apt install -y \
    ubuntu-standard \
    sudo \
    systemd-sysv \
    casper \
    linux-image-generic \
    linux-headers-generic \
    xubuntu-desktop \
    dbus-x11 \
    policykit-1 \
    network-manager \
    net-tools \
    network-manager-gnome \
    iproute2 \
    ethtool \
    wireless-tools \
    wpasupplicant \
    linux-firmware \
    ca-certificates

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
# Locale English
# -----------------------
apt install -y locales
locale-gen en_US.UTF-8
update-locale LANG=en_US.UTF-8

# Remove ifupdown if present
apt purge -y ifupdown || true

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

apt clean
