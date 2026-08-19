#!/bin/bash
set -e

WORKDIR="$(pwd)/work"
ISODIR="$WORKDIR/iso"

echo "=== Building PLANAMO ISO (UDF for >4GiB files) ==="

grub-mkrescue \
  -o planamo.iso \
  "$ISODIR" \
  -- \
  -as mkisofs \
  -iso-level 3 \
  -full-iso9660-filenames \
  -R -J \

echo "=== ISO BUILT SUCCESSFULLY ==="
