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
# Icônes bureau via skel + home
# -----------------------
echo "=== Desktop icons ==="

mkdir -p /etc/skel/Desktop
mkdir -p "$HOME_DIR/Desktop"

# Icône Documentation PLANAMO
# firefox appelé directement pour éviter xdg-open qui ouvre un éditeur de texte
cat <<'EOF' > /etc/skel/Desktop/PLANAMO-Documentation.desktop
[Desktop Entry]
Name=PLANAMO Documentation
Exec=firefox /opt/planamo/docs/site/index.html
Icon=help-browser
Terminal=false
Type=Application
EOF
chmod +x /etc/skel/Desktop/PLANAMO-Documentation.desktop

# Icône Installer PLANAMO
# calamares sans pkexec : la règle polkit ci-dessous gère les droits
cat <<'EOF' > /etc/skel/Desktop/Install-PLANAMO.desktop
[Desktop Entry]
Name=Install PLANAMO
Exec=calamares
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

# Marquer les .desktop comme trusted via attribut xattr (sans session active)
# Cela évite le popup "Untrusted application launcher" de XFCE
apt install -y attr 2>/dev/null || true
for f in "$HOME_DIR/Desktop/"*.desktop; do
  attr -s "metadata::trusted" -V "yes" "$f" 2>/dev/null || \
  python3 -c "
import os
try:
    os.setxattr('$f', b'user.metadata::trusted', b'yes\x00')
except Exception as e:
    pass
" 2>/dev/null || true
done

# -----------------------
# Polkit : autoriser analyste à lancer calamares sans mot de passe
# -----------------------
echo "=== Polkit rule for calamares ==="

mkdir -p /etc/polkit-1/rules.d
cat <<'EOF' > /etc/polkit-1/rules.d/49-calamares.rules
polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.policykit.exec" &&
        action.lookup("program") == "/usr/bin/calamares" &&
        subject.isInGroup("sudo")) {
        return polkit.Result.YES;
    }
});
EOF

# -----------------------
# Images : copie dans ~/Pictures
# -----------------------
echo "=== Copying images to ~/Pictures ==="

PIC_DIR="$HOME_DIR/Pictures"
SRC_DIR="/usr/share/planamo"

mkdir -p "$PIC_DIR"
cp -f "$SRC_DIR/wallpaper_sim.png" "$PIC_DIR/" 2>/dev/null || true
cp -f "$SRC_DIR/patch_sim.png"     "$PIC_DIR/" 2>/dev/null || true
cp -f "$SRC_DIR/avatar_sim.png"    "$PIC_DIR/" 2>/dev/null || true
chown -R "$USER_NAME:$USER_NAME" "$PIC_DIR"

# -----------------------
# Wallpaper XFCE via xfconf xml (sans session active)
# Écrit directement le fichier de config xfce4-desktop
# -----------------------
echo "=== XFCE wallpaper config ==="

XFCONF_DIR="$HOME_DIR/.config/xfce4/xfconf/xfce-perchannel-xml"
mkdir -p "$XFCONF_DIR"

cat <<EOF > "$XFCONF_DIR/xfce4-desktop.xml"
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitorVirtual-1" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$PIC_DIR/wallpaper_sim.png"/>
          <property name="image-style" type="int" value="4"/>
        </property>
      </property>
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$PIC_DIR/wallpaper_sim.png"/>
          <property name="image-style" type="int" value="4"/>
        </property>
      </property>
    </property>
  </property>
</channel>
EOF

chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR/.config"



AVATAR_SRC="$PIC_DIR/avatar_sim.png"
if [ -f "$AVATAR_SRC" ]; then
  mkdir -p /var/lib/AccountsService/icons /var/lib/AccountsService/users
  cp -f "$AVATAR_SRC" "/var/lib/AccountsService/icons/$USER_NAME"
  cat <<EOF > "/var/lib/AccountsService/users/$USER_NAME"
[User]
Icon=/var/lib/AccountsService/icons/$USER_NAME
EOF
fi

echo "=== Finalize done ==="
