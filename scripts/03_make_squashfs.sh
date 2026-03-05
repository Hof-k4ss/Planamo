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

VMLINUZ=$(ls "$ROOTFS"/boot/vmlinuz-* 2>/dev/null | sort -V | tail -1)
INITRD=$(ls "$ROOTFS"/boot/initrd.img-* 2>/dev/null | sort -V | tail -1)

[ -z "$VMLINUZ" ] && { echo "ERROR: no vmlinuz found in $ROOTFS/boot/"; exit 1; }
[ -z "$INITRD"  ] && { echo "ERROR: no initrd.img found in $ROOTFS/boot/"; exit 1; }

echo "Kernel  : $(basename "$VMLINUZ")"
echo "Initrd  : $(basename "$INITRD")"

cp "$VMLINUZ" "$ISODIR/casper/vmlinuz"
cp "$INITRD"  "$ISODIR/casper/initrd"


echo "SquashFS créé."
