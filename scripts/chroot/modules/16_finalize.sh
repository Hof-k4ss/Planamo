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

for i in $(seq 1 30); do
    pgrep xfdesktop >/dev/null 2>&1 && break
    sleep 0.5
done

xfconf-query -c xfce4-desktop \
  -p /backdrop/screen0/monitor0/workspace0/last-image \
  --create -t string -s "$WALL" 2>/dev/null || true

xfdesktop --reload 2>/dev/null || true
EOF
chmod +x /usr/local/bin/planamo-set-wallpaper

mkdir -p /etc/xdg/autostart
cat > /etc/xdg/autostart/planamo-wallpaper.desktop << 'EOF'
[Desktop Entry]
Type=Application
Exec=/usr/local/bin/planamo-set-wallpaper
OnlyShowIn=XFCE;
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

    # marquage local XFCE (clé)
    python3 - <<PY
import os
try:
    os.setxattr(r"$file", b"user.xdg.origin.url", b"")
except Exception:
    pass
PY
}

# Documentation
cat > "$HOME_DIR/Desktop/PLANAMO-Documentation.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Name=PLANAMO Documentation
Exec=/usr/local/bin/rtfm
Icon=help-browser
Type=Application
EOF
make_trusted_desktop "$HOME_DIR/Desktop/PLANAMO-Documentation.desktop"

# Install
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
ln -s /etc/machine-id /var/lib/dbus/machine-id

sync

echo "=== Finalize done ==="
