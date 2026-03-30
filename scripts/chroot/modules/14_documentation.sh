#!/bin/bash
# =============================================================================
# 14_documentation.sh — Génération de la documentation PLANAMO avec MkDocs
# =============================================================================
#
# Génère le site HTML statique depuis tools_map.conf.
# Les pages manuelles (ex: remnux.html) doivent être placées dans :
#   documentation/docs/extra/
#
# Elles sont copiées dans le site final et référencées depuis l'index.
#
# COMMENT AJOUTER UNE PAGE MANUELLE :
#   1. Créez documentation/docs/extra/mon-outil.html
#   2. Elle apparaîtra automatiquement dans la section "Guides" de l'index
#      et dans la nav de mkdocs.
#
# Structure finale :
#   /opt/planamo/docs/site/index.html   ← point d'entrée (rtfm / planamo-doc)
#   /opt/planamo/docs/site/extra/       ← pages manuelles (remnux.html, etc.)
# =============================================================================
set -e

MAP_FILE="/root/tools_map.conf"
DOC_SRC="/root/documentation"
DOCROOT="/opt/planamo/docs"
DOCS="$DOCROOT/docs"
MK="$DOCROOT/mkdocs.yml"
SITE="$DOCROOT/site"

echo "=== Generating PLANAMO docs from tools_map.conf ==="

export DEBIAN_FRONTEND=noninteractive
apt install -y python3-venv python3-pip

# --- Venv MkDocs ---
mkdir -p /opt/planamo/venvs
python3 -m venv /opt/planamo/venvs/mkdocs
/opt/planamo/venvs/mkdocs/bin/pip install --upgrade pip
/opt/planamo/venvs/mkdocs/bin/pip install mkdocs mkdocs-material

# Wrapper global mkdocs
cat > /usr/local/bin/mkdocs << 'WEOF'
#!/bin/bash
exec /opt/planamo/venvs/mkdocs/bin/mkdocs "$@"
WEOF
chmod +x /usr/local/bin/mkdocs

# --- Préparation de l'arborescence docs ---
mkdir -p "$DOCS/themes"
mkdir -p "$DOCS/extra"
mkdir -p "$DOCROOT/assets/css"

# Copie des assets CSS personnalisés depuis le repo
if [ -d "$DOC_SRC/assets/css" ]; then
    cp -f "$DOC_SRC/assets/css/"* "$DOCROOT/assets/css/" 2>/dev/null || true
fi

# Copie des pages manuelles depuis documentation/docs/extra/
# (remnux.html et toute autre page HTML manuelle)
if [ -d "$DOC_SRC/docs/extra" ]; then
    cp -rf "$DOC_SRC/docs/extra/". "$DOCS/extra/"
    echo "[*] Pages manuelles copiées depuis documentation/docs/extra/ :"
    ls "$DOCS/extra/" 2>/dev/null | sed 's/^/    /'
fi

# --- Remise à zéro des pages générées (pas des manuelles) ---
rm -f "$DOCS/index.md"
rm -f "$DOCS/themes/"*.md
rm -f "$MK"
rm -rf "$SITE"

# =============================================================================
# CSS INTÉGRÉ (utilisé si pas de custom.css dans le repo)
# =============================================================================
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

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================
slugify() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

theme_icon() {
    case "$1" in
        "Mobile Acquisition")            echo "📱" ;;
        "Mobile Analysis")               echo "🔬" ;;
        "Malware & Reverse Engineering") echo "🦠" ;;
        "Disk & Filesystem")             echo "💽" ;;
        "Memory & Volatile Analysis")    echo "🧠" ;;
        "Network & Traffic")             echo "🌐" ;;
        "OSINT & Investigation")         echo "🔍" ;;
        "Development & Scripting")       echo "⚙️" ;;
        "Docker & Services")             echo "🐳" ;;
        *)                               echo "🔧" ;;
    esac
}

# =============================================================================
# GÉNÉRATION DES PAGES PAR THÈME
# =============================================================================
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

nav_theme_lines=()

for t in "${themes[@]}"; do
    s="$(slugify "$t")"
    icon="$(theme_icon "$t")"
    page="$DOCS/themes/$s.md"
    printf "# %s %s\n\n" "$icon" "$t" > "$page"
    nav_theme_lines+=("  - \"$icon $t\": \"themes/$s.md\"")
done

# Remplissage des pages thème depuis tools_map.conf
while IFS='|' read -r name cmd themes_list type description; do
    # Ignorer les commentaires et lignes vides
    [[ -z "$name" || "$name" =~ ^# ]] && continue

    # Nettoyage des espaces autour des champs
    name="$(echo "$name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    cmd="$(echo "$cmd" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    type="$(echo "$type" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    description="$(echo "$description" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

    # Un outil peut appartenir à plusieurs thèmes (séparés par virgule)
    IFS=',' read -ra tarr <<< "$themes_list"
    for raw in "${tarr[@]}"; do
        theme="$(echo "$raw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
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

# =============================================================================
# DÉTECTION DES PAGES MANUELLES (extra/*.html)
# Chaque fichier HTML dans docs/extra/ devient un "Guide" dans la nav.
# =============================================================================
nav_guide_lines=()

if [ -d "$DOCS/extra" ]; then
    for f in "$DOCS/extra/"*.html; do
        [ -f "$f" ] || continue
        base="$(basename "$f" .html)"
        # Génère un label lisible depuis le nom de fichier (remnux → Remnux)
        label="$(echo "$base" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2); print}')"
        nav_guide_lines+=("    - \"$label\": \"extra/$(basename "$f")\"")
        echo "[*] Guide détecté : $label (extra/$(basename "$f"))"
    done
fi

# =============================================================================
# GÉNÉRATION DE L'INDEX
# Inclut les thèmes ET les guides (pages manuelles comme remnux.html)
# =============================================================================
{
    echo "# PLANAMO — Documentation Outils Forensiques"
    echo ""
    echo "| Catégorie | Description |"
    echo "|-----------|-------------|"
    for t in "${themes[@]}"; do
        s="$(slugify "$t")"
        icon="$(theme_icon "$t")"
        echo "| [$icon $t](themes/$s.md) | — |"
    done
    echo ""
    echo "---"
    echo ""

    # Section Guides uniquement si des pages manuelles existent
    if [ ${#nav_guide_lines[@]} -gt 0 ]; then
        echo "## Guides"
        echo ""
        for f in "$DOCS/extra/"*.html; do
            [ -f "$f" ] || continue
            base="$(basename "$f" .html)"
            label="$(echo "$base" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2); print}')"
            echo "- [$label](extra/$(basename "$f"))"
        done
        echo ""
        echo "---"
        echo ""
    fi

    echo "*Documentation générée depuis tools_map.conf — Pages manuelles dans documentation/docs/extra/*"
} > "$DOCS/index.md"

# =============================================================================
# GÉNÉRATION DE mkdocs.yml
# =============================================================================
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

    # Thèmes
    for line in "${nav_theme_lines[@]}"; do
        echo "$line"
    done

    # Guides (pages manuelles) — section séparée dans la nav
    if [ ${#nav_guide_lines[@]} -gt 0 ]; then
        echo "  - \"Guides\":"
        for line in "${nav_guide_lines[@]}"; do
            echo "$line"
        done
    fi
} > "$MK"

# =============================================================================
# BUILD MKDOCS
# =============================================================================
echo "[*] Building MkDocs site..."
cd "$DOCROOT"
mkdocs build -d "$SITE"

# =============================================================================
# COPIE POST-BUILD des pages manuelles HTML
# MkDocs ne traite pas les fichiers .html dans docs/ directement —
# on les copie manuellement dans le site généré pour garantir leur présence.
# =============================================================================
if [ -d "$DOCS/extra" ]; then
    mkdir -p "$SITE/extra"
    cp -f "$DOCS/extra/"*.html "$SITE/extra/" 2>/dev/null || true
    echo "[*] Pages manuelles copiées dans $SITE/extra/ :"
    ls "$SITE/extra/" 2>/dev/null | sed 's/^/    /'
fi

echo "=== HTML documentation built: $SITE/index.html ==="
apt clean
