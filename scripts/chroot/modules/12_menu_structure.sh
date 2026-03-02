#!/bin/bash
set -e

MAP_FILE="/root/tools_map.conf"
APP_DIR="/usr/share/applications"

echo "=== Generating menu from tools_map.conf ==="

mkdir -p "$APP_DIR"

# Fonction : catégorie XDG standard selon thème
map_category() {
  case "$1" in
    "Mobile Acquisition") echo "Utility";;
    "Mobile Analysis") echo "Development";;
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

while IFS='|' read -r name cmd themes; do

  # Ignore commentaires / lignes vides
  [[ -z "$name" || "$name" =~ ^# ]] && continue

  # Vérifie si la commande existe (sauf Docker spécial)
  if [[ "$cmd" != "docker" ]] && ! command -v "$cmd" >/dev/null 2>&1; then
    continue
  fi

  # Prend le premier thème pour la catégorie XDG
  main_theme=$(echo "$themes" | cut -d',' -f1 | xargs)
  category=$(map_category "$main_theme")

  file_name=$(echo "$name" | tr ' ' '-' | tr '[:upper:]' '[:lower:]').desktop

  # Cas spécial Docker images
  if [[ "$name" == "MobSF" ]]; then
    cat > "$APP_DIR/$file_name" <<EOF
[Desktop Entry]
Name=MobSF
Exec=xfce4-terminal -e "docker rm -f mobsf 2>/dev/null || true; docker run -d -p 8000:8000 --name mobsf opensecurity/mobile-security-framework-mobsf:latest && sleep 5 && firefox http://127.0.0.1:8000; bash"
Icon=applications-internet
Terminal=true
Type=Application
Categories=$category;
OnlyShowIn=XFCE;
EOF
    continue
  fi

  # GUI détectée si contient -gui ou firefox/chromium/code
  if [[ "$cmd" =~ (gui|firefox|chromium|code|terminator|sqlitebrowser|gparted) ]]; then
    cat > "$APP_DIR/$file_name" <<EOF
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
    cat > "$APP_DIR/$file_name" <<EOF
[Desktop Entry]
Name=$name
Exec=xfce4-terminal -e "$cmd; bash"
Icon=utilities-terminal
Terminal=true
Type=Application
Categories=$category;
OnlyShowIn=XFCE;
EOF
  fi

done < "$MAP_FILE"

echo "=== Menu generation complete ==="
