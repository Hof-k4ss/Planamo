#!/bin/bash
set -e

WORKDIR="$(pwd)/work"
ROOTFS="$WORKDIR/planamo-root"

echo "=== Copying Docker images into ISO rootfs ==="

sudo mkdir -p "$ROOTFS/opt/planamo/docker-images"
sudo cp docker-images/*.tar "$ROOTFS/opt/planamo/docker-images/"

echo "=== Docker images copied ==="
