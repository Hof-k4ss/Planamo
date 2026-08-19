#!/bin/bash
set -e

echo "======================================="
echo "       PLANAMO CHROOT INSTALL           "
echo "======================================="

cd /root/modules

for f in \
  01_base_system.sh \
  02_user.sh \
  03_tools_mobile.sh \
  04_tools_network.sh \
  05_tools_disk.sh \
  06_tools_malware.sh \
  07_tools_osint.sh \
  08_tools_dev.sh \
  09_tools_nonapt.sh \
  10_tools_custom.sh \
  11_docker_load.sh \
  12_menu_structure.sh \
  13_menu_planamo.sh \
  14_documentation.sh \
  15_installer.sh \
  16_finalize.sh
do
  echo "=== Running $f ==="
  bash "$f"
done

echo "======================================="
echo "       PLANAMO CHROOT INSTALL DONE      "
echo "======================================="
