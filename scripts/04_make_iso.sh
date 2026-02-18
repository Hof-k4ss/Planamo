#!/bin/bash
set -e

WORKDIR="$(pwd)/work"
ISODIR="$WORKDIR/iso"

grub-mkrescue \
  -o planamo.iso \
  "$ISODIR" \
  --modules="gfxterm png all_video"

echo "ISO générée : planamo.iso"
