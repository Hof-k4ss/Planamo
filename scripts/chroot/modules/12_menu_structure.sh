#!/bin/bash
set -e

APP_DIR="/usr/share/applications"
MAP_FILE="/root/tools_map.conf"

MENU_DIR="/etc/xdg/menus/applications-merged"
DIR_DIR="/usr/share/desktop-directories"

echo "=== Generating PLANAMO launchers + menu folders from tools_map.conf ==="

mkdir -p "$APP_DIR" "$MENU_DIR" "$DIR_DIR"

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

# Commandes GUI (ne pas lancer en terminal)
is_gui_cmd() {
  case "$1" in
    firefox|sqlitebrowser|gparted|jadx-gui|code|terminator|tor-browser) return 0;;
    *) return 1;;
  esac
}

# Thèmes connus (doit matcher tools_map.conf)
themes=(
  "Mobile Acquisition"
  "Mobile Analysis"
  "Malware & Reverse Engineering"
  "Disk & Filesystem"
  "Memory & Volatile Analysis"
  "Network & Traffic"
  "OSINT & Investigation"
  "Development & Scripting"
  "Docker & Services"
)

# --- 1) .directory files + top directory for PLANAMO root menu ---
cat > "$DIR_DIR/planamo.directory" <<'EOF'
[Desktop Entry]
Name=PLANAMO
Icon=applications-system
Type=Directory
EOF

for t in "${themes[@]}"; do
  s="$(slugify "$t")"
  cat > "$DIR_DIR/planamo-${s}.directory" <<EOF
[Desktop Entry]
Name=$t
Icon=folder
Type=Directory
EOF
done

# --- 2) Create merged menu definition (PLANAMO + submenus) ---
# XFCE reads /etc/xdg/menus/applications-merged/*.menu automatically.
cat > "$MENU_DIR/planamo.menu" <<EOF
<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN"
 "http://www.freedesktop.org/standards/menu-spec/menu-1.0.dtd">
<Menu>
  <Name>Applications</Name>

  <Menu>
    <Name>PLANAMO</Name>
    <Directory>planamo.directory</Directory>

$(for t in "${themes[@]}"; do
    s="$(slugify "$t")"
    cat <<SUB
    <Menu>
      <Name>$t</Name>
      <Directory>planamo-${s}.directory</Directory>
      <Include>
        <Category>PLANAMO-${s}</Category>
      </Include>
    </Menu>

SUB
done)

  </Menu>
</Menu>
EOF

# --- 3) Generate .desktop launchers from tools_map.conf ---
while IFS='|' read -r name cmd themes_list; do
  [[ -z "$name" || "$name" =~ ^# ]] && continue

  # Ne génère que si la commande existe
  if ! command -v "$cmd" >/dev/null 2>&1; then
    continue
  fi

  file="$(slugify "$name").desktop"

  # thèmes -> catégories PLANAMO-<slug>
  cats=""
  IFS=',' read -ra tarr <<< "$themes_list"
  for raw in "${tarr[@]}"; do
    theme="$(echo "$raw" | xargs)"
    ts="$(slugify "$theme")"
    cats="${cats}PLANAMO-${ts};"
  done

  # Toujours ajouter PLANAMO; pour debug/tri si besoin
  cats="${cats}PLANAMO;"

  if is_gui_cmd "$cmd"; then
    cat > "$APP_DIR/$file" <<EOF
[Desktop Entry]
Name=$name
Exec=$cmd
Icon=applications-development
Terminal=false
Type=Application
Categories=$cats
OnlyShowIn=XFCE;
EOF
  else
    # CLI: lancer en sudo comme tu veux (évite les problèmes de droits)
    cat > "$APP_DIR/$file" <<EOF
[Desktop Entry]
Name=$name
Exec=bash -lc "sudo $cmd; exec bash"
Icon=utilities-terminal
Terminal=true
Type=Application
Categories=$cats
OnlyShowIn=XFCE;
EOF
  fi

done < "$MAP_FILE"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" || true

echo "=== PLANAMO menu + launchers generated ==="
