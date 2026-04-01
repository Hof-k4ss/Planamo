#!/bin/bash
# =============================================================================
# 16_finalize.sh — Configuration finale du système PLANAMO
# =============================================================================
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
# RÉSEAU
# =============================================================================
echo "=== Network ==="
systemctl enable NetworkManager || true

mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/10-globally-managed-devices.conf << 'EOF'
[keyfile]
unmanaged-devices=none
EOF

# =============================================================================
# LIGHTDM — autologin + session XFCE
# =============================================================================
echo "=== LightDM ==="

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
# IMAGES → ~/Pictures
# =============================================================================
echo "=== Images ==="
SRC_DIR="/usr/share/planamo"
mkdir -p "$PIC_DIR"
cp -f "$SRC_DIR/wallpaper_sim.png" "$PIC_DIR/" 2>/dev/null || true
cp -f "$SRC_DIR/patch_sim.png"     "$PIC_DIR/" 2>/dev/null || true
cp -f "$SRC_DIR/avatar_sim.png"    "$PIC_DIR/" 2>/dev/null || true
chown -R "$USER_NAME:$USER_NAME" "$PIC_DIR" || true

# =============================================================================
# WALLPAPER (autostart)
# =============================================================================
echo "=== Wallpaper ==="

cat > /usr/local/bin/planamo-set-wallpaper << 'EOF'
#!/bin/bash
WALL="/home/analyste/Pictures/wallpaper_sim.png"
[ -f "$WALL" ] || exit 0
for i in $(seq 1 30); do pgrep xfdesktop >/dev/null 2>&1 && break; sleep 0.5; done
sleep 1
for monitor in $(xrandr --query 2>/dev/null | grep ' connected' | awk '{print $1}'); do
    for screen in 0 1; do
        xfconf-query -c xfce4-desktop \
          -p "/backdrop/screen${screen}/monitor${monitor}/workspace0/last-image" \
          --create -t string -s "$WALL" 2>/dev/null || true
        xfconf-query -c xfce4-desktop \
          -p "/backdrop/screen${screen}/monitor${monitor}/workspace0/image-style" \
          --create -t int -s 5 2>/dev/null || true
    done
done
xfdesktop --reload 2>/dev/null || true
EOF
chmod +x /usr/local/bin/planamo-set-wallpaper

mkdir -p /etc/xdg/autostart
cat > /etc/xdg/autostart/planamo-wallpaper.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=PLANAMO Wallpaper
Exec=/usr/local/bin/planamo-set-wallpaper
Terminal=false
OnlyShowIn=XFCE;
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF

# =============================================================================
# SESSION XFCE — désactiver la sauvegarde de session
# =============================================================================
# Le panel "rien du tout" est causé par xfce4-session qui rejoue une session
# sauvegardée sans panel (enregistrée lors d'un boot précédent où rien n'était
# configuré). SaveOnExit=false empêche toute future sauvegarde.
# On supprime aussi les sessions sauvegardées existantes.
# =============================================================================
echo "=== XFCE session (no-save) ==="

mkdir -p "$XFCONF_DIR"
mkdir -p "$HOME_DIR/.config/xfce4"

cat > "$XFCONF_DIR/xfce4-session.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-session" version="1.0">
  <property name="general" type="empty">
    <!-- Ne jamais sauvegarder la session à la déconnexion -->
    <property name="SaveOnExit" type="bool" value="false"/>
    <!-- Toujours démarrer une session vierge -->
    <property name="SessionName" type="string" value="Default"/>
  </property>
</channel>
EOF

# Supprimer toute session sauvegardée existante qui prendrait le dessus
rm -rf "$HOME_DIR/.config/xfce4/sessions" 2>/dev/null || true

chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR/.config" || true

# =============================================================================
# ICÔNES BUREAU
# =============================================================================
# Le dialog "mark executable / launch anyway / cancel" signifie deux choses :
#   1. Le fichier .desktop n'a PAS le bit exécutable (chmod +x manquant)
#   2. ET/OU metadata::trusted n'est pas positionné
#
# Fix bit exécutable : on utilise install(1) qui préserve correctement les
# permissions dans l'image squashfs, contrairement à cp suivi de chmod
# qui peut être ignoré selon le umask du chroot.
#
# Fix trusted : script autostart qui appelle "gio set metadata::trusted true"
# dans la vraie session XFCE où gvfs-daemon tourne déjà.
# =============================================================================
echo "=== Desktop icons ==="

mkdir -p /etc/skel/Desktop
mkdir -p "$HOME_DIR/Desktop"

# Icône Documentation — install -m 0755 garantit le bit exécutable dans squashfs
install -m 0755 /dev/null "$HOME_DIR/Desktop/PLANAMO-Documentation.desktop"
cat > "$HOME_DIR/Desktop/PLANAMO-Documentation.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Name=PLANAMO Documentation
Comment=Ouvrir la documentation des outils PLANAMO
Exec=/usr/local/bin/rtfm
Icon=help-browser
Terminal=false
Type=Application
EOF

# Icône Installer
install -m 0755 /dev/null "$HOME_DIR/Desktop/Install-PLANAMO.desktop"
cat > "$HOME_DIR/Desktop/Install-PLANAMO.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Name=Install PLANAMO
Comment=Installer PLANAMO sur disque dur
Exec=xterm -title "PLANAMO Installer" -fa "Monospace" -fs 11 -geometry 100x35 -e "sudo TERM=linux /usr/local/bin/planamo-install"
Icon=system-software-install
Terminal=false
Type=Application
EOF

# Vérification explicite que les bits sont bien là
chmod 0755 "$HOME_DIR/Desktop/PLANAMO-Documentation.desktop"
chmod 0755 "$HOME_DIR/Desktop/Install-PLANAMO.desktop"

# Copie dans /etc/skel avec les bons bits
install -m 0755 "$HOME_DIR/Desktop/PLANAMO-Documentation.desktop" /etc/skel/Desktop/
install -m 0755 "$HOME_DIR/Desktop/Install-PLANAMO.desktop"        /etc/skel/Desktop/

chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR/Desktop/" || true

# Vérification finale des permissions — affiché dans le log de build
ls -la "$HOME_DIR/Desktop/"

# =============================================================================
# SCRIPT AUTOSTART — marque les icônes trusted via gio set au premier login
# =============================================================================
# gvfs-daemon est lancé automatiquement par xfce4-session avant xfdesktop.
# "gio set metadata::trusted true" fonctionne dès que gvfs-daemon tourne.
# On attend que "gio info" réponde avant d'agir (max 30 secondes).
# Un flag .done évite de rejouer à chaque login.
# =============================================================================
cat > /usr/local/bin/planamo-trust-icons << 'EOF'
#!/bin/bash
FLAG="$HOME/.local/share/planamo-trust-icons.done"
[ -f "$FLAG" ] && exit 0

mkdir -p "$HOME/.local/share"

# Attendre que gvfs-daemon soit prêt
for i in $(seq 1 60); do
    gio info "$HOME/Desktop" >/dev/null 2>&1 && break
    sleep 0.5
done
sleep 2

# S'assurer que les fichiers sont bien exécutables
chmod 0755 "$HOME/Desktop/"*.desktop 2>/dev/null || true

# Marquer chaque .desktop comme trusted
for f in "$HOME/Desktop/"*.desktop; do
    [ -f "$f" ] || continue
    gio set "$f" metadata::trusted true 2>/dev/null && \
        echo "[OK] trusted: $(basename "$f")" || \
        echo "[!] gio set failed: $(basename "$f")"
done

# Recharger le bureau
xfdesktop --reload 2>/dev/null || true
touch "$FLAG"
EOF
chmod +x /usr/local/bin/planamo-trust-icons

cat > /etc/xdg/autostart/planamo-trust-icons.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=PLANAMO Trust Icons
Exec=/usr/local/bin/planamo-trust-icons
Terminal=false
OnlyShowIn=XFCE;
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF

# =============================================================================
# AVATAR UTILISATEUR
# =============================================================================
echo "=== Avatar ==="
if [ -f "$PIC_DIR/avatar_sim.png" ]; then
    mkdir -p /var/lib/AccountsService/icons /var/lib/AccountsService/users
    cp -f "$PIC_DIR/avatar_sim.png" "/var/lib/AccountsService/icons/$USER_NAME"
    cat > "/var/lib/AccountsService/users/$USER_NAME" << EOF
[User]
Icon=/var/lib/AccountsService/icons/$USER_NAME
EOF
fi

# =============================================================================
# POLKIT
# =============================================================================
echo "=== Polkit ==="
mkdir -p /etc/polkit-1/rules.d
cat > /etc/polkit-1/rules.d/49-planamo.rules << 'EOF'
polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.policykit.exec" &&
        subject.isInGroup("sudo")) {
        return polkit.Result.YES;
    }
});
EOF

# =============================================================================
# HELPERS XFCE (terminal, navigateur, fichiers)
# =============================================================================
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

cat > /etc/xdg/xfce4/helpers.rc << 'EOF'
WebBrowser=custom-WebBrowser
TerminalEmulator=custom-TerminalEmulator
FileManager=custom-FileManager
EOF

# =============================================================================
# ÉCONOMISEUR D'ÉCRAN ET VEILLE désactivés
# =============================================================================
echo "=== Power settings ==="
mkdir -p "$XFCONF_DIR"

cat > "$XFCONF_DIR/xfce4-screensaver.xml" << 'EOF'
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

chown -R "$USER_NAME:$USER_NAME" "$XFCONF_DIR" || true

# =============================================================================
# FOND D'ÉCRAN LIGHTDM
# =============================================================================
echo "=== LightDM greeter ==="
WALL_PATH="/usr/share/planamo/wallpaper_sim.png"
if [ -f "$WALL_PATH" ]; then
    cat > /etc/lightdm/lightdm-gtk-greeter.conf << EOF
[greeter]
background=$WALL_PATH
theme-name=Adwaita-dark
icon-theme-name=elementary-xfce-dark
font-name=Sans 11
xft-antialias=true
xft-hintstyle=slight
EOF
fi

echo "=== Final cleanup for ISO ==="

export DEBIAN_FRONTEND=noninteractive

# Nettoyage APT
apt-get autoremove -y || true
apt-get autoclean -y || true
apt-get clean || true
rm -rf /var/lib/apt/lists/* 2>/dev/null || true

# Nettoyage caches temporaires
rm -rf /tmp/* /tmp/.[!.]* /tmp/..?* 2>/dev/null || true
rm -rf /var/tmp/* /var/tmp/.[!.]* /var/tmp/..?* 2>/dev/null || true

# Nettoyage journaux
find /var/log -type f -exec truncate -s 0 {} \; 2>/dev/null || true
rm -f /var/log/*.gz /var/log/*.[0-9] 2>/dev/null || true
rm -rf /var/log/journal/* 2>/dev/null || true

# Nettoyage historiques shell
rm -f /root/.bash_history 2>/dev/null || true
rm -f /home/analyste/.bash_history 2>/dev/null || true

# Nettoyage miniatures / caches utilisateur
rm -rf /home/analyste/.cache/thumbnails/* 2>/dev/null || true
rm -rf /home/analyste/.cache/mime/* 2>/dev/null || true
rm -rf /home/analyste/.cache/xfce4/* 2>/dev/null || true

# Nettoyage cache pip éventuel
rm -rf /root/.cache/pip 2>/dev/null || true
rm -rf /home/analyste/.cache/pip 2>/dev/null || true

# Nettoyage machine-id pour cloner une ISO propre
truncate -s 0 /etc/machine-id 2>/dev/null || true
rm -f /var/lib/dbus/machine-id 2>/dev/null || true
ln -sf /etc/machine-id /var/lib/dbus/machine-id 2>/dev/null || true

# Nettoyage fichiers runtime résiduels
rm -rf /run/* 2>/dev/null || true

# Permissions utilisateur
chown -R analyste:analyste /home/analyste 2>/dev/null || true

sync
echo "=== Finalize done ==="
