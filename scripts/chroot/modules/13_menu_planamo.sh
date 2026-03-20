#!/bin/bash
set -e

echo "=== Installing PLANAMO XFCE menu structure ==="

mkdir -p /etc/xdg/menus
mkdir -p /usr/share/desktop-directories

cat > /etc/xdg/menus/xfce-applications.menu << 'XMLEOF'
<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN"
  "http://www.freedesktop.org/standards/menu-spec/menu-1.0.dtd">
<Menu>
  <Name>Xfce</Name>
  <DefaultAppDirs/>
  <DefaultDirectoryDirs/>
  <DefaultMergeDirs/>

  <!-- Menu PLANAMO custom -->
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
      <Name>Malware and Reverse Engineering</Name>
      <Directory>planamo-malware.directory</Directory>
      <Include><Category>X-PLANAMO-MALWARE</Category></Include>
    </Menu>

    <Menu>
      <Name>Disk and Filesystem</Name>
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
      <Name>Docker and Services</Name>
      <Directory>planamo-docker.directory</Directory>
      <Include><Category>X-PLANAMO-DOCKER</Category></Include>
    </Menu>

  </Menu>

  <!-- Menus XFCE standard -->
  <Menu>
    <Name>Accessories</Name>
    <Directory>xfce-accessories.directory</Directory>
    <Include><Category>Utility</Category></Include>
    <Exclude><Category>System</Category></Exclude>
  </Menu>

  <Menu>
    <Name>Graphics</Name>
    <Directory>xfce-graphics.directory</Directory>
    <Include><Category>Graphics</Category></Include>
  </Menu>

  <Menu>
    <Name>Internet</Name>
    <Directory>xfce-internet.directory</Directory>
    <Include>
      <Category>Network</Category>
      <Category>WebBrowser</Category>
    </Include>
  </Menu>

  <Menu>
    <Name>Office</Name>
    <Directory>xfce-office.directory</Directory>
    <Include><Category>Office</Category></Include>
  </Menu>

  <Menu>
    <Name>Multimedia</Name>
    <Directory>xfce-multimedia.directory</Directory>
    <Include>
      <Category>Audio</Category>
      <Category>Video</Category>
    </Include>
  </Menu>

  <Menu>
    <Name>System</Name>
    <Directory>xfce-system.directory</Directory>
    <Include>
      <Category>System</Category>
      <Category>Settings</Category>
      <Category>TerminalEmulator</Category>
    </Include>
  </Menu>

</Menu>
XMLEOF

cat > /usr/share/desktop-directories/planamo.directory << 'EOF'
[Desktop Entry]
<Name>PLANAMO</Name>
<Icon>security-high</Icon>
Type=Directory
EOF

cat > /usr/share/desktop-directories/planamo-mobile-acq.directory << 'EOF'
[Desktop Entry]
<Name>Mobile Acquisition</Name>
<Icon>phone</Icon>
Type=Directory
EOF

cat > /usr/share/desktop-directories/planamo-mobile-analysis.directory << 'EOF'
[Desktop Entry]
<Name>Mobile Analysis</Name>
<Icon>phone</Icon>
Type=Directory
EOF

cat > /usr/share/desktop-directories/planamo-malware.directory << 'EOF'
[Desktop Entry]
<Name>Malware and RE</Name>
<Icon>dialog-warning</Icon>
Type=Directory
EOF

cat > /usr/share/desktop-directories/planamo-disk.directory << 'EOF'
[Desktop Entry]
<Name>Disk and Filesystem</Name>
<Icon>drive-harddisk</Icon>
Type=Directory
EOF

cat > /usr/share/desktop-directories/planamo-memory.directory << 'EOF'
[Desktop Entry]
<Name>Memory</Name>
<Icon>media-flash</Icon>
Type=Directory
EOF

cat > /usr/share/desktop-directories/planamo-network.directory << 'EOF'
[Desktop Entry]
<Name>Network</Name>
<Icon>network-wired</Icon>
Type=Directory
EOF

cat > /usr/share/desktop-directories/planamo-osint.directory << 'EOF'
[Desktop Entry]
<Name>OSINT</Name>
<Icon>system-search</Icon>
Type=Directory
EOF

cat > /usr/share/desktop-directories/planamo-dev.directory << 'EOF'
[Desktop Entry]
<Name>Development</Name>
<Icon>applications-development</Icon>
Type=Directory
EOF

cat > /usr/share/desktop-directories/planamo-docker.directory << 'EOF'
[Desktop Entry]
<Name>Docker and Services</Name>
<Icon>application-x-executable</Icon>
Type=Directory
EOF

# Configurer xfce4-panel pour utiliser notre menu custom
mkdir -p /etc/xdg/xfce4/xfconf/xfce-perchannel-xml
cat > /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="plugins" type="empty">
    <property name="plugin-1" type="string" value="applicationsmenu">
      <property name="menu-file" type="string" value="/etc/xdg/menus/xfce-applications.menu"/>
      <property name="custom-menu" type="bool" value="true"/>
      <property name="show-button-title" type="bool" value="true"/>
      <property name="button-title" type="string" value="Applications"/>
    </property>
  </property>
</channel>
EOF

echo "=== PLANAMO menu installed ==="
