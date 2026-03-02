#!/bin/bash
set -e

echo "======================================="
echo "      PLANAMO CHROOT INSTALL START     "
echo "======================================="

bash /root/modules/01_base_system.sh
bash /root/modules/02_user.sh

bash /root/modules/03_tools_mobile.sh
bash /root/modules/04_tools_network.sh
bash /root/modules/05_tools_disk.sh
bash /root/modules/06_tools_malware.sh
bash /root/modules/07_tools_osint.sh

bash /root/modules/08_dev_tools.sh
bash /root/modules/09_tools_nonapt.sh
bash /root/modules/10_tools_custom.sh

bash /root/modules/11_docker_load.sh

bash /root/modules/12_menu_structure.sh
bash /root/modules/13_documentation.sh

bash /root/modules/14_finalize.sh

echo "======================================="
echo "       PLANAMO CHROOT INSTALL DONE     "
echo "======================================="
