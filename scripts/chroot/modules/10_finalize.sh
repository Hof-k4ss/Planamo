#!/bin/bash
set -e

echo "=== Final system configuration ==="

echo planamo > /etc/hostname

cat <<EOF > /etc/hosts
127.0.0.1   localhost
127.0.1.1   planamo

::1         localhost ip6-localhost ip6-loopback
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
EOF

echo "=== Network auto configuration ==="

systemctl enable NetworkManager

# Autoriser NM à gérer toutes les interfaces
mkdir -p /etc/NetworkManager/conf.d
cat <<EOF > /etc/NetworkManager/conf.d/10-globally-managed-devices.conf
[keyfile]
unmanaged-devices=none
EOF

# Créer une connexion ethernet automatique
nmcli connection add type ethernet ifname "*" con-name "Wired connection" autoconnect yes || true
