#!/bin/bash
# =============================================================================
# 10_tools_custom.sh — Installation des outils personnalisés depuis /root/outils/
# =============================================================================
#
# COMMENT AJOUTER UN NOUVEL OUTIL :
# ----------------------------------
# 1. Copiez votre outil dans le dossier outils/ du repo :
#    - Un binaire seul      → outils/mon-outil/mon-outil-linux-amd64
#    - Un dossier complet   → outils/mon-outil/
#    - Une archive .7z      → outils/mon-outil/archive.7z
#
# 2. Ajoutez une ligne dans scripts/chroot/tools_map.conf :
#    Mon Outil|mon-outil|Mobile Analysis|terminal|Description courte
#
# 3. Si votre outil nécessite une installation spéciale (venv Python, etc.),
#    ajoutez un bloc INSTALL dans ce script en copiant le pattern existant.
#
# STRUCTURE /root/outils/ (copiée depuis outils/ du repo) :
#   androidqf/
#     androidqf_v1.7.0_linux_amd64    ← binaire direct
#   calid_pcr/
#     CALID_PCR_Android.7z             ← archive (copiée telle quelle)
#   mvt/
#     20250317_mvt-extended/           ← dossier source Python (pip install)
#
# VARIABLES D'ENVIRONNEMENT DISPONIBLES :
#   TOOLS_DIR   = /opt/planamo/tools/mobile   (destination des binaires)
#   VENVS_DIR   = /opt/planamo/venvs          (environnements Python)
#   WRAPPERS_DIR = /opt/planamo/wrappers      (scripts wrapper → /usr/local/bin/)
# =============================================================================
set -e

echo "=== Installing Custom Tools from /root/outils/ ==="

# --- Répertoires cibles ---
TOOLS_DIR="/opt/planamo/tools/mobile"
VENVS_DIR="/opt/planamo/venvs"
WRAPPERS_DIR="/opt/planamo/wrappers"

mkdir -p "$TOOLS_DIR"
mkdir -p "$VENVS_DIR"
mkdir -p "$WRAPPERS_DIR"

# =============================================================================
# FONCTION UTILITAIRE : créer un wrapper terminal pour un binaire
# Usage : make_wrapper <nom_commande> <chemin_binaire>
# Crée /opt/planamo/wrappers/<nom> et le symlink dans /usr/local/bin/
# =============================================================================
make_wrapper() {
    local name="$1"     # nom de la commande (ex: androidqf)
    local binary="$2"   # chemin complet vers le binaire (ex: /opt/planamo/tools/mobile/androidqf/androidqf_v1.7.0_linux_amd64)

    chmod +x "$binary"

    cat > "$WRAPPERS_DIR/$name" << WEOF
#!/bin/bash
# Wrapper auto-généré pour $name
exec "$binary" "\$@"
WEOF
    chmod +x "$WRAPPERS_DIR/$name"

    # Symlink global (écrase si déjà existant)
    ln -sf "$WRAPPERS_DIR/$name" "/usr/local/bin/$name"
    echo "[OK] $name → $binary"
}

# =============================================================================
# FONCTION UTILITAIRE : créer un wrapper pour un outil dans un venv Python
# Usage : make_venv_wrapper <nom_commande> <chemin_venv>
# Le venv doit déjà contenir la commande dans son bin/
# =============================================================================
make_venv_wrapper() {
    local name="$1"     # nom de la commande dans le venv (ex: mvt-android)
    local venv="$2"     # chemin du venv (ex: /opt/planamo/venvs/mvt)
    local cmd="${3:-$name}"  # commande dans le venv si différente du nom

    cat > "$WRAPPERS_DIR/$name" << WEOF
#!/bin/bash
# Wrapper auto-généré pour $name (venv Python)
source "$venv/bin/activate"
exec $cmd "\$@"
WEOF
    chmod +x "$WRAPPERS_DIR/$name"
    ln -sf "$WRAPPERS_DIR/$name" "/usr/local/bin/$name"
    echo "[OK] $name → $venv (cmd: $cmd)"
}

# =============================================================================
# ANDROIDQF
# Binaire unique Linux amd64 — copié depuis outils/androidqf/
# =============================================================================
echo "--- Installing AndroidQF ---"

ANDROIDQF_SRC="/root/outils/androidqf"
ANDROIDQF_DST="$TOOLS_DIR/androidqf"

mkdir -p "$ANDROIDQF_DST"
cp -r "$ANDROIDQF_SRC"/. "$ANDROIDQF_DST/"

# Trouver le binaire (supporte n'importe quel nom de version)
ANDROIDQF_BIN=$(find "$ANDROIDQF_DST" -maxdepth 1 -type f -name "androidqf*linux*amd64" | head -1)

if [ -z "$ANDROIDQF_BIN" ]; then
    echo "[!] Binaire androidqf introuvable dans $ANDROIDQF_DST — skip"
else
    make_wrapper "androidqf" "$ANDROIDQF_BIN"
fi

# =============================================================================
# CALID_PCR
# Archive — copiée telle quelle (pas de lancement direct en ligne de commande)
# Pour ajouter un wrapper : make_wrapper "calid" "$TOOLS_DIR/calid_pcr/calid_binary"
# =============================================================================
echo "--- Installing CALID_PCR ---"

cp -r /root/outils/calid_pcr "$TOOLS_DIR/"
echo "[OK] CALID_PCR copié dans $TOOLS_DIR/calid_pcr/"

# =============================================================================
# MVT (Mobile Verification Toolkit)
# Installation via pip dans un venv Python dédié
# Source : outils/mvt/<dossier_mvt-extended>/
# =============================================================================
echo "--- Installing MVT (Python venv) ---"

MVT_SRC_DIR=$(find /root/outils/mvt -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)

if [ -z "$MVT_SRC_DIR" ]; then
    echo "[!] Dossier MVT introuvable dans /root/outils/mvt/ — skip"
else
    MVT_DST="$TOOLS_DIR/mvt"
    cp -r "$MVT_SRC_DIR" "$MVT_DST"
    echo "[*] MVT source : $MVT_SRC_DIR → $MVT_DST"

    # Création du venv Python dédié
    python3 -m venv "$VENVS_DIR/mvt"

    # Installation des dépendances et du package MVT
    "$VENVS_DIR/mvt/bin/pip" install --upgrade pip
    "$VENVS_DIR/mvt/bin/pip" install libusb1 sqlite-utils
    "$VENVS_DIR/mvt/bin/pip" install "$MVT_DST"

    # Wrappers pour les deux commandes MVT
    make_venv_wrapper "mvt-android" "$VENVS_DIR/mvt"
    make_venv_wrapper "mvt-ios"     "$VENVS_DIR/mvt"
fi

# =============================================================================
# AJOUT D'UN NOUVEL OUTIL — EXEMPLE (décommentez et adaptez) :
# =============================================================================
#
# Exemple 1 : binaire direct depuis outils/mon-outil/
# ---------------------------------------------------
# MON_BIN=$(find /root/outils/mon-outil -maxdepth 1 -type f -executable | head -1)
# mkdir -p "$TOOLS_DIR/mon-outil"
# cp -r /root/outils/mon-outil/. "$TOOLS_DIR/mon-outil/"
# make_wrapper "mon-outil" "$TOOLS_DIR/mon-outil/$(basename "$MON_BIN")"
#
# Exemple 2 : outil Python depuis outils/mon-outil/ (pip installable)
# --------------------------------------------------------------------
# python3 -m venv "$VENVS_DIR/mon-outil"
# "$VENVS_DIR/mon-outil/bin/pip" install "$TOOLS_DIR/mon-outil"
# make_venv_wrapper "mon-outil" "$VENVS_DIR/mon-outil"
#
# N'oubliez pas d'ajouter la ligne dans tools_map.conf !
# =============================================================================

echo "=== Custom tools installed ==="
