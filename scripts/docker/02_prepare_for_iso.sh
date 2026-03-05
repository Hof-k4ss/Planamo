#!/bin/bash
set -euo pipefail

WORKDIR="$(pwd)/work"
TARGET_DIR="$WORKDIR/iso/docker-images"
SRC_DIR="$(pwd)/docker-images"
SPLIT_SIZE="3900M"

echo "=== Prepare docker images for ISO ==="
echo "[*] Source: $SRC_DIR"
echo "[*] Target: $TARGET_DIR"

[ -d "$SRC_DIR" ] || {
  echo "[!] Source directory not found: $SRC_DIR"
  exit 1
}

mkdir -p "$TARGET_DIR"

# Nettoie l'ancien contenu pour éviter les restes
rm -f "$TARGET_DIR"/*.tar "$TARGET_DIR"/*.tar.part-* 2>/dev/null || true

# Copie depuis docker-images/ vers work/iso/docker-images/
shopt -s nullglob
tars=("$SRC_DIR"/*.tar)

if [ ${#tars[@]} -eq 0 ]; then
  echo "[!] No .tar files found in $SRC_DIR"
  exit 1
fi

for tar in "${tars[@]}"; do
  echo "[*] Copying: $(basename "$tar")"
  cp -f "$tar" "$TARGET_DIR/"
done

echo ""
echo "=== Splitting docker tar files > 4GiB for ISO9660 ==="

shopt -s nullglob
for tar in "$TARGET_DIR"/*.tar; do
  size=$(stat -c%s "$tar")

  if [ "$size" -gt 4294967295 ]; then
    base="${tar%.tar}"

    # Déjà splitté → skip
    if compgen -G "${base}.tar.part-[0-9][0-9][0-9]" > /dev/null; then
      echo "[=] Already split: $(basename "$tar") → skip"
      continue
    fi

    echo "[!] Splitting: $(basename "$tar") ($(numfmt --to=iec "$size"))"
    split -b "$SPLIT_SIZE" -d -a 3 "$tar" "${base}.tar.part-"
    rm -f "$tar"
    echo "[✓] Split complete: $(basename "$base").tar.part-*"
  else
    echo "[OK] $(basename "$tar") ($(numfmt --to=iec "$size"))"
  fi
done

echo ""
echo "=== Done ==="
ls -lh "$TARGET_DIR"
