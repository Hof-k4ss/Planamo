#!/bin/bash
# =============================================================================
# 16_finalize.sh — Configuration finale du système PLANAMO
# =============================================================================
set -e

echo "=== Final system configuration ==="

USER_NAME="analyste"
HOME_DIR="/home/$USER_NAME"
PIC_DIR="$HOME_DIR/Pictures"

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
echo "=== Network configuration ==="
systemctl enable NetworkManager || true

mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/10-globally-managed-devices.conf << 'EOF'
[keyfile]
unmanaged-devices=none
EOF

# =============================================================================
# LIGHTDM — autologin + session XFCE
# =============================================================================
echo "=== LightDM configuration ==="

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
echo "=== Copying images ==="

SRC_DIR="/usr/share/planamo"
mkdir -p "$PIC_DIR"
cp -f "$SRC_DIR/wallpaper_sim.png" "$PIC_DIR/" 2>/dev/null || true
cp -f "$SRC_DIR/patch_sim.png"     "$PIC_DIR/" 2>/dev/null || true
cp -f "$SRC_DIR/avatar_sim.png"    "$PIC_DIR/" 2>/dev/null || true
chown -R "$USER_NAME:$USER_NAME" "$PIC_DIR" || true

# =============================================================================
# WALLPAPER XFCE (via autostart)
# =============================================================================
echo "=== XFCE wallpaper ==="

cat > /usr/local/bin/planamo-set-wallpaper << 'EOF'
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

mkdir -p "$HOME_DIR/.config"
chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR/.config" || true

# =============================================================================
# PANEL XFCE — CONFIGURATION COMPLÈTE
# =============================================================================
# CAUSE DU BUG (panel vide / absent) :
#
# xfce4-panel fonctionne avec DEUX couches de configuration :
#
#   Couche 1 — xfce4-panel.xml (xfconf) :
#     Liste des panels et leurs plugin-ids.
#     Lu depuis ~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml
#
#   Couche 2 — fichiers .rc par plugin :
#     Configuration individuelle de chaque plugin.
#     Lu depuis ~/.config/xfce4/panel/<plugin>-<id>.rc
#     Ex: applicationsmenu-1.rc, clock-5.rc, actions-6.rc
#
# ERREUR PRÉCÉDENTE : on créait le XML (couche 1) MAIS on effaçait le
# dossier ~/.config/xfce4/panel/ et on le laissait VIDE (couche 2 absente).
# Résultat : xfce4-panel ignorait notre XML et régénérait un panel minimal
# par défaut, sans horloge ni menu utilisateur.
#
# FIX : créer les DEUX couches de configuration.
# =============================================================================
echo "=== XFCE panel configuration ==="

XFCONF_DIR="$HOME_DIR/.config/xfce4/xfconf/xfce-perchannel-xml"
PANEL_DIR="$HOME_DIR/.config/xfce4/panel"
XDG_XFCONF_DIR="/etc/xdg/xfce4/xfconf/xfce-perchannel-xml"

mkdir -p "$XFCONF_DIR"
mkdir -p "$PANEL_DIR"
mkdir -p "$XDG_XFCONF_DIR"

# --- Couche 1 : xfce4-panel.xml ---
# Déclare les panels et la liste ordonnée des plugin-ids.
cat > /tmp/xfce4-panel.xml << 'PANELEOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
  </property>
  <property name="panel-1" type="empty">
    <property name="position" type="string" value="p=6;x=0;y=0"/>
    <property name="length" type="uint" value="100"/>
    <property name="position-locked" type="bool" value="true"/>
    <property name="size" type="uint" value="30"/>
    <property name="icon-size" type="uint" value="16"/>
    <property name="plugin-ids" type="array">
      <value type="int" value="1"/>
      <value type="int" value="2"/>
      <value type="int" value="3"/>
      <value type="int" value="4"/>
      <value type="int" value="5"/>
      <value type="int" value="6"/>
    </property>
  </property>
  <property name="plugins" type="empty">
    <property name="plugin-1" type="string" value="applicationsmenu"/>
    <property name="plugin-2" type="string" value="separator"/>
    <property name="plugin-3" type="string" value="tasklist"/>
    <property name="plugin-4" type="string" value="systray"/>
    <property name="plugin-5" type="string" value="clock"/>
    <property name="plugin-6" type="string" value="actions"/>
  </property>
</channel>
PANELEOF

# Copier dans ~/.config (config utilisateur, prioritaire) et /etc/xdg (défaut système)
cp /tmp/xfce4-panel.xml "$XFCONF_DIR/xfce4-panel.xml"
cp /tmp/xfce4-panel.xml "$XDG_XFCONF_DIR/xfce4-panel.xml"

# --- Couche 2 : fichiers .rc par plugin ---
# OBLIGATOIRES : sans eux, xfce4-panel ignore le XML et génère un panel par défaut.

# Plugin 1 : menu Applications PLANAMO (bouton en haut à gauche)
cat > "$PANEL_DIR/applicationsmenu-1.rc" << 'EOF'
[Configuration]
ShowButtonTitle=true
ButtonTitle=PLANAMO
CustomMenu=true
CustomMenuFile=/etc/xdg/menus/xfce-applications.menu
ButtonIcon=security-high
EOF

# Plugin 2 : séparateur invisible extensible (pousse les plugins suivants à droite)
cat > "$PANEL_DIR/separator-2.rc" << 'EOF'
[Configuration]
Expand=true
Style=0
EOF

# Plugin 3 : tasklist — liste des fenêtres ouvertes
cat > "$PANEL_DIR/tasklist-3.rc" << 'EOF'
[Configuration]
ShowLabels=true
Grouping=1
EOF

# Plugin 4 : systray — icônes réseau, son, notifications
cat > "$PANEL_DIR/systray-4.rc" << 'EOF'
[Configuration]
SizeMax=22
ShowFrame=false
EOF

# Plugin 5 : horloge avec date et heure
cat > "$PANEL_DIR/clock-5.rc" << 'EOF'
[Configuration]
Mode=6
DigitalFormat=%a %d %b  %H:%M
ShowFrame=false
EOF

# Plugin 6 : actions utilisateur — menu Déconnexion / Éteindre / Redémarrer
# C'est CE plugin qui affiche le nom d'utilisateur en haut à droite
cat > "$PANEL_DIR/actions-6.rc" << 'EOF'
[Configuration]
Appearance=0
Items=+logout,+separator,+shutdown,+restart
EOF

# Appliquer les permissions sur toute la config XFCE
chown -R "$USER_NAME:$USER_NAME" \
    "$XFCONF_DIR" \
    "$PANEL_DIR" \
    "$HOME_DIR/.config/xfce4" || true

# =============================================================================
# ICÔNES BUREAU — FIX "Untrusted Application Launcher"
# =============================================================================
# CAUSE DU BUG :
#
# XFCE4 marque un .desktop comme "trusted" via l'attribut GIO
# metadata::trusted, stocké dans ~/.local/share/gvfs-metadata/
# (ce n'est PAS un xattr du filesystem).
#
# os.setxattr("user.xdg.origin.url") ne résout PAS ce problème car :
#   1. /home/ en chroot peut être tmpfs (sans support xattr user)
#   2. XFCE lit metadata::trusted via GIO, indépendamment de cet xattr
#
# SOLUTION : un script autostart qui appelle "gio set metadata::trusted true"
# au premier login, avec une boucle d'attente que gio soit opérationnel.
# "gio set" écrit dans gvfs-metadata sans nécessiter le daemon gvfs-metadata.
# Un flag ~/.local/share/planamo-trust-icons.done évite de rejouer à chaque login.
# =============================================================================
echo "=== Desktop icons ==="

mkdir -p /etc/skel/Desktop
mkdir -p "$HOME_DIR/Desktop"

# --- Icône Documentation ---
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
chmod +x "$HOME_DIR/Desktop/PLANAMO-Documentation.desktop"

# --- Icône Installer ---
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
chmod +x "$HOME_DIR/Desktop/Install-PLANAMO.desktop"

# Copie dans /etc/skel pour les futurs utilisateurs
cp -f "$HOME_DIR/Desktop/PLANAMO-Documentation.desktop" /etc/skel/Desktop/
cp -f "$HOME_DIR/Desktop/Install-PLANAMO.desktop"       /etc/skel/Desktop/
chmod +x /etc/skel/Desktop/*.desktop

chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR/Desktop/" || true

# --- Script autostart : confiance des icônes au premier login ---
cat > /usr/local/bin/planamo-trust-icons << 'EOF'
#!/bin/bash
# Marque les icônes bureau comme "trusted" au premier démarrage de session.
# Utilise "gio set metadata::trusted true" (écrit dans gvfs-metadata,
# pas dans les xattrs filesystem — fonctionne sans le daemon gvfs).
# Un flag .done évite de rejouer à chaque login.

FLAG="$HOME/.local/share/planamo-trust-icons.done"
[ -f "$FLAG" ] && exit 0

mkdir -p "$HOME/.local/share/gvfs-metadata"

# Attendre que gio soit opérationnel (max 30 secondes)
for i in $(seq 1 60); do
    if gio info "$HOME/Desktop" >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done
sleep 1

# Marquer chaque .desktop du bureau comme trusted
for f in "$HOME/Desktop/"*.desktop; do
    [ -f "$f" ] || continue
    chmod +x "$f"
    gio set "$f" metadata::trusted true 2>/dev/null && \
        echo "[OK] trusted: $(basename "$f")" || \
        echo "[!] gio set failed: $(basename "$f")"
done

# Recharger le bureau pour afficher les icônes sans avertissement
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

AVATAR_SRC="$PIC_DIR/avatar_sim.png"
if [ -f "$AVATAR_SRC" ]; then
    mkdir -p /var/lib/AccountsService/icons /var/lib/AccountsService/users
    cp -f "$AVATAR_SRC" "/var/lib/AccountsService/icons/$USER_NAME"
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
# HELPERS XFCE (terminal, navigateur, gestionnaire de fichiers)
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
# DÉSACTIVER ÉCONOMISEUR D'ÉCRAN ET VEILLE
# =============================================================================
echo "=== Power & screensaver settings ==="

XFCONF_CHAN="$HOME_DIR/.config/xfce4/xfconf/xfce-perchannel-xml"
mkdir -p "$XFCONF_CHAN"

cat > "$XFCONF_CHAN/xfce4-screensaver.xml" << 'EOF'
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

cat > "$XFCONF_CHAN/xfce4-power-manager.xml" << 'EOF'
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
# FOND D'ÉCRAN LIGHTDM (greeter)
# =============================================================================
echo "=== LightDM wallpaper ==="

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

echo "=== Finalize done ==="
