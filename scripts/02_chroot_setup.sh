#!/bin/bash
set -ex

WORKDIR="$(pwd)/work"
ROOTFS="$WORKDIR/planamo-root"

cleanup() {
    echo "Nettoyage des mounts..."
    sudo umount -lf "$ROOTFS/dev/pts" 2>/dev/null || true
    sudo umount -lf "$ROOTFS/dev" 2>/dev/null || true
    sudo umount -lf "$ROOTFS/proc" 2>/dev/null || true
    sudo umount -lf "$ROOTFS/sys" 2>/dev/null || true
    sudo umount -lf "$ROOTFS/etc/resolv.conf" 2>/dev/null || true
}

trap cleanup EXIT

echo "Mount des pseudo-filesystems..."
sudo mount --bind /dev "$ROOTFS/dev"
sudo mount --bind /dev/pts "$ROOTFS/dev/pts"
sudo mount --bind /proc "$ROOTFS/proc"
sudo mount --bind /sys "$ROOTFS/sys"
sudo mount --bind /etc/resolv.conf "$ROOTFS/etc/resolv.conf"

# Copier images Planamo
sudo mkdir -p "$ROOTFS/usr/share/planamo"
sudo cp images/* "$ROOTFS/usr/share/planamo/"

# Copier les modules dans le chroot
sudo mkdir -p "$ROOTFS/root/modules"
sudo cp -r scripts/chroot/modules/* "$ROOTFS/root/modules/"
sudo cp scripts/chroot/main.sh "$ROOTFS/root/main.sh"
sudo cp -r outils "$ROOTFS/root/"

# Création des thèmes
cp scripts/chroot/tools_map.conf "$ROOTFS/root/tools_map.conf"

echo "Entrée dans le chroot..."
sudo chroot "$ROOTFS" /bin/bash /root/main.sh

# Nettoyage
sudo rm -rf "$ROOTFS/root/modules"
sudo rm "$ROOTFS/root/main.sh"

echo "Configuration chroot terminée."
