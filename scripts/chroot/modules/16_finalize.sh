#!/bin/bash
set -e

echo "=== Final system configuration ==="

USER_NAME="analyste"
HOME_DIR="/home/$USER_NAME"

# -----------------------
# Hostname
# -----------------------
echo planamo > /etc/hostname

cat <<EOF > /etc/hosts
127.0.0.1   localhost
127.0.1.1   planamo

::1         localhost ip6-localhost ip6-loopback
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
EOF

# -----------------------
# Network
# -----------------------
echo "=== Network configuration ==="
systemctl enable NetworkManager || true

mkdir -p /etc/NetworkManager/conf.d
cat <<EOF > /etc/NetworkManager/conf.d/10-globally-managed-devices.conf
[keyfile]
unmanaged-devices=none
EOF

# -----------------------
# LightDM : session XFCE + autologin analyste
# -----------------------
echo "=== LightDM : XFCE session + autologin ==="

cat <<EOF > /etc/lightdm/lightdm.conf
[Seat:*]
autologin-user=$USER_NAME
autologin-user-timeout=0
user-session=xfce
greeter-session=lightdm-gtk-greeter
EOF

# Forcer la session XFCE par défaut pour l'utilisateur
cat <<EOF > "$HOME_DIR/.dmrc"
[Desktop]
Session=xfce
EOF
chown "$USER_NAME:$USER_NAME" "$HOME_DIR/.dmrc"

# S'assurer que le fichier de session XFCE existe
if [ ! -f /usr/share/xsessions/xfce.desktop ]; then
  mkdir -p /usr/share/xsessions
  cat <<EOF > /usr/share/xsessions/xfce.desktop
[Desktop Entry]
Name=Xfce Session
Comment=Use this session to run Xfce as your desktop environment
Exec=startxfce4
Icon=
Type=Application
EOF
fi

# -----------------------
# Icônes bureau via skel + home (fiable, pas de timing)
# -----------------------
echo "=== Desktop icons ==="

mkdir -p /etc/skel/Desktop
mkdir -p "$HOME_DIR/Desktop"

# Icône Documentation PLANAMO
cat <<'EOF' > /etc/skel/Desktop/PLANAMO-Documentation.desktop
[Desktop Entry]
Name=PLANAMO Documentation
Exec=xdg-open /opt/planamo/docs/site/index.html
Icon=help-browser
Terminal=false
Type=Application
EOF
chmod +x /etc/skel/Desktop/PLANAMO-Documentation.desktop

# Icône Installer PLANAMO
cat <<'EOF' > /etc/skel/Desktop/Install-PLANAMO.desktop
[Desktop Entry]
Name=Install PLANAMO
Exec=pkexec calamares
Icon=system-software-install
Terminal=false
Type=Application
EOF
chmod +x /etc/skel/Desktop/Install-PLANAMO.desktop

# Copier dans le home de l'utilisateur déjà créé
cp -f /etc/skel/Desktop/PLANAMO-Documentation.desktop "$HOME_DIR/Desktop/"
cp -f /etc/skel/Desktop/Install-PLANAMO.desktop "$HOME_DIR/Desktop/"
chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR/Desktop/"
chmod +x "$HOME_DIR/Desktop/"*.desktop

# -----------------------
# Avatar utilisateur
# -----------------------
echo "=== Avatar ==="

AVATAR_SRC="/usr/share/planamo/logo_sim.png"
if [ -f "$AVATAR_SRC" ]; then
  mkdir -p /var/lib/AccountsService/icons /var/lib/AccountsService/users
  cp -f "$AVATAR_SRC" "/var/lib/AccountsService/icons/$USER_NAME"
  cat <<EOF > "/var/lib/AccountsService/users/$USER_NAME"
[User]
Icon=/var/lib/AccountsService/icons/$USER_NAME
EOF
fi

echo "=== Finalize done ==="
