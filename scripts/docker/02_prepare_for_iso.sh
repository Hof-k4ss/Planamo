#!/bin/bash
set -e

WORKDIR="$(pwd)/work"
ISOROOT="$WORKDIR/iso"

echo "=== Copying Docker images into ISO (outside squashfs) ==="

sudo mkdir -p "$ISOROOT/docker-images"
sudo cp docker-images/*.tar "$ISOROOT/docker-images/"

echo "=== Docker images copied into ISO root ==="
