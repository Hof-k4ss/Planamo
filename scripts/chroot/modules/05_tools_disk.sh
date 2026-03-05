#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== Installing Disk / Filesystem Tools (forensics) ==="

apt install -y \
  gparted \
  gddrescue \
  dc3dd \
  partclone \
  testdisk \
  xfsprogs \
  btrfs-progs \
  exfatprogs \
  ntfs-3g \
  dosfstools \
  lvm2 \
  mdadm \
  cryptsetup \
  p7zip-full \
  rar \
  unrar \
  xz-utils \
  zip \
  unzip

apt clean
