analyste@planamo:~/planamo$ cat scripts/chroot/modules/12_menu_structure.sh 
#!/bin/bash
set -e

APP_DIR="/usr/share/applications"
MAP_FILE="/root/tools_map.conf"

echo "=== Generating desktop launchers from tools_map.conf (robust) ==="

mkdir -p "$APP_DIR"

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

# commandes GUI (pas de terminal)
is_gui_cmd() {
  case "$1" in
    firefox|sqlitebrowser|gparted|jadx-gui|code|terminator) return 0;;
    *) return 1;;
  esac
}

while IFS='|' read -r name cmd themes; do
  [[ -z "$name" || "$name" =~ ^# ]] && continue

  # Ne génère que si la commande existe
  if ! command -v "$cmd" >/dev/null 2>&1; then
    continue
  fi

  file="$(slugify "$name").desktop"

  if is_gui_cmd "$cmd"; then
    cat > "$APP_DIR/$file" <<EOF
[Desktop Entry]
Name=$name
Exec=$cmd
Icon=applications-development
Terminal=false
Type=Application
OnlyShowIn=XFCE;
EOF
  else
    cat > "$APP_DIR/$file" <<EOF
[Desktop Entry]
Name=$name
Exec=bash -lc "$cmd; exec bash"
Icon=utilities-terminal
Terminal=true
Type=Application
OnlyShowIn=XFCE;
EOF
  fi

done < "$MAP_FILE"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" || true

echo "=== Desktop launchers generated ==="
