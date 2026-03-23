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
chown "$USER_NAME:$USER_NAME" "$HOME_DIR/.dmrc" || true

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
chown -R "$USER_NAME:$USER_NAME" "$PIC_DIR" || true

# -----------------------
# Wallpaper XFCE
# Écrit le XML de config directement dans le profil utilisateur.
# Couvre tous les noms de moniteurs courants (VM + bare metal).
# image-style 5 = Stretched (étiré)
# -----------------------
echo "=== XFCE wallpaper ==="

WALL="$PIC_DIR/wallpaper_sim.png"

# Script dynamique : applique le wallpaper sur tous les moniteurs detectes
cat << 'WALLEOF' > /usr/local/bin/planamo-set-wallpaper
#!/bin/bash
WALL="/home/analyste/Pictures/wallpaper_sim.png"
[ -f "$WALL" ] || exit 0

for i in $(seq 1 30); do
  pgrep xfdesktop >/dev/null 2>&1 && break
  sleep 0.5
done
sleep 1

for monitor in $(xrandr --query 2>/dev/null | grep ' connected' | awk '{print $1}'); do
  for screen in 0 1; do
    xfconf-query -c xfce4-desktop       -p "/backdrop/screen${screen}/monitor${monitor}/workspace0/last-image"       --create -t string -s "$WALL" 2>/dev/null || true
    xfconf-query -c xfce4-desktop       -p "/backdrop/screen${screen}/monitor${monitor}/workspace0/image-style"       --create -t int -s 5 2>/dev/null || true
  done
done

xfdesktop --reload 2>/dev/null || true
WALLEOF
chmod +x /usr/local/bin/planamo-set-wallpaper

mkdir -p /etc/xdg/autostart
cat << 'AEOF' > /etc/xdg/autostart/planamo-wallpaper.desktop
[Desktop Entry]
Type=Application
Name=PLANAMO Wallpaper
Exec=/usr/local/bin/planamo-set-wallpaper
Terminal=false
OnlyShowIn=XFCE;
X-GNOME-Autostart-enabled=true
NoDisplay=true
AEOF

mkdir -p "$HOME_DIR/.config"
chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR/.config" || true

# -----------------------
# Icônes bureau
# -----------------------
echo "=== Desktop icons ==="

mkdir -p /etc/skel/Desktop
mkdir -p "$HOME_DIR/Desktop"

cat << 'EOF' > /etc/skel/Desktop/PLANAMO-Documentation.desktop
[Desktop Entry]
Name=PLANAMO Documentation
Exec=/usr/local/bin/rtfm
Icon=help-browser
Terminal=false
Type=Application
EOF
chmod +x /etc/skel/Desktop/PLANAMO-Documentation.desktop

cat << 'EOF' > /etc/skel/Desktop/Install-PLANAMO.desktop
[Desktop Entry]
Name=Install PLANAMO
Exec=xterm -title "PLANAMO Installer" -fa "Monospace" -fs 11 -geometry 100x35 -e "sudo TERM=linux /usr/local/bin/planamo-install"
Icon=system-software-install
Terminal=false
Type=Application
X-XFCE-Source=file:///etc/skel/Desktop/Install-PLANAMO.desktop
EOF
chmod +x /etc/skel/Desktop/Install-PLANAMO.desktop

# L'icone Install ne va que sur le bureau live (casper/live)
# Elle se supprime d'elle-meme a la fin de planamo-install
cp -f /etc/skel/Desktop/PLANAMO-Documentation.desktop "$HOME_DIR/Desktop/"
cp -f /etc/skel/Desktop/Install-PLANAMO.desktop "$HOME_DIR/Desktop/"
chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR/Desktop/" || true
chmod +x "$HOME_DIR/Desktop/"*.desktop

# -----------------------
# Trusted launcher
# Double méthode : xattr direct dans le chroot + autostart one-shot
# -----------------------
echo "=== Trusted launcher ==="

# 1) xattr direct (fonctionne si le filesystem supporte les xattrs)
python3 -c "
import os
files = [
    '/home/analyste/Desktop/PLANAMO-Documentation.desktop',
    '/home/analyste/Desktop/Install-PLANAMO.desktop',
]
for f in files:
    if not os.path.exists(f):
        print('[!] Absent:', f)
        continue
    try:
        os.setxattr(f, b'user.xdg.origin.url', b'')
        print('[OK] xattr:', f)
    except Exception as ex:
        print('[!] xattr failed:', ex)
    os.chmod(f, 0o755)
" 2>/dev/null || true

# 2) Autostart one-shot : gio set au premier login
mkdir -p /etc/xdg/autostart

cat << 'EOF' > /usr/local/bin/planamo-trust-icons
#!/bin/bash
# Attendre xfdesktop
for i in $(seq 1 30); do
  pgrep xfdesktop >/dev/null 2>&1 && break
  sleep 0.5
done
sleep 2

for f in "$HOME/Desktop/"*.desktop; do
  [ -f "$f" ] || continue
  chmod +x "$f"
  # Methode 1 : gio set metadata trusted
  gio set "$f" metadata::trusted true 2>/dev/null || true
  # Methode 2 : xattr
  python3 -c "import os; os.setxattr('$f', b'user.xdg.origin.url', b'')" 2>/dev/null || true
done

# Forcer xfdesktop a relire les icones
xfdesktop --reload 2>/dev/null || true
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

# Helpers XFCE : terminal par defaut = Terminator, fichiers = Thunar
mkdir -p /usr/share/xfce4/helpers

cat > /usr/share/xfce4/helpers/custom-TerminalEmulator.desktop << 'EOF'
[Desktop Entry]
NoDisplay=true
Version=0.9.0
Type=X-XFCE-Helper
X-XFCE-Binaries=terminator;
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

# Appliquer pour tous les utilisateurs via helpers.rc global
cat > /etc/xdg/xfce4/helpers.rc << 'EOF'
WebBrowser=custom-WebBrowser
TerminalEmulator=custom-TerminalEmulator
FileManager=custom-FileManager
EOF

# -----------------------
# Désactiver économiseur d'écran, verrouillage et mise en veille
# -----------------------
echo "=== Power & screensaver settings ==="

XFCONF="$HOME_DIR/.config/xfce4/xfconf/xfce-perchannel-xml"
mkdir -p "$XFCONF"

# Désactiver xfce4-screensaver / verrouillage
cat > "$XFCONF/xfce4-screensaver.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-screensaver" version="1.0">
  <property name="saver" type="empty">
    <property name="enabled" type="bool" value="false"/>
    <property name="mode" type="int" value="0"/>
  </property>
  <property name="lock" type="empty">
    <property name="enabled" type="bool" value="false"/>
    <property name="saver-activation" type="bool" value="false"/>
  </property>
</channel>
EOF

# Désactiver DPMS et mise en veille écran
cat > "$XFCONF/xfce4-power-manager.xml" << 'EOF'
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

# Désactiver aussi xscreensaver si présent
if command -v xscreensaver-command >/dev/null 2>&1; then
  cat > "$HOME_DIR/.xscreensaver" << 'EOF'
mode: off
dpmsEnabled: False
EOF
  chown "$USER_NAME:$USER_NAME" "$HOME_DIR/.xscreensaver" || true
fi

chown -R "$USER_NAME:$USER_NAME" "$XFCONF" || true

# -----------------------
# Fond d'écran LightDM (écran de connexion)
# -----------------------
echo "=== LightDM wallpaper ==="

GREETER_CONF="/etc/lightdm/lightdm-gtk-greeter.conf"
WALL_PATH="/usr/share/planamo/wallpaper_sim.png"
if [ -f "$WALL_PATH" ]; then
  cat > "$GREETER_CONF" << EOF
[greeter]
background=$WALL_PATH
theme-name=Adwaita-dark
icon-theme-name=elementary-xfce-dark
font-name=Sans 11
xft-antialias=true
xft-hintstyle=slight
EOF
fi

# -----------------------
# Config panel XFCE — config réelle générée par XFCE sur le système
# -----------------------
echo "=== XFCE panel configuration ==="

XDG_PANEL_DIR="/etc/xdg/xfce4/xfconf/xfce-perchannel-xml"
XFCONF_PANEL="$HOME_DIR/.config/xfce4/xfconf/xfce-perchannel-xml"
mkdir -p "$XDG_PANEL_DIR"
mkdir -p "$XFCONF_PANEL"

cat > /tmp/xfce4-panel.xml << 'PANELEOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <value type="int" value="2"/>
  </property>
  <property name="dark-mode" type="bool" value="true"/>
  <property name="panel-1" type="empty">
    <property name="position" type="string" value="p=6;x=0;y=0"/>
    <property name="length" type="uint" value="100"/>
    <property name="position-locked" type="bool" value="true"/>
    <property name="icon-size" type="uint" value="16"/>
    <property name="size" type="uint" value="26"/>
    <property name="plugin-ids" type="array">
      <value type="int" value="1"/>
      <value type="int" value="2"/>
      <value type="int" value="3"/>
      <value type="int" value="4"/>
      <value type="int" value="5"/>
      <value type="int" value="6"/>
      <value type="int" value="8"/>
      <value type="int" value="9"/>
      <value type="int" value="10"/>
      <value type="int" value="11"/>
      <value type="int" value="12"/>
      <value type="int" value="13"/>
      <value type="int" value="14"/>
    </property>
  </property>
  <property name="panel-2" type="empty">
    <property name="autohide-behavior" type="uint" value="1"/>
    <property name="position" type="string" value="p=10;x=0;y=0"/>
    <property name="length" type="uint" value="1"/>
    <property name="position-locked" type="bool" value="true"/>
    <property name="size" type="uint" value="48"/>
    <property name="plugin-ids" type="array">
      <value type="int" value="15"/>
      <value type="int" value="16"/>
      <value type="int" value="17"/>
      <value type="int" value="18"/>
      <value type="int" value="19"/>
      <value type="int" value="20"/>
      <value type="int" value="21"/>
      <value type="int" value="22"/>
    </property>
  </property>
  <property name="plugins" type="empty">
    <property name="plugin-1" type="string" value="applicationsmenu">
      <property name="menu-file" type="string" value="/etc/xdg/menus/xfce-applications.menu"/>
      <property name="custom-menu" type="bool" value="true"/>
      <property name="show-button-title" type="bool" value="false"/>
    </property>
    <property name="plugin-2" type="string" value="tasklist">
      <property name="grouping" type="uint" value="1"/>
    </property>
    <property name="plugin-3" type="string" value="separator">
      <property name="expand" type="bool" value="true"/>
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-4" type="string" value="pager"/>
    <property name="plugin-5" type="string" value="separator">
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-6" type="string" value="systray">
      <property name="square-icons" type="bool" value="true"/>
      <property name="known-legacy-items" type="array">
        <value type="string" value="ibus panel"/>
      </property>
      <property name="known-items" type="array">
        <value type="string" value="nm-applet"/>
      </property>
    </property>
    <property name="plugin-8" type="string" value="pulseaudio">
      <property name="enable-keyboard-shortcuts" type="bool" value="true"/>
      <property name="show-notifications" type="bool" value="true"/>
    </property>
    <property name="plugin-9" type="string" value="power-manager-plugin"/>
    <property name="plugin-10" type="string" value="notification-plugin"/>
    <property name="plugin-11" type="string" value="separator">
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-12" type="string" value="clock"/>
    <property name="plugin-13" type="string" value="separator">
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-14" type="string" value="actions"/>
    <property name="plugin-15" type="string" value="showdesktop"/>
    <property name="plugin-16" type="string" value="separator"/>
    <property name="plugin-17" type="string" value="launcher"/>
    <property name="plugin-18" type="string" value="launcher"/>
    <property name="plugin-19" type="string" value="launcher"/>
    <property name="plugin-20" type="string" value="launcher"/>
    <property name="plugin-21" type="string" value="separator"/>
    <property name="plugin-22" type="string" value="directorymenu">
      <property name="base-directory" type="string" value="/home/analyste"/>
    </property>
  </property>
</channel>
PANELEOF

cp /tmp/xfce4-panel.xml "$XDG_PANEL_DIR/xfce4-panel.xml"
cp /tmp/xfce4-panel.xml "$XFCONF_PANEL/xfce4-panel.xml"
chown -R "$USER_NAME:$USER_NAME" "$XFCONF_PANEL" || true

echo "=== Finalize done ==="
