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

systemctl enable NetworkManager

# Autoriser NM à gérer toutes les interfaces
mkdir -p /etc/NetworkManager/conf.d
cat <<EOF > /etc/NetworkManager/conf.d/10-globally-managed-devices.conf
[keyfile]
unmanaged-devices=none
EOF

# Créer une connexion ethernet automatique
nmcli connection add type ethernet ifname "*" con-name "Wired connection" autoconnect yes || true

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

# Wallpaper XFCE (plein écran / zoom)
WALL="$PIC_DIR/patch_sim.png"
if command -v xfconf-query >/dev/null 2>&1 && [ -f "$WALL" ]; then
  while read -r prop; do
    xfconf-query -c xfce4-desktop -p "$prop" -s "$WALL" || true
  done < <(xfconf-query -c xfce4-desktop -l | grep -E 'last-image$' || true)

  # 5 = "Zoomed" (remplit l'écran)
  while read -r prop; do
    xfconf-query -c xfce4-desktop -p "$prop" -s 5 || true
  done < <(xfconf-query -c xfce4-desktop -l | grep -E 'image-style$' || true)
fi

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
