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

tool_icon() {
  local cmd="$1"
  local type="$2"
  case "$cmd" in
    adb|fastboot|androidqf)          echo "phone" ;;
    ideviceinfo|idevicebackup2|\
    idevicesyslog|idevicecrashreport) echo "phone" ;;
    mvt-android|mvt-ios)             echo "security-medium" ;;
    sqlitebrowser)                   echo "database" ;;
    exiftool)                        echo "image-x-generic" ;;
    androguard|apktool|jadx-gui)     echo "package-x-generic" ;;
    yara|clamscan)                   echo "dialog-warning" ;;
    binwalk|strings|hexedit)         echo "applications-science" ;;
    r2|rizin|frida|upx)              echo "applications-engineering" ;;
    dc3dd|ddrescue|partclone)        echo "drive-harddisk" ;;
    gparted|testdisk|photorec)       echo "drive-harddisk" ;;
    tsk_recover|foremost)            echo "edit-find" ;;
    cryptsetup)                      echo "security-high" ;;
    volatility3)                     echo "media-flash" ;;
    tcpdump|nmap|nc|socat)           echo "network-wired" ;;
    ssh|rsync)                       echo "network-transmit-receive" ;;
    dig|whois)                       echo "network-server" ;;
    firefox)                         echo "firefox" ;;
    tor-browser)                     echo "tor" ;;
    proxychains4)                    echo "network-vpn" ;;
    curl|wget)                       echo "internet-web-browser" ;;
    jq|rg)                           echo "edit-find" ;;
    python3)                         echo "text-x-python" ;;
    git)                             echo "git" ;;
    code)                            echo "code" ;;
    terminator)                      echo "utilities-terminal" ;;
    tmux)                            echo "utilities-terminal" ;;
    docker|mobsf|remnux)             echo "application-x-executable" ;;
    *)
      if [ "$type" = "gui" ]; then
        echo "applications-system"
      else
        echo "utilities-terminal"
      fi
      ;;
  esac
}

while IFS='|' read -r name cmd themes type description; do
  [[ -z "$name" || "$name" =~ ^# ]] && continue

  name="${name#"${name%%[![:space:]]*}"}"; name="${name%"${name##*[![:space:]]}"}" 
  cmd="${cmd#"${cmd%%[![:space:]]*}"}"; cmd="${cmd%"${cmd##*[![:space:]]}"}" 
  themes="${themes#"${themes%%[![:space:]]*}"}"; themes="${themes%"${themes##*[![:space:]]}"}" 
  type="${type#"${type%%[![:space:]]*}"}"; type="${type%"${type##*[![:space:]]}"}" 

  # Ne pas bloquer si la commande n'est pas dans le PATH
  # (certains outils sont dans /opt ou installés plus tard)
  bin="${cmd%% *}"

  file="planamo-$(slugify "$name").desktop"
  icon="$(tool_icon "$bin" "$type")"

  cats=""
  IFS=',' read -ra tarr <<< "$themes"
  for raw in "${tarr[@]}"; do
    t="${raw#"${raw%%[![:space:]]*}"}"; t="${t%"${t##*[![:space:]]}"}"
    c="$(theme_to_cat "$t")"
    cats="${cats}${c};"
  done

  if [ "$type" = "gui" ]; then
    cat > "$APP_DIR/$file" << EOF
[Desktop Entry]
Name=$name
Exec=$cmd
Icon=$icon
Terminal=false
Type=Application
Categories=$cats
EOF
  else
    cat > "$APP_DIR/$file" << EOF
[Desktop Entry]
Name=$name
Exec=xfce4-terminal -e "bash -lc '$cmd; exec bash'"
Icon=$icon
Terminal=false
Type=Application
Categories=$cats
EOF
  fi

done < "$MAP_FILE"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" || true

echo "=== PLANAMO launchers generated ==="
