#!/bin/bash
set -e

APP_DIR="/usr/share/applications"
MAP_FILE="/root/tools_map.conf"

echo "=== Generating desktop launchers + PLANAMO themed folders ==="

mkdir -p "$APP_DIR"

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

is_gui_cmd() {
  case "$1" in
    firefox|sqlitebrowser|gparted|jadx-gui|code|terminator|tor-browser) return 0;;
    *) return 1;;
  esac
}

# Crée une version "portable" d'un desktop (utilisable dans un dossier)
write_desktop() {
  local out="$1" name="$2" exec="$3" icon="$4" term="$5"

  cat > "$out" <<EOF
[Desktop Entry]
Name=$name
Exec=$exec
Icon=$icon
Terminal=$term
Type=Application
Categories=Utility;
OnlyShowIn=XFCE;
EOF
  chmod 755 "$out" || true
}

# 1) Génère les launchers systèmes (menu "All Applications")
while IFS='|' read -r name cmd themes; do
  [[ -z "$name" || "$name" =~ ^# ]] && continue

  command -v "$cmd" >/dev/null 2>&1 || continue

  file="$(slugify "$name").desktop"

  if is_gui_cmd "$cmd"; then
    # GUI : on le lance en sudo (comme tu veux). Attention: certains GUI n'aiment pas root.
    write_desktop "$APP_DIR/$file" "$name" "bash -lc \"sudo -n $cmd || sudo $cmd\"" "applications-development" "false"
  else
    # CLI : terminal + sudo
    write_desktop "$APP_DIR/$file" "$name" "bash -lc \"sudo -n $cmd || sudo $cmd; exec bash\"" "utilities-terminal" "true"
  fi
done < "$MAP_FILE"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" || true

# 2) Prépare les dossiers par thèmes dans /etc/skel (copié dans /home au 1er login)
SKEL_ROOT="/etc/skel/PLANAMO-Tools"
mkdir -p "$SKEL_ROOT"

# Nettoyage simple (rebuild propre)
find "$SKEL_ROOT" -type f -name "*.desktop" -delete 2>/dev/null || true

# Construit les dossiers + raccourcis dedans
while IFS='|' read -r name cmd themes_list; do
  [[ -z "$name" || "$name" =~ ^# ]] && continue
  command -v "$cmd" >/dev/null 2>&1 || continue

  # calc exec comme au-dessus
  if is_gui_cmd "$cmd"; then
    exec="bash -lc \"sudo -n $cmd || sudo $cmd\""
    icon="applications-development"
    term="false"
  else
    exec="bash -lc \"sudo -n $cmd || sudo $cmd; exec bash\""
    icon="utilities-terminal"
    term="true"
  fi

  IFS=',' read -ra tarr <<< "$themes_list"
  for raw in "${tarr[@]}"; do
    theme="$(echo "$raw" | xargs)"
    [ -n "$theme" ] || continue

    dir="$SKEL_ROOT/$theme"
    mkdir -p "$dir"

    out="$dir/$(slugify "$name").desktop"
    write_desktop "$out" "$name" "$exec" "$icon" "$term"
  done
done < "$MAP_FILE"

echo "=== Launchers + themed folders generated ==="
