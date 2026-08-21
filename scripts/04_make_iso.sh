#!/bin/bash
set -e

WORKDIR="$(pwd)/work"
ISODIR="$WORKDIR/iso"

echo "=== Building PLANAMO ISO ==="

rm -f planamo.iso

grub-mkrescue \
  -o planamo.iso \
  "$ISODIR" \
  -iso-level 3 \
  -R \
  -J

echo "=== ISO BUILT SUCCESSFULLY ==="