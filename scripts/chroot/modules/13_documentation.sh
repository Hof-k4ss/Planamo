#!/bin/bash
set -e

MAP_FILE="/root/tools_map.conf"
DOCROOT="/opt/planamo/docs"
DOCS="$DOCROOT/docs"
MK="$DOCROOT/mkdocs.yml"

echo "=== Generating PLANAMO docs from tools_map.conf ==="

mkdir -p "$DOCS/themes"

# Nettoyage simple (rebuild propre)
rm -f "$DOCS/index.md"
rm -f "$DOCS/themes/"*.md
rm -f "$MK"

# Liste des thèmes (ordre fixe)
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

desktop_filename_from_name() {
  # doit matcher la logique du 12_menu_structure.sh
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

# Index
cat > "$DOCS/index.md" <<'EOF'
# PLANAMO — Documentation outils

Cette documentation est générée automatiquement depuis `tools_map.conf`.

Chaque outil indique :
- la commande
- le fichier `.desktop`
- comment le lancer via : `gtk-launch <id>`

EOF

# Génère une page par thème + nav mkdocs
nav_lines=()
for t in "${themes[@]}"; do
  s="$(slugify "$t")"
  page="$DOCS/themes/$s.md"

  cat > "$page" <<EOF
# $t

EOF

  nav_lines+=("  - \"$t\": \"themes/$s.md\"")
done

# Parcours tools_map.conf et remplit les pages par thème
while IFS='|' read -r name cmd themes_list; do
  [[ -z "$name" || "$name" =~ ^# ]] && continue

  desktop_base="$(desktop_filename_from_name "$name")"
  desktop_file="${desktop_base}.desktop"
  desktop_id="$desktop_base"

  # Pour chaque thème de l’outil
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

# mkdocs.yml minimal
cat > "$MK" <<EOF
site_name: PLANAMO
docs_dir: docs
nav:
  - "Accueil": "index.md"
$(printf "%s\n" "${nav_lines[@]}")
EOF

echo "=== Docs generated in $DOCROOT ==="
