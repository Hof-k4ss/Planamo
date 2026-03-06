#!/bin/bash
set -e

APP_DIR="/usr/share/applications"
MAP_FILE="/root/tools_map.conf"

echo "=== Generating PLANAMO launchers (menu categories) ==="
mkdir -p "$APP_DIR"

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

theme_to_cat() {
  case "$1" in
    "Mobile Acquisition")            echo "X-PLANAMO-MOBILE-ACQ" ;;
    "Mobile Analysis")               echo "X-PLANAMO-MOBILE-ANALYSIS" ;;
    "Malware & Reverse Engineering") echo "X-PLANAMO-MALWARE" ;;
    "Disk & Filesystem")             echo "X-PLANAMO-DISK" ;;
    "Memory & Volatile Analysis")    echo "X-PLANAMO-MEMORY" ;;
    "Network & Traffic")             echo "X-PLANAMO-NETWORK" ;;
    "OSINT & Investigation")         echo "X-PLANAMO-OSINT" ;;
    "Development & Scripting")       echo "X-PLANAMO-DEV" ;;
    "Docker & Services")             echo "X-PLANAMO-DOCKER" ;;
    *)                               echo "X-PLANAMO" ;;
  esac
}

while IFS='|' read -r name cmd themes type; do
  [[ -z "$name" || "$name" =~ ^# ]] && continue

  bin="${cmd%% *}"
  command -v "$bin" >/dev/null 2>&1 || continue

  file="planamo-$(slugify "$name").desktop"

  cats=""
  IFS=',' read -ra tarr <<< "$themes"
  for raw in "${tarr[@]}"; do
    t="$(echo "$raw" | xargs)"
    c="$(theme_to_cat "$t")"
    cats="${cats}${c};"
  done

  type="$(echo "$type" | xargs)"

  if [ "$type" = "gui" ]; then
    cat > "$APP_DIR/$file" << EOF
[Desktop Entry]
Name=$name
Exec=$cmd
Icon=applications-system
Terminal=false
Type=Application
Categories=$cats
EOF
  else
    cat > "$APP_DIR/$file" << EOF
[Desktop Entry]
Name=$name
Exec=xfce4-terminal -e "bash -lc '$cmd; exec bash'"
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=$cats
EOF
  fi

done < "$MAP_FILE"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" || true
echo "=== PLANAMO launchers generated ==="
