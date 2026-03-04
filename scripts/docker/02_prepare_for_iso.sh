#!/bin/bash
set -e

WORKDIR="$(pwd)/work"
TARGET_DIR="$WORKDIR/iso/docker-images"
SRC_DIR="$(pwd)/docker-images"

echo "=== Prepare docker images for ISO ==="
echo "[*] Source: $SRC_DIR"
echo "[*] Target: $TARGET_DIR"

mkdir -p "$TARGET_DIR"

# Nettoie l'ancien contenu pour éviter les restes (ex: remnux)
rm -f "$TARGET_DIR"/*.tar "$TARGET_DIR"/*.tar.part-* 2>/dev/null || true

# Copie depuis repo/docker-images vers work/iso/docker-images
cp -f "$SRC_DIR"/*.tar "$TARGET_DIR"/ 2>/dev/null || true

echo "=== Splitting docker tar files > 4GiB for ISO9660 ==="
SPLIT_SIZE="3900m"

find "$TARGET_DIR" -maxdepth 1 -type f -name "*.tar" -size +4096M -print0 | while IFS= read -r -d '' tar; do
  echo "[*] Splitting: $tar"
  split -b "$SPLIT_SIZE" -d -a 3 "$tar" "${tar}.part-"
  rm -f "$tar"
done

echo "=== Done ==="
ls -lh "$TARGET_DIR" || true
