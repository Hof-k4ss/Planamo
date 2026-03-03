#!/bin/bash
set -e

echo "=== Creating launchers (robust, works from menu) ==="

APP_DIR="/usr/share/applications"
MAP_FILE="/root/tools_map.conf"

mkdir -p "$APP_DIR"

# Catégories standard
map_category() {
  case "$1" in
    "Mobile Acquisition") echo "Utility";;
    "Mobile Analysis") echo "Utility";;
    "Malware & Reverse Engineering") echo "Development";;
    "Disk & Filesystem") echo "System";;
    "Memory & Volatile Analysis") echo "System";;
    "Network & Traffic") echo "Network";;
    "OSINT & Investigation") echo "Network";;
    "Development & Scripting") echo "Development";;
    "Docker & Services") echo "Development";;
    *) echo "Utility";;
  esac
}

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

# Liste des commandes GUI (pas en terminal)
is_gui_cmd() {
  case "$1" in
    gparted|sqlitebrowser|jadx-gui|code|terminator|chromium-browser|firefox|firefox-esr) return 0;;
    *) return 1;;
  esac
}

while IFS='|' read -r name cmd themes; do
  [[ -z "$name" || "$name" =~ ^# ]] && continue

  # si commande absente, on ne génère pas
  if ! command -v "$cmd" >/dev/null 2>&1; then
    continue
  fi

  main_theme="$(echo "$themes" | cut -d',' -f1 | xargs)"
  category="$(map_category "$main_theme")"
  file="$(slugify "$name").desktop"

  if is_gui_cmd "$cmd"; then
    cat > "$APP_DIR/$file" <<EOF
[Desktop Entry]
Name=$name
Exec=$cmd
Icon=applications-development
Terminal=false
Type=Application
Categories=$category;
OnlyShowIn=XFCE;
EOF
  else
    # CLI: Terminal=true + bash -lc => marche même si PATH GUI diffère
    cat > "$APP_DIR/$file" <<EOF
[Desktop Entry]
Name=$name
Exec=bash -lc "$cmd; exec bash"
Icon=utilities-terminal
Terminal=true
Type=Application
Categories=$category;
OnlyShowIn=XFCE;
EOF
  fi

done < "$MAP_FILE"

# met à jour la base des .desktop (utile)
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" || true

echo "=== Launchers done ==="
