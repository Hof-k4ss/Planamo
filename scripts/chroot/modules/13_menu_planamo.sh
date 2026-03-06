#!/bin/bash
set -e

echo "=== Installing PLANAMO XFCE menu structure ==="

mkdir -p /etc/xdg/menus
cat > /etc/xdg/menus/xfce-applications.menu <<'EOF'
<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN"
"http://www.freedesktop.org/standards/menu-spec/1.0/menu.dtd">
<Menu>
  <Name>Xfce</Name>

  <Menu>
    <Name>PLANAMO</Name>
    <Directory>planamo.directory</Directory>

    <Menu><Name>Mobile Acquisition</Name>
      <Directory>planamo-mobile-acq.directory</Directory>
      <Include><Category>X-PLANAMO-MOBILE-ACQ</Category></Include>
    </Menu>

    <Menu><Name>Mobile Analysis</Name>
      <Directory>planamo-mobile-analysis.directory</Directory>
      <Include><Category>X-PLANAMO-MOBILE-ANALYSIS</Category></Include>
    </Menu>

    <Menu><Name>Malware &amp; Reverse Engineering</Name>
      <Directory>planamo-malware.directory</Directory>
      <Include><Category>X-PLANAMO-MALWARE</Category></Include>
    </Menu>

    <Menu><Name>Disk &amp; Filesystem</Name>
      <Directory>planamo-disk.directory</Directory>
      <Include><Category>X-PLANAMO-DISK</Category></Include>
    </Menu>

    <Menu><Name>Memory</Name>
      <Directory>planamo-memory.directory</Directory>
      <Include><Category>X-PLANAMO-MEMORY</Category></Include>
    </Menu>

    <Menu><Name>Network</Name>
      <Directory>planamo-network.directory</Directory>
      <Include><Category>X-PLANAMO-NETWORK</Category></Include>
    </Menu>

    <Menu><Name>OSINT</Name>
      <Directory>planamo-osint.directory</Directory>
      <Include><Category>X-PLANAMO-OSINT</Category></Include>
    </Menu>

    <Menu><Name>Development</Name>
      <Directory>planamo-dev.directory</Directory>
      <Include><Category>X-PLANAMO-DEV</Category></Include>
    </Menu>

    <Menu><Name>Docker &amp; Services</Name>
      <Directory>planamo-docker.directory</Directory>
      <Include><Category>X-PLANAMO-DOCKER</Category></Include>
    </Menu>

  </Menu>
</Menu>
EOF

mkdir -p /usr/share/desktop-directories
cat > /usr/share/desktop-directories/planamo.directory <<'EOF'
[Desktop Entry]
Name=PLANAMO
Icon=folder
Type=Directory
EOF

for x in mobile-acq mobile-analysis malware disk memory network osint dev docker; do
cat > "/usr/share/desktop-directories/planamo-$x.directory" <<EOF
[Desktop Entry]
Name=PLANAMO - $x
Icon=folder
Type=Directory
EOF
done

echo "=== PLANAMO menu installed ==="
