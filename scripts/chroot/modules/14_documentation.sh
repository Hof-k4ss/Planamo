#!/bin/bash
set -e

MAP_FILE="/root/tools_map.conf"
DOCROOT="/opt/planamo/docs"
DOCS="$DOCROOT/docs"
MK="$DOCROOT/mkdocs.yml"
SITE="$DOCROOT/site"

echo "=== Generating PLANAMO docs from tools_map.conf ==="

# Dépendances + mkdocs (venv)
export DEBIAN_FRONTEND=noninteractive
apt update || true
apt install -y python3-venv python3-pip

mkdir -p /opt/planamo/venvs
python3 -m venv /opt/planamo/venvs/mkdocs
/opt/planamo/venvs/mkdocs/bin/pip install --upgrade pip
/opt/planamo/venvs/mkdocs/bin/pip install mkdocs mkdocs-material

# Wrapper mkdocs global
cat <<'EOF' > /usr/local/bin/mkdocs
#!/bin/bash
exec /opt/planamo/venvs/mkdocs/bin/mkdocs "$@"
EOF
chmod +x /usr/local/bin/mkdocs

# Dossiers docs
mkdir -p "$DOCS/themes"

# Nettoyage
rm -f "$DOCS/index.md"
rm -f "$DOCS/themes/"*.md
rm -f "$MK"
rm -rf "$SITE"

# Thèmes (ordre fixe)
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

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

desktop_id_from_name() {
  # Doit matcher la logique du 12_menu_structure.sh (slug du Name)
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

# Index
cat > "$DOCS/index.md" <<'EOF'
# PLANAMO — Documentation outils

Documentation générée automatiquement depuis `tools_map.conf`.

Chaque outil indique :
- la commande
- le fichier `.desktop`
- comment le lancer via `gtk-launch <id>`
EOF

# Pages par thème + nav mkdocs
nav_lines=()
for t in "${themes[@]}"; do
  s="$(slugify "$t")"
  page="$DOCS/themes/$s.md"

  cat > "$page" <<EOF
# $t

EOF

  nav_lines+=("  - \"$t\": \"themes/$s.md\"")
done

# Remplissage des pages
while IFS='|' read -r name cmd themes_list; do
  [[ -z "$name" || "$name" =~ ^# ]] && continue

  desktop_id="$(desktop_id_from_name "$name")"
  desktop_file="${desktop_id}.desktop"

  IFS=',' read -ra tarr <<< "$themes_list"
  for raw in "${tarr[@]}"; do
    theme="$(echo "$raw" | xargs)"
    s="$(slugify "$theme")"
    page="$DOCS/themes/$s.md"
    [[ -f "$page" ]] || continue

    cat >> "$page" <<EOF
## $name

- **Commande** : \`$cmd\`
- **Lanceur** : \`/usr/share/applications/$desktop_file\`
- **Run (XFCE)** : \`gtk-launch $desktop_id\`

EOF
  done
done < "$MAP_FILE"

# mkdocs.yml
cat > "$MK" <<EOF
site_name: PLANAMO
theme:
  name: material
docs_dir: docs
nav:
  - "Accueil": "index.md"
$(printf "%s\n" "${nav_lines[@]}")
EOF

# Build HTML
cd "$DOCROOT"
mkdocs build -d "$SITE"

echo "=== HTML documentation built: $SITE/index.html ==="

# --------------------------------------------------------------------
# Desktop icon (SKEL ONLY) + fix "Untrusted" on first XFCE login
# --------------------------------------------------------------------
echo "=== Desktop icon: PLANAMO Documentation (skel only) ==="

mkdir -p /etc/skel/Desktop

cat > /etc/skel/Desktop/PLANAMO-Documentation.desktop <<'EOF'
[Desktop Entry]
Name=PLANAMO Documentation
Exec=xdg-open /opt/planamo/docs/site/index.html
Icon=help-browser
Terminal=false
Type=Application
EOF

chmod +x /etc/skel/Desktop/PLANAMO-Documentation.desktop

# Mark desktop files as trusted on first XFCE login (avoids popup)
mkdir -p /etc/xdg/autostart
cat > /etc/xdg/autostart/planamo-trust-desktop-files.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=PLANAMO Trust Desktop Files
Exec=sh -lc 'for f in "$HOME/Desktop/"*.desktop; do [ -f "$f" ] && gio set "$f" metadata::trusted true || true; done'
OnlyShowIn=XFCE;
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF

apt clean
