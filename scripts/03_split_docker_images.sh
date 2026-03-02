#!/bin/bash
set -euo pipefail

DOCKER_DIR="$(pwd)/work/iso/docker-images"
SPLIT_SIZE="3900M"

echo "=== Checking docker images for >4GB files ==="

[ -d "$DOCKER_DIR" ] || {
  echo "[!] Directory not found: $DOCKER_DIR (skip)"
  exit 0
}

shopt -s nullglob

for tar in "$DOCKER_DIR"/*.tar; do
  size=$(stat -c%s "$tar")

  if [ "$size" -gt 4294967295 ]; then
    base="${tar%.tar}"

    # Si déjà splitté → skip
    if compgen -G "${base}.tar.part-[0-9][0-9][0-9]" > /dev/null; then
      echo "[=] Already split: $tar"
      continue
    fi

    echo "[!] Splitting $tar"
    split -b "$SPLIT_SIZE" -d -a 3 "$tar" "${base}.tar.part-"
    rm -f "$tar"
    echo "[✓] Split complete"
  else
    echo "[OK] $tar"
  fi
done

echo "=== Docker image check complete ==="
