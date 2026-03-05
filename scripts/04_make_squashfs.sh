#!/bin/bash
set -e

WORKDIR="$(pwd)/work"
ROOTFS="$WORKDIR/planamo-root"
ISODIR="$WORKDIR/iso"

mkdir -p "$ISODIR/casper"
mkdir -p "$ISODIR/boot/grub"

# --- GRUB THEME ---
mkdir -p "$ISODIR/boot/grub/themes/planamo"
cp -r config/grub-theme/* "$ISODIR/boot/grub/themes/planamo/"
cp config/grub.cfg "$ISODIR/boot/grub/grub.cfg"

rm -f "$ISODIR/casper/filesystem.squashfs"
mksquashfs "$ROOTFS" "$ISODIR/casper/filesystem.squashfs" -noappend -comp xz -b 1048576 -Xbcj x86 -e boot

echo "Création du manifest..."
sudo chroot "$ROOTFS" dpkg-query -W --showformat='${Package} ${Version}\n' > "$ISODIR/casper/filesystem.manifest"

cp "$ISODIR/casper/filesystem.manifest" "$ISODIR/casper/filesystem.manifest-desktop"

echo $(sudo du -sx --block-size=1 "$ROOTFS" | cut -f1) > "$ISODIR/casper/filesystem.size"
mkdir -p "$ISODIR/.disk"
echo "Planamo Live" > "$ISODIR/.disk/info"

cp "$ROOTFS"/boot/vmlinuz-* "$ISODIR/casper/vmlinuz"
cp "$ROOTFS"/boot/initrd.img-* "$ISODIR/casper/initrd"


echo "SquashFS créé."
