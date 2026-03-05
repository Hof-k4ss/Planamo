#!/bin/bash
set -e

echo "=== Final system configuration ==="

echo planamo > /etc/hostname

cat <<EOF > /etc/hosts
127.0.0.1   localhost
127.0.1.1   planamo

::1         localhost ip6-localhost ip6-loopback
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
EOF

echo "=== Network auto configuration ==="
systemctl enable NetworkManager || true

mkdir -p /etc/NetworkManager/conf.d
cat <<EOF > /etc/NetworkManager/conf.d/10-globally-managed-devices.conf
[keyfile]
unmanaged-devices=none
EOF

# nmcli ne marche pas en chroot (pas de dbus) => on ignore
nmcli connection add type ethernet ifname "*" con-name "Wired connection" autoconnect yes >/dev/null 2>&1 || true

echo "=== PLANAMO UI: wallpaper + avatar ==="

USER_NAME="analyste"
HOME_DIR="/home/$USER_NAME"
PIC_DIR="$HOME_DIR/Pictures"

SRC_DIR="/usr/share/planamo"
WALL_SRC="$SRC_DIR/patch_sim.png"
AVATAR_SRC="$SRC_DIR/logo_sim.png"

mkdir -p "$PIC_DIR"

# Copier dans ~/Pictures
if [ -f "$WALL_SRC" ]; then
  cp -f "$WALL_SRC" "$PIC_DIR/patch_sim.png"
fi
if [ -f "$AVATAR_SRC" ]; then
  cp -f "$AVATAR_SRC" "$PIC_DIR/logo_sim.png"
fi
chown -R "$USER_NAME":"$USER_NAME" "$PIC_DIR" || true

# Avatar via AccountsService
AVATAR="$PIC_DIR/logo_sim.png"
if [ -f "$AVATAR" ]; then
  mkdir -p /var/lib/AccountsService/icons /var/lib/AccountsService/users
  cp -f "$AVATAR" "/var/lib/AccountsService/icons/$USER_NAME"
  cat > "/var/lib/AccountsService/users/$USER_NAME" <<EOF
[User]
Icon=/var/lib/AccountsService/icons/$USER_NAME
EOF
fi

echo "=== PLANAMO UI applied ==="
echo "=== First-login actions (wallpaper + desktop icons trusted) ==="

# Launcher système documentation (fiable)
cat > /usr/share/applications/planamo-documentation.desktop <<'EOF'
[Desktop Entry]
Name=PLANAMO Documentation
Exec=exo-open file:///opt/planamo/docs/site/index.html
Icon=help-browser
Terminal=false
Type=Application
Categories=Utility;
OnlyShowIn=XFCE;
EOF
chmod 644 /usr/share/applications/planamo-documentation.desktop

# Launcher système PLANAMO Tools (ouvre les dossiers par thèmes)
cat > /usr/share/applications/planamo-tools.desktop <<'EOF'
[Desktop Entry]
Name=PLANAMO Tools
Exec=exo-open --launch FileManager "$HOME/PLANAMO-Tools"
Icon=folder
Terminal=false
Type=Application
Categories=Utility;
OnlyShowIn=XFCE;
EOF
chmod 644 /usr/share/applications/planamo-tools.desktop

# Script de post-login (XFCE) : applique wallpaper + place icônes desktop TRUSTED
cat > /usr/local/bin/planamo-first-login <<'EOF'
#!/bin/bash
set -e

USER_NAME="analyste"
HOME_DIR="/home/${USER_NAME}"
DESK="${HOME_DIR}/Desktop"
WALL="${HOME_DIR}/Pictures/patch_sim.png"
[ -f "$WALL" ] || WALL="/usr/share/planamo/patch_sim.png"

mkdir -p "$DESK"

# 1) Fond d'écran XFCE : attendre que xfdesktop/xfconf soient prêts
for i in {1..40}; do
  if command -v xfconf-query >/dev/null 2>&1 && xfconf-query -c xfce4-desktop -l >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if [ -f "$WALL" ] && command -v xfconf-query >/dev/null 2>&1; then
  xfconf-query -c xfce4-desktop -l | grep -E 'last-image$' | while read -r prop; do
    xfconf-query -c xfce4-desktop -p "$prop" -s "$WALL" >/dev/null 2>&1 || true
  done

  # 2 = Stretched (étiré)
  xfconf-query -c xfce4-desktop -l | grep -E 'image-style$' | while read -r prop; do
    xfconf-query -c xfce4-desktop -p "$prop" -s 2 >/dev/null 2>&1 || true
  done

  command -v xfdesktop >/dev/null 2>&1 && xfdesktop --reload >/dev/null 2>&1 || true
fi

# 2) Icônes Desktop (copie) + trusted via gio
cp -f /usr/share/applications/planamo-documentation.desktop "$DESK/PLANAMO-Documentation.desktop" || true
cp -f /usr/share/applications/planamo-tools.desktop "$DESK/PLANAMO-Tools.desktop" || true
chown "${USER_NAME}:${USER_NAME}" "$DESK/"*.desktop 2>/dev/null || true
chmod 755 "$DESK/"*.desktop 2>/dev/null || true

# Trust XFCE launcher
if command -v gio >/dev/null 2>&1; then
  gio set "$DESK/PLANAMO-Documentation.desktop" metadata::trusted true >/dev/null 2>&1 || true
  gio set "$DESK/PLANAMO-Tools.desktop" metadata::trusted true >/dev/null 2>&1 || true
fi

exit 0
EOF
chmod +x /usr/local/bin/planamo-first-login

# Autostart XFCE (global)
mkdir -p /etc/xdg/autostart
cat > /etc/xdg/autostart/planamo-first-login.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=PLANAMO First Login
Exec=/usr/local/bin/planamo-first-login
Terminal=false
OnlyShowIn=XFCE;
X-GNOME-Autostart-enabled=true
EOF
