#!/bin/bash
set -e

echo "=== PLANAMO CHROOT START ==="

bash /root/modules/01_base_system.sh
bash /root/modules/02_user.sh
bash /root/modules/03_tools_mobile.sh
bash /root/modules/04_tools_network.sh
bash /root/modules/05_tools_disk.sh
bash /root/modules/06_tools_malware.sh
bash /root/modules/07_tools_osint.sh
bash /root/modules/08_menu_structure.sh
bash /root/modules/09_documentation.sh
bash /root/modules/10_finalize.sh
bash /root/modules/11_dev_tools.sh
bash /root/modules/12_tools_nonapt.sh
bash /root/modules/13_tools_custom.sh
bash /root/modules/14_docker_loader.sh
bash /root/modules/15_docker_runtime.sh
bash /root/modules/16_live_autostart.sh

echo "=== PLANAMO CHROOT DONE ==="
