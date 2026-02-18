#!/bin/bash
set -e

# 1. Docker images FULL offline
bash scripts/docker/01_fetch_images.sh

# 2. Base system
bash scripts/01_debootstrap.sh
bash scripts/02_chroot_setup.sh

# 3. Inject docker images into rootfs
bash scripts/docker/02_prepare_for_iso.sh

# 4. Make squashfs
bash scripts/03_make_squashfs.sh

# 5. Build ISO
bash scripts/04_make_iso.sh

echo "=== PLANAMO FULL ISO BUILT ==="
