#!/bin/bash
set -e

echo "=== Final system configuration ==="

USER_NAME="analyste"
HOME_DIR="/home/$USER_NAME"
PIC_DIR="$HOME_DIR/Pictures"
XFCONF_DIR="$HOME_DIR/.config/xfce4/xfconf/xfce-perchannel-xml"

# =============================================================================
# HOSTNAME
# =============================================================================
echo planamo > /etc/hostname

cat > /etc/hosts << EOF
127.0.0.1   localhost
127.0.1.1   planamo
::1         localhost ip6-localhost ip6-loopback
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
EOF

# =============================================================================
# NETWORK
# =============================================================================
systemctl enable NetworkManager || true

mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/10-globally-managed-devices.conf << 'EOF'
[keyfile]
unmanaged-devices=none
EOF

# =============================================================================
# LIGHTDM
# =============================================================================
mkdir -p /etc/lightdm
cat > /etc/lightdm/lightdm.conf << EOF
[Seat:*]
autologin-user=$USER_NAME
autologin-user-timeout=0
user-session=xfce
greeter-session=lightdm-gtk-greeter
EOF

cat > "$HOME_DIR/.dmrc" << 'EOF'
[Desktop]
Session=xfce
EOF
chown "$USER_NAME:$USER_NAME" "$HOME_DIR/.dmrc" || true

if [ ! -f /usr/share/xsessions/xfce.desktop ]; then
    mkdir -p /usr/share/xsessions
    cat > /usr/share/xsessions/xfce.desktop << 'EOF'
[Desktop Entry]
Name=Xfce Session
Comment=Use this session to run Xfce as your desktop environment
Exec=startxfce4
Icon=
Type=Application
EOF
fi

# =============================================================================
# IMAGES
# =============================================================================
SRC_DIR="/usr/share/planamo"
mkdir -p "$PIC_DIR"
cp -f "$SRC_DIR/"*.png "$PIC_DIR/" 2>/dev/null || true
chown -R "$USER_NAME:$USER_NAME" "$PIC_DIR" || true

# =============================================================================
# WALLPAPER
# =============================================================================
cat > /usr/local/bin/planamo-set-wallpaper << 'EOF'
#!/bin/bash
WALL="/home/analyste/Pictures/wallpaper_sim.png"
[ -f "$WALL" ] || exit 0

for i in $(seq 1 40); do
    pgrep -x xfdesktop >/dev/null 2>&1 && break
    sleep 0.5
done
sleep 1

for monitor in $(xrandr --query 2>/dev/null | awk '/ connected/{print $1}'); do
    xfconf-query -c xfce4-desktop \
      -p "/backdrop/screen0/monitor${monitor}/workspace0/last-image" \
      --create -t string -s "$WALL" 2>/dev/null || true

    xfconf-query -c xfce4-desktop \
      -p "/backdrop/screen0/monitor${monitor}/workspace0/image-style" \
      --create -t int -s 5 2>/dev/null || true
done

xfconf-query -c xfce4-desktop \
  -p "/backdrop/screen0/monitor0/workspace0/last-image" \
  --create -t string -s "$WALL" 2>/dev/null || true

xfconf-query -c xfce4-desktop \
  -p "/backdrop/screen0/monitor0/workspace0/image-style" \
  --create -t int -s 5 2>/dev/null || true

xfdesktop --reload 2>/dev/null || true
EOF
chmod +x /usr/local/bin/planamo-set-wallpaper

mkdir -p /etc/xdg/autostart
cat > /etc/xdg/autostart/planamo-wallpaper.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=PLANAMO Wallpaper
Exec=/usr/local/bin/planamo-set-wallpaper
OnlyShowIn=XFCE;
Terminal=false
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF

# =============================================================================
# XFCE HELPERS — TERMINATOR + THUNAR + FIREFOX
# =============================================================================
mkdir -p /usr/share/xfce4/helpers
mkdir -p /etc/xdg/xfce4
mkdir -p "$HOME_DIR/.config/xfce4"
mkdir -p "$XFCONF_DIR"

cat > /usr/share/xfce4/helpers/custom-TerminalEmulator.desktop << 'EOF'
[Desktop Entry]
NoDisplay=true
Version=0.9.0
Type=X-XFCE-Helper
X-XFCE-Binaries=terminator;xfce4-terminal;xterm;
X-XFCE-Category=TerminalEmulator
X-XFCE-CommandsWithParameter=terminator -x "%s";
Icon=terminator
Name=Terminator
X-XFCE-Commands=terminator;
EOF

cat > /usr/share/xfce4/helpers/custom-FileManager.desktop << 'EOF'
[Desktop Entry]
NoDisplay=true
Version=0.9.0
Type=X-XFCE-Helper
X-XFCE-Binaries=thunar;
X-XFCE-Category=FileManager
X-XFCE-CommandsWithParameter=thunar "%s";
Icon=thunar
Name=Thunar
X-XFCE-Commands=thunar;
EOF

cat > /usr/share/xfce4/helpers/custom-WebBrowser.desktop << 'EOF'
[Desktop Entry]
NoDisplay=true
Version=0.9.0
Type=X-XFCE-Helper
X-XFCE-Binaries=firefox;
X-XFCE-Category=WebBrowser
X-XFCE-CommandsWithParameter=firefox "%s";
Icon=firefox
Name=Firefox
X-XFCE-Commands=firefox;
EOF

cat > /etc/xdg/xfce4/helpers.rc << 'EOF'
WebBrowser=custom-WebBrowser
TerminalEmulator=custom-TerminalEmulator
FileManager=custom-FileManager
EOF

cat > "$HOME_DIR/.config/xfce4/helpers.rc" << 'EOF'
WebBrowser=custom-WebBrowser
TerminalEmulator=custom-TerminalEmulator
FileManager=custom-FileManager
EOF

cat > "$XFCONF_DIR/xfce4-mime-settings.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-mime-settings" version="1.0">
  <property name="default-mail-reader" type="string" value=""/>
  <property name="default-web-browser" type="string" value="firefox"/>
  <property name="default-file-manager" type="string" value="thunar"/>
  <property name="default-terminal" type="string" value="terminator"/>
</channel>
EOF

# =============================================================================
# LOCK SCREEN / SCREENSAVER
# =============================================================================
mkdir -p "$XFCONF_DIR"

cat > "$XFCONF_DIR/xfce4-screensaver.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-screensaver" version="1.0">
  <property name="saver" type="empty">
    <property name="enabled" type="bool" value="true"/>
    <property name="mode" type="int" value="0"/>
    <property name="idle-activation-enabled" type="bool" value="false"/>
  </property>
  <property name="lock" type="empty">
    <property name="enabled" type="bool" value="true"/>
    <property name="saver-activation" type="bool" value="false"/>
  </property>
  <property name="background" type="empty">
    <property name="type" type="string" value="image"/>
    <property name="image" type="string" value="/home/analyste/Pictures/avatar_sim.png"/>
    <property name="mode" type="string" value="scaled"/>
  </property>
</channel>
EOF

cat > "$XFCONF_DIR/xfce4-power-manager.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-power-manager" version="1.0">
  <property name="xfce4-power-manager" type="empty">
    <property name="dpms-enabled" type="bool" value="false"/>
    <property name="blank-on-ac" type="int" value="0"/>
    <property name="dpms-on-ac-sleep" type="uint" value="0"/>
    <property name="dpms-on-ac-off" type="uint" value="0"/>
    <property name="lid-action-on-ac" type="uint" value="0"/>
    <property name="lid-action-on-battery" type="uint" value="0"/>
    <property name="sleep-button-action" type="uint" value="0"/>
    <property name="hibernate-button-action" type="uint" value="0"/>
  </property>
</channel>
EOF

# =============================================================================
# DESKTOP ICONS (FIX DEFINITIF)
# =============================================================================
echo "=== Desktop icons ==="

mkdir -p /etc/skel/Desktop
mkdir -p "$HOME_DIR/Desktop"

make_trusted_desktop() {
    local file="$1"

    chmod 0755 "$file" 2>/dev/null || true

    python3 - <<PY
import os
try:
    os.setxattr(r"$file", b"user.xdg.origin.url", b"")
except Exception:
    pass
PY
}

cat > "$HOME_DIR/Desktop/PLANAMO-Documentation.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Name=PLANAMO Documentation
Exec=/usr/local/bin/rtfm
Icon=help-browser
Type=Application
EOF
make_trusted_desktop "$HOME_DIR/Desktop/PLANAMO-Documentation.desktop"

cat > "$HOME_DIR/Desktop/Install-PLANAMO.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Name=Install PLANAMO
Exec=xterm -e "sudo /usr/local/bin/planamo-install"
Icon=system-software-install
Type=Application
EOF
make_trusted_desktop "$HOME_DIR/Desktop/Install-PLANAMO.desktop"

cp "$HOME_DIR/Desktop/"*.desktop /etc/skel/Desktop/
chmod 0755 /etc/skel/Desktop/*.desktop

chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR/Desktop"

# =============================================================================
# TRUST ICONS (AUTOSTART)
# =============================================================================
cat > /usr/local/bin/planamo-trust-icons << 'EOF'
#!/bin/bash

for i in $(seq 1 60); do
    gio info "$HOME/Desktop" >/dev/null 2>&1 && break
    sleep 0.5
done

for f in "$HOME/Desktop/"*.desktop; do
    [ -f "$f" ] || continue

    chmod 0755 "$f"

    python3 - <<PY
import os
try:
    os.setxattr(r"$f", b"user.xdg.origin.url", b"")
except:
    pass
PY

    gio set "$f" metadata::trusted true 2>/dev/null || true
    gio set "$f" metadata::xfce-exe-checksum "$(sha256sum "$f" | awk '{print $1}')" 2>/dev/null || true
done

xfdesktop --reload
EOF

chmod +x /usr/local/bin/planamo-trust-icons

cat > /etc/xdg/autostart/planamo-trust-icons.desktop << 'EOF'
[Desktop Entry]
Type=Application
Exec=/usr/local/bin/planamo-trust-icons
OnlyShowIn=XFCE;
Terminal=false
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF

# =============================================================================
# AVATAR
# =============================================================================
if [ -f "$PIC_DIR/avatar_sim.png" ]; then
    mkdir -p /var/lib/AccountsService/icons /var/lib/AccountsService/users
    cp -f "$PIC_DIR/avatar_sim.png" "/var/lib/AccountsService/icons/$USER_NAME"
    cat > "/var/lib/AccountsService/users/$USER_NAME" << EOF
[User]
Icon=/var/lib/AccountsService/icons/$USER_NAME
EOF
fi

# =============================================================================
# XFCE POSTLOGIN
# =============================================================================
cat > /usr/local/bin/planamo-xfce-postlogin << 'EOF'
#!/bin/bash

for i in $(seq 1 40); do
    pgrep -x xfconfd >/dev/null 2>&1 && break
    sleep 0.5
done
sleep 1

/usr/local/bin/planamo-set-wallpaper 2>/dev/null || true

xfconf-query -c exo -p /preferred-applications/WebBrowser/command \
  --create -t string -s "firefox" 2>/dev/null || true
xfconf-query -c exo -p /preferred-applications/WebBrowser/parameter \
  --create -t string -s "%s" 2>/dev/null || true

xfconf-query -c exo -p /preferred-applications/TerminalEmulator/command \
  --create -t string -s "terminator" 2>/dev/null || true
xfconf-query -c exo -p /preferred-applications/TerminalEmulator/parameter \
  --create -t string -s "-x" 2>/dev/null || true

xfconf-query -c exo -p /preferred-applications/FileManager/command \
  --create -t string -s "thunar" 2>/dev/null || true

xfconf-query -c xfce4-mime-settings -p /default-web-browser \
  --create -t string -s "firefox" 2>/dev/null || true
xfconf-query -c xfce4-mime-settings -p /default-terminal \
  --create -t string -s "terminator" 2>/dev/null || true
xfconf-query -c xfce4-mime-settings -p /default-file-manager \
  --create -t string -s "thunar" 2>/dev/null || true
EOF
chmod +x /usr/local/bin/planamo-xfce-postlogin

cat > /etc/xdg/autostart/planamo-xfce-postlogin.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=PLANAMO XFCE Defaults
Exec=/usr/local/bin/planamo-xfce-postlogin
OnlyShowIn=XFCE;
Terminal=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=3
NoDisplay=true
EOF

# =============================================================================
# CLEAN ISO
# =============================================================================
echo "=== Cleanup ==="

apt-get autoremove -y || true
apt-get clean || true
rm -rf /var/lib/apt/lists/*

rm -rf /tmp/*
rm -rf /var/tmp/*

find /var/log -type f -exec truncate -s 0 {} \; 2>/dev/null || true

rm -f /root/.bash_history
rm -f /home/analyste/.bash_history

truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id
ln -sf /etc/machine-id /var/lib/dbus/machine-id

chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR" 2>/dev/null || true

sync

echo "=== Finalize done ==="
