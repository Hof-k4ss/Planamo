#!/bin/bash
set -e

WORKDIR="$(pwd)/work"
ROOTFS="$WORKDIR/planamo-root"

echo "=== Nettoyage ancien rootfs ==="
sudo rm -rf "$ROOTFS"
mkdir -p "$ROOTFS"

echo "=== Forcer IPv4 pour debootstrap ==="
sudo bash -c 'echo "Acquire::ForceIPv4 \"true\";" > /etc/apt/apt.conf.d/99force-ipv4'

sudo debootstrap \
  --arch=amd64 \
  --variant=minbase \
  noble \
  "$ROOTFS" \
  http://fr.archive.ubuntu.com/ubuntu/

echo "=== Debootstrap terminé ==="
