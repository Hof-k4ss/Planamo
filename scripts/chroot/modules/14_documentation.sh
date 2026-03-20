#!/bin/bash
set -e

# Le dossier documentation/ est versionné dans le repo git
# et copié dans le rootfs par 02_chroot_setup.sh
# Structure :
#   /root/documentation/
#       docs/
#           extra/        ← pages manuelles (remnux.html, etc.)
#           themes/       ← générées automatiquement
#           index.md      ← généré automatiquement
#       assets/css/custom.css
#       mkdocs.yml        ← généré automatiquement

MAP_FILE="/root/tools_map.conf"
DOC_SRC="/root/documentation"
DOCROOT="/opt/planamo/docs"
DOCS="$DOCROOT/docs"
MK="$DOCROOT/mkdocs.yml"
SITE="$DOCROOT/site"

echo "=== Generating PLANAMO docs from tools_map.conf ==="

export DEBIAN_FRONTEND=noninteractive
apt install -y python3-venv python3-pip

mkdir -p /opt/planamo/venvs
python3 -m venv /opt/planamo/venvs/mkdocs
/opt/planamo/venvs/mkdocs/bin/pip install --upgrade pip
/opt/planamo/venvs/mkdocs/bin/pip install mkdocs mkdocs-material

cat << 'EOF' > /usr/local/bin/mkdocs
#!/bin/bash
exec /opt/planamo/venvs/mkdocs/bin/mkdocs "$@"
EOF
chmod +x /usr/local/bin/mkdocs

# Copier la structure documentation/ vers /opt/planamo/docs
mkdir -p "$DOCS/themes"
mkdir -p "$DOCS/extra"
mkdir -p "$DOCROOT/assets/css"

# Copier les assets CSS
if [ -d "$DOC_SRC/assets/css" ]; then
  cp -f "$DOC_SRC/assets/css/"* "$DOCROOT/assets/css/" 2>/dev/null || true
fi

# Copier les pages manuelles (extra/)
if [ -d "$DOC_SRC/docs/extra" ]; then
  cp -rf "$DOC_SRC/docs/extra/". "$DOCS/extra/" 2>/dev/null || true
  echo "[*] Pages manuelles copiées depuis documentation/docs/extra/"
fi

# Nettoyage pages générées (pas les manuelles)
rm -f "$DOCS/index.md"
rm -f "$DOCS/themes/"*.md
rm -f "$MK"
rm -rf "$SITE"

# CSS personnalisé (embarqué si pas fourni dans le repo)
CSS_FILE="$DOCROOT/assets/css/custom.css"
if [ ! -f "$CSS_FILE" ]; then
  mkdir -p "$(dirname "$CSS_FILE")"
  cat > "$CSS_FILE" << 'CSSEOF'
:root {
  --md-text-font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
  --md-code-font: "SF Mono", "Fira Code", "Roboto Mono", monospace;
}
body, .md-typeset {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  letter-spacing: -0.01em;
}
:root {
  --md-primary-fg-color: #3DDC84;
  --md-primary-fg-color--light: #3DDC84;
  --md-primary-fg-color--dark: #2bb56a;
  --md-accent-fg-color: #3DDC84;
}
.md-header { background-color: #1a1a1a; border-bottom: 2px solid #3DDC84; }
.md-header__title { font-weight: 600; letter-spacing: -0.02em; color: #3DDC84; }
.md-tabs { background-color: #111111; }
.md-tabs__link--active, .md-tabs__link:hover { color: #3DDC84 !important; }
[data-md-color-scheme="slate"] {
  --md-default-bg-color: #0d0d0d;
  --md-default-fg-color: #f5f5f7;
  --md-default-fg-color--light: #a1a1a6;
  --md-code-bg-color: #1c1c1e;
}
.md-typeset h1 { font-weight: 700; letter-spacing: -0.03em; color: #3DDC84; font-size: 2em; }
.md-typeset h2 { font-weight: 600; letter-spacing: -0.02em; color: #f5f5f7; border-bottom: 1px solid #3DDC84; padding-bottom: 0.3em; }
.md-typeset table { border-radius: 10px; overflow: hidden; border: 1px solid #2c2c2e; }
.md-typeset table th { background-color: #1c1c1e; color: #3DDC84; font-weight: 600; }
.md-typeset table tr:nth-child(even) { background-color: #141414; }
.md-typeset code { background-color: #1c1c1e; color: #3DDC84; border-radius: 4px; padding: 0.1em 0.4em; font-size: 0.85em; }
.md-nav__title { color: #3DDC84; font-weight: 600; }
.md-nav__link--active { color: #3DDC84 !important; }
.md-typeset hr { border-color: #2c2c2e; }
CSSEOF
fi

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

# Index avec liens directs
cat > "$DOCS/index.md" << 'MDEOF'
# PLANAMO — Documentation Outils Forensiques

| Catégorie | Description |
|-----------|-------------|
| [📱 Mobile Acquisition](themes/mobile-acquisition.md) | Acquisition forensique Android et iOS |
| [🔬 Mobile Analysis](themes/mobile-analysis.md) | Analyse d'artefacts mobiles |
| [🦠 Malware & Reverse Engineering](themes/malware-reverse-engineering.md) | Analyse de malwares et reverse engineering |
| [💽 Disk & Filesystem](themes/disk-filesystem.md) | Analyse et récupération de disques |
| [🧠 Memory & Volatile Analysis](themes/memory-volatile-analysis.md) | Analyse de dumps mémoire |
| [🌐 Network & Traffic](themes/network-traffic.md) | Capture et analyse réseau |
| [🔍 OSINT & Investigation](themes/osint-investigation.md) | Recherche en sources ouvertes |
| [⚙️ Development & Scripting](themes/development-scripting.md) | Développement et automatisation |
| [🐳 Docker & Services](themes/docker-services.md) | Environnements forensiques Docker |

---

## Guides

- [🦠 Guide REMnux](extra/remnux.html) — Utilisation du conteneur REMnux pour l'analyse de malwares

---
*Documentation générée depuis tools_map.conf — Pages manuelles dans documentation/docs/extra/*
MDEOF

nav_lines=()
for t in "${themes[@]}"; do
  s="$(slugify "$t")"
  page="$DOCS/themes/$s.md"
  case "$t" in
    "Mobile Acquisition")            icon="📱" ;;
    "Mobile Analysis")               icon="🔬" ;;
    "Malware & Reverse Engineering") icon="🦠" ;;
    "Disk & Filesystem")             icon="💽" ;;
    "Memory & Volatile Analysis")    icon="🧠" ;;
    "Network & Traffic")             icon="🌐" ;;
    "OSINT & Investigation")         icon="🔍" ;;
    "Development & Scripting")       icon="⚙️" ;;
    "Docker & Services")             icon="🐳" ;;
    *)                               icon="🔧" ;;
  esac
  printf "# %s %s\n\n" "$icon" "$t" > "$page"
  nav_lines+=("  - \"$icon $t\": \"themes/$s.md\"")
done

while IFS='|' read -r name cmd themes_list type description; do
  [[ -z "$name" || "$name" =~ ^# ]] && continue
  name="$(echo "$name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  cmd="$(echo "$cmd" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  type="$(echo "$type" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  description="$(echo "$description" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

  IFS=',' read -ra tarr <<< "$themes_list"
  for raw in "${tarr[@]}"; do
    theme="${raw#"${raw%%[![:space:]]*}"}"; theme="${theme%"${theme##*[![:space:]]}"}"
    s="$(slugify "$theme")"
    page="$DOCS/themes/$s.md"
    [[ -f "$page" ]] || continue

    {
      echo "## $name"
      echo ""
      echo "$description"
      echo ""
      echo "| Champ | Valeur |"
      echo "|-------|--------|"
      echo "| **Commande** | \`$cmd\` |"
      echo "| **Type** | $type |"
      echo ""
      echo "---"
      echo ""
    } >> "$page"
  done
done < "$MAP_FILE"

# Construire le mkdocs.yml
{
  echo "site_name: PLANAMO"
  echo "site_description: Mobile Forensics & Incident Response Platform"
  echo "use_directory_urls: false"
  echo "theme:"
  echo "  name: material"
  echo "  palette:"
  echo "    scheme: slate"
  echo "    primary: custom"
  echo "    accent: custom"
  echo "  font:"
  echo "    text: false"
  echo "    code: false"
  echo "  features:"
  echo "    - navigation.instant"
  echo "    - navigation.tabs"
  echo "    - navigation.expand"
  echo "    - toc.integrate"
  echo "extra_css:"
  echo "  - ../assets/css/custom.css"
  echo "docs_dir: docs"
  echo "nav:"
  echo "  - \"Accueil\": \"index.md\""
  for line in "${nav_lines[@]}"; do
    echo "$line"
  done
  if [ -d "$DOCS/extra" ] && ls "$DOCS/extra/"*.html >/dev/null 2>&1; then
    echo "  - \"Guides\":"
    for f in "$DOCS/extra/"*.html; do
      base=$(basename "$f" .html)
      label=$(echo "$base" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2); print}')
      echo "    - \"$label\": \"extra/$(basename "$f")\""
    done
  fi
} > "$MK" 
cd "$DOCROOT"
mkdocs build -d "$SITE"

echo "=== HTML documentation built: $SITE/index.html ==="
apt clean
