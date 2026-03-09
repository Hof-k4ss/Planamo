#!/bin/bash
set -e

echo "=== Installing PLANAMO XFCE menu structure ==="

mkdir -p /etc/xdg/menus

# Écriture du menu XML avec les balises Name correctes
printf '%s\n' '<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN"
"http://www.freedesktop.org/standards/menu-spec/1.0/menu.dtd">
<Menu>
  <Name>Xfce</Name>

  <Menu>
    <Name>PLANAMO</Name>
    <Directory>planamo.directory</Directory>

    <Menu>
      <Name>Mobile Acquisition</Name>
      <Directory>planamo-mobile-acq.directory</Directory>
      <Include><Category>X-PLANAMO-MOBILE-ACQ</Category></Include>
    </Menu>

    <Menu>
      <Name>Mobile Analysis</Name>
      <Directory>planamo-mobile-analysis.directory</Directory>
      <Include><Category>X-PLANAMO-MOBILE-ANALYSIS</Category></Include>
    </Menu>

    <Menu>
      <Name>Malware &amp; Reverse Engineering</Name>
      <Directory>planamo-malware.directory</Directory>
      <Include><Category>X-PLANAMO-MALWARE</Category></Include>
    </Menu>

    <Menu>
      <Name>Disk &amp; Filesystem</Name>
      <Directory>planamo-disk.directory</Directory>
      <Include><Category>X-PLANAMO-DISK</Category></Include>
    </Menu>

    <Menu>
      <Name>Memory</Name>
      <Directory>planamo-memory.directory</Directory>
      <Include><Category>X-PLANAMO-MEMORY</Category></Include>
    </Menu>

    <Menu>
      <Name>Network</Name>
      <Directory>planamo-network.directory</Directory>
      <Include><Category>X-PLANAMO-NETWORK</Category></Include>
    </Menu>

    <Menu>
      <Name>OSINT</Name>
      <Directory>planamo-osint.directory</Directory>
      <Include><Category>X-PLANAMO-OSINT</Category></Include>
    </Menu>

    <Menu>
      <Name>Development</Name>
      <Directory>planamo-dev.directory</Directory>
      <Include><Category>X-PLANAMO-DEV</Category></Include>
    </Menu>

    <Menu>
      <Name>Docker &amp; Services</Name>
      <Directory>planamo-docker.directory</Directory>
      <Include><Category>X-PLANAMO-DOCKER</Category></Include>
    </Menu>

  </Menu>
</Menu>' > /etc/xdg/menus/xfce-applications.menu

mkdir -p /usr/share/desktop-directories

cat > /usr/share/desktop-directories/planamo.directory << 'DEOF'
[Desktop Entry]
<Name>PLANAMO</Name>
Icon=folder
Type=Directory
DEOF

for x in mobile-acq mobile-analysis malware disk memory network osint dev docker; do
  printf '[Desktop Entry]\n<Name>PLANAMO - %s</Name>\nIcon=folder\nType=Directory\n' "$x" \
    > "/usr/share/desktop-directories/planamo-$x.directory"
done

echo "=== PLANAMO menu installed ==="
