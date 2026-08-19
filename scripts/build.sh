#!/bin/bash
set -e

LOGDIR="$(pwd)/logs"
mkdir -p "$LOGDIR"
BUILD_LOG="$LOGDIR/build_$(date +%Y%m%d_%H%M%S).log"

# Redirige stdout + stderr vers le log ET le terminal
exec > >(tee -a "$BUILD_LOG") 2>&1

echo "======================================="
echo "   PLANAMO BUILD START"
echo "   $(date '+%Y-%m-%d %H:%M:%S')"
echo "   Log : $BUILD_LOG"
echo "======================================="

run_step() {
  local label="$1"
  local cmd="$2"
  local start

  echo ""
  echo "--- [$label] START $(date '+%H:%M:%S') ---"
  start=$(date +%s)

  bash $cmd

  local duration=$(( $(date +%s) - start ))
  echo "--- [$label] DONE in ${duration}s ---"
}

run_step "01 fetch docker images"    "scripts/docker/01_fetch_images.sh"
run_step "02 debootstrap"            "scripts/01_debootstrap.sh"
run_step "03 chroot setup"           "scripts/02_chroot_setup.sh"
run_step "04 prepare docker for iso" "scripts/docker/02_prepare_for_iso.sh"
run_step "05 make squashfs"          "scripts/03_make_squashfs.sh"
run_step "06 build iso"              "scripts/04_make_iso.sh"

echo ""
echo "======================================="
echo "   PLANAMO FULL ISO BUILT"
echo "   $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================="
