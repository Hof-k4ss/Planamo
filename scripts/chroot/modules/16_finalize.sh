#!/bin/bash
set -e

echo "=== Final system configuration ==="

USER_NAME="analyste"
HOME_DIR="/home/$USER_NAME"
PIC_DIR="$HOME_DIR/Pictures"

# -----------------------
# Hostname
# -----------------------
echo planamo > /etc/hostname

cat << EOF > /etc/hosts
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
cat << EOF > /etc/NetworkManager/conf.d/10-globally-managed-devices.conf
[keyfile]
unmanaged-devices=none
EOF

# -----------------------
# LightDM : session XFCE + autologin
# -----------------------
echo "=== LightDM configuration ==="

mkdir -p /etc/lightdm
cat << EOF > /etc/lightdm/lightdm.conf
[Seat:*]
autologin-user=$USER_NAME
autologin-user-timeout=0
user-session=xfce
greeter-session=lightdm-gtk-greeter
EOF

cat << EOF > "$HOME_DIR/.dmrc"
[Desktop]
Session=xfce
EOF
chown "$USER_NAME:$USER_NAME" "$HOME_DIR/.dmrc"

# Créer le fichier de session XFCE si absent
if [ ! -f /usr/share/xsessions/xfce.desktop ]; then
  mkdir -p /usr/share/xsessions
  cat << EOF > /usr/share/xsessions/xfce.desktop
[Desktop Entry]
Name=Xfce Session
Comment=Use this session to run Xfce as your desktop environment
Exec=startxfce4
Icon=
Type=Application
EOF
fi

# -----------------------
# Images → ~/Pictures
# -----------------------
echo "=== Copying images ==="

SRC_DIR="/usr/share/planamo"
mkdir -p "$PIC_DIR"
cp -f "$SRC_DIR/wallpaper_sim.png" "$PIC_DIR/" 2>/dev/null || true
cp -f "$SRC_DIR/patch_sim.png"     "$PIC_DIR/" 2>/dev/null || true
cp -f "$SRC_DIR/avatar_sim.png"    "$PIC_DIR/" 2>/dev/null || true
chown -R "$USER_NAME:$USER_NAME" "$PIC_DIR"

# -----------------------
# Wallpaper XFCE
# Écrit le XML de config directement dans le profil utilisateur.
# Couvre tous les noms de moniteurs courants (VM + bare metal).
# image-style 4 = étiré (Stretched)
# -----------------------
echo "=== XFCE wallpaper ==="

XFCONF_DIR="$HOME_DIR/.config/xfce4/xfconf/xfce-perchannel-xml"
mkdir -p "$XFCONF_DIR"
WALL="$PIC_DIR/wallpaper_sim.png"

cat << EOF > "$XFCONF_DIR/xfce4-desktop.xml"
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitorVirtual-1" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$WALL"/>
          <property name="image-style" type="int" value="4"/>
          <property name="color-style" type="int" value="0"/>
        </property>
      </property>
      <property name="monitorVirtual1" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$WALL"/>
          <property name="image-style" type="int" value="4"/>
          <property name="color-style" type="int" value="0"/>
        </property>
      </property>
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$WALL"/>
          <property name="image-style" type="int" value="4"/>
          <property name="color-style" type="int" value="0"/>
        </property>
      </property>
      <property name="monitorHDMI-1" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$WALL"/>
          <property name="image-style" type="int" value="4"/>
          <property name="color-style" type="int" value="0"/>
        </property>
      </property>
      <property name="monitorDP-1" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$WALL"/>
          <property name="image-style" type="int" value="4"/>
          <property name="color-style" type="int" value="0"/>
        </property>
      </property>
    </property>
  </property>
</channel>
EOF

chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR/.config"

# -----------------------
# Icônes bureau
# -----------------------
echo "=== Desktop icons ==="

mkdir -p /etc/skel/Desktop
mkdir -p "$HOME_DIR/Desktop"

cat << 'EOF' > /etc/skel/Desktop/PLANAMO-Documentation.desktop
[Desktop Entry]
Name=PLANAMO Documentation
Exec=/usr/local/bin/planamo-doc
Icon=help-browser
Terminal=false
Type=Application
EOF
chmod +x /etc/skel/Desktop/PLANAMO-Documentation.desktop

cat << 'EOF' > /etc/skel/Desktop/Install-PLANAMO.desktop
[Desktop Entry]
Name=Install PLANAMO
Exec=/usr/local/bin/planamo-install-gui
Icon=system-software-install
Terminal=false
Type=Application
EOF
chmod +x /etc/skel/Desktop/Install-PLANAMO.desktop

cp -f /etc/skel/Desktop/PLANAMO-Documentation.desktop "$HOME_DIR/Desktop/"
cp -f /etc/skel/Desktop/Install-PLANAMO.desktop "$HOME_DIR/Desktop/"
chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR/Desktop/"
chmod +x "$HOME_DIR/Desktop/"*.desktop

# -----------------------
# Trusted launcher : autostart one-shot
# gio set ne fonctionne pas sans session active.
# On utilise un autostart qui tourne au premier login et pose le flag trusted.
# -----------------------
echo "=== Trusted launcher autostart ==="

mkdir -p /etc/xdg/autostart

cat << 'EOF' > /usr/local/bin/planamo-trust-icons
#!/bin/bash
FLAG="$HOME/.config/planamo/.trusted-done"
[ -f "$FLAG" ] && exit 0

# Attendre que la session XFCE soit prête
sleep 2

for f in "$HOME/Desktop/"*.desktop; do
  [ -f "$f" ] || continue
  gio set "$f" metadata::trusted true 2>/dev/null || true
done

mkdir -p "$(dirname "$FLAG")"
touch "$FLAG"
EOF
chmod +x /usr/local/bin/planamo-trust-icons

cat << 'EOF' > /etc/xdg/autostart/planamo-trust-icons.desktop
[Desktop Entry]
Type=Application
Name=PLANAMO Trust Icons
Exec=/usr/local/bin/planamo-trust-icons
Terminal=false
OnlyShowIn=XFCE;
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF

# -----------------------
# Avatar utilisateur
# -----------------------
echo "=== Avatar ==="

AVATAR_SRC="$PIC_DIR/avatar_sim.png"
if [ -f "$AVATAR_SRC" ]; then
  mkdir -p /var/lib/AccountsService/icons /var/lib/AccountsService/users
  cp -f "$AVATAR_SRC" "/var/lib/AccountsService/icons/$USER_NAME"
  cat << EOF > "/var/lib/AccountsService/users/$USER_NAME"
[User]
Icon=/var/lib/AccountsService/icons/$USER_NAME
EOF
fi

# -----------------------
# Polkit : autoriser analyste à lancer l'installeur sans mot de passe
# -----------------------
echo "=== Polkit ==="

mkdir -p /etc/polkit-1/rules.d
cat << 'EOF' > /etc/polkit-1/rules.d/49-planamo.rules
polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.policykit.exec" &&
        subject.isInGroup("sudo")) {
        return polkit.Result.YES;
    }
});
EOF

echo "=== Finalize done ==="
