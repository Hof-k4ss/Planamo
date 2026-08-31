#!/bin/bash
set -e

WORKDIR="$(pwd)/work"
ISODIR="$WORKDIR/iso"
VERSION="v2.0.0"

echo "=== Building PLANAMO ISO $VERSION ==="

grub-mkrescue \
  -o "planamo_${VERSION}.iso" \
  "$ISODIR" \
  -- \
  -as mkisofs \
  -iso-level 3 \
  -full-iso9660-filenames \
  -R -J \

echo "=== ISO BUILT SUCCESSFULLY ==="
