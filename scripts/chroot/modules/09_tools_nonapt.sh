#!/bin/bash
# =============================================================================
# 09_tools_nonapt.sh — Outils non disponibles via apt
# =============================================================================
set -ex

echo "=== Installing Non-APT Tools ==="

export DEBIAN_FRONTEND=noninteractive

apt install -y \
    wget \
    unzip \
    git \
    python3-venv \
    python3-pip \
    python3-tk \
    ca-certificates \
    fuse3 \
    default-jdk-headless

mkdir -p /opt/planamo/tools
mkdir -p /opt/planamo/venvs
mkdir -p /opt/planamo/wrappers

# =============================================================================
# JADX
# =============================================================================
echo "=== Installing JADX ==="

JADX_DIR="/opt/planamo/tools/jadx"
JADX_VERSION="1.5.5"
JADX_URL="https://github.com/skylot/jadx/releases/download/v${JADX_VERSION}/jadx-${JADX_VERSION}.zip"

mkdir -p "$JADX_DIR"
cd "$JADX_DIR"

wget -O jadx.zip "$JADX_URL"
[ -s jadx.zip ] || { echo "ERROR: JADX download failed"; exit 1; }

unzip -q -o jadx.zip
rm -f jadx.zip

chmod +x "$JADX_DIR/bin/"*

[ -f "$JADX_DIR/bin/jadx" ]     || { echo "ERROR: jadx binary not found"; exit 1; }
[ -f "$JADX_DIR/bin/jadx-gui" ] || { echo "ERROR: jadx-gui binary not found"; exit 1; }

ln -sf "$JADX_DIR/bin/jadx"     /usr/local/bin/jadx
ln -sf "$JADX_DIR/bin/jadx-gui" /usr/local/bin/jadx-gui

echo "[OK] JADX $JADX_VERSION (jadx + jadx-gui)"

# =============================================================================
# RIZIN
# =============================================================================
echo "=== Building Rizin ==="

apt install -y \
    build-essential meson ninja-build pkg-config \
    libssl-dev libzip-dev libzstd-dev liblz4-dev libpcre2-dev libmagic-dev

RIZIN_SRC="/opt/planamo/tools/rizin-src"
RIZIN_VERSION="0.8.2"
RIZIN_URL="https://github.com/rizinorg/rizin/archive/refs/tags/v${RIZIN_VERSION}.tar.gz"

mkdir -p "$RIZIN_SRC"
cd "$RIZIN_SRC"

wget -O rizin.tar.gz "$RIZIN_URL"
[ -s rizin.tar.gz ] || { echo "ERROR: Rizin download failed"; exit 1; }

tar -xzf rizin.tar.gz
rm -f rizin.tar.gz

cd "rizin-${RIZIN_VERSION}"
meson setup build --prefix=/opt/planamo/tools/rizin --buildtype=release
ninja -C build
ninja -C build install

[ -f /opt/planamo/tools/rizin/bin/rizin ] || { echo "ERROR: Rizin binary not found"; exit 1; }
ln -sf /opt/planamo/tools/rizin/bin/rizin /usr/local/bin/rizin

echo "[OK] Rizin installed"

# =============================================================================
# FRIDA
# =============================================================================
echo "=== Installing Frida ==="

python3 -m venv /opt/planamo/venvs/frida
/opt/planamo/venvs/frida/bin/pip install --upgrade pip
/opt/planamo/venvs/frida/bin/pip install frida-tools

cat > /opt/planamo/wrappers/frida << 'EOF'
#!/bin/bash
source /opt/planamo/venvs/frida/bin/activate
exec frida "$@"
EOF
chmod +x /opt/planamo/wrappers/frida
ln -sf /opt/planamo/wrappers/frida /usr/local/bin/frida

echo "[OK] Frida installed"

# =============================================================================
# VOLATILITY3
# =============================================================================
echo "=== Installing Volatility3 ==="

python3 -m venv /opt/planamo/venvs/volatility3
/opt/planamo/venvs/volatility3/bin/pip install --upgrade pip
/opt/planamo/venvs/volatility3/bin/pip install volatility3

cat > /opt/planamo/wrappers/volatility3 << 'EOF'
#!/bin/bash
source /opt/planamo/venvs/volatility3/bin/activate
exec vol "$@"
EOF
chmod +x /opt/planamo/wrappers/volatility3
ln -sf /opt/planamo/wrappers/volatility3 /usr/local/bin/volatility3

echo "[OK] Volatility3 installed"

# =============================================================================
# ALEAPP
# =============================================================================
echo "=== Installing ALEAPP (git clone) ==="

ALEAPP_DST="/opt/planamo/tools/aleapp"
ALEAPP_VENV="/opt/planamo/venvs/aleapp"

rm -rf "$ALEAPP_DST"
git clone --depth=1 https://github.com/abrignoni/ALEAPP.git "$ALEAPP_DST"

python3 -m venv "$ALEAPP_VENV"
"$ALEAPP_VENV/bin/pip" install --upgrade pip

if [ -f "$ALEAPP_DST/requirements.txt" ]; then
    "$ALEAPP_VENV/bin/pip" install -r "$ALEAPP_DST/requirements.txt"
else
    "$ALEAPP_VENV/bin/pip" install \
        PyQt5 python-dateutil jinja2 pillow xlsxwriter simplekml six chardet
fi

# FIX GUI : certains chemins sont résolus depuis le venv
if [ -d "$ALEAPP_DST/assets" ]; then
    rm -rf "$ALEAPP_VENV/assets"
    ln -s "$ALEAPP_DST/assets" "$ALEAPP_VENV/assets"
fi

cat > /opt/planamo/wrappers/aleapp << EOF
#!/bin/bash
cd "$ALEAPP_DST"
source "$ALEAPP_VENV/bin/activate"
exec python3 "$ALEAPP_DST/aleapp.py" "\$@"
EOF
chmod +x /opt/planamo/wrappers/aleapp
ln -sf /opt/planamo/wrappers/aleapp /usr/local/bin/aleapp

if [ -f "$ALEAPP_DST/aleappGUI.py" ]; then
    cat > /opt/planamo/wrappers/aleapp-gui << EOF
#!/bin/bash
cd "$ALEAPP_DST"
source "$ALEAPP_VENV/bin/activate"
exec python3 "$ALEAPP_DST/aleappGUI.py" "\$@"
EOF
    chmod +x /opt/planamo/wrappers/aleapp-gui
    ln -sf /opt/planamo/wrappers/aleapp-gui /usr/local/bin/aleapp-gui
    echo "[OK] ALEAPP + ALEAPP GUI installed"
else
    echo "[OK] ALEAPP installed (no GUI found)"
fi

# =============================================================================
# iLEAPP
# =============================================================================
echo "=== Installing iLEAPP (git clone) ==="

ILEAPP_DST="/opt/planamo/tools/ileapp"
ILEAPP_VENV="/opt/planamo/venvs/ileapp"

rm -rf "$ILEAPP_DST"
git clone --depth=1 https://github.com/abrignoni/iLEAPP.git "$ILEAPP_DST"

python3 -m venv "$ILEAPP_VENV"
"$ILEAPP_VENV/bin/pip" install --upgrade pip

if [ -f "$ILEAPP_DST/requirements.txt" ]; then
    "$ILEAPP_VENV/bin/pip" install -r "$ILEAPP_DST/requirements.txt"
else
    "$ILEAPP_VENV/bin/pip" install \
        PyQt5 python-dateutil jinja2 pillow xlsxwriter simplekml six chardet \
        blackboxprotobuf
fi

# FIX GUI : certains chemins sont résolus depuis le venv
if [ -d "$ILEAPP_DST/assets" ]; then
    rm -rf "$ILEAPP_VENV/assets"
    ln -s "$ILEAPP_DST/assets" "$ILEAPP_VENV/assets"
fi

cat > /opt/planamo/wrappers/ileapp << EOF
#!/bin/bash
cd "$ILEAPP_DST"
source "$ILEAPP_VENV/bin/activate"
exec python3 "$ILEAPP_DST/ileapp.py" "\$@"
EOF
chmod +x /opt/planamo/wrappers/ileapp
ln -sf /opt/planamo/wrappers/ileapp /usr/local/bin/ileapp

if [ -f "$ILEAPP_DST/ileappGUI.py" ]; then
    cat > /opt/planamo/wrappers/ileapp-gui << EOF
#!/bin/bash
cd "$ILEAPP_DST"
source "$ILEAPP_VENV/bin/activate"
exec python3 "$ILEAPP_DST/ileappGUI.py" "\$@"
EOF
    chmod +x /opt/planamo/wrappers/ileapp-gui
    ln -sf /opt/planamo/wrappers/ileapp-gui /usr/local/bin/ileapp-gui
    echo "[OK] iLEAPP + iLEAPP GUI installed"
else
    echo "[OK] iLEAPP installed (no GUI found)"
fi

# =============================================================================
# BULK_EXTRACTOR — extraction d'artefacts forensiques depuis images disque
# Compilé depuis les sources (pas de binaire précompilé disponible)
# =============================================================================
echo "=== Installing bulk_extractor (git clone + build) ==="

apt install -y \
    build-essential cmake git \
    libssl-dev libewf-dev libexpat1-dev \
    libsqlite3-dev libbz2-dev zlib1g-dev \
    libpcap-dev

BULK_DST="/opt/planamo/tools/bulk_extractor"

git clone --depth=1 https://github.com/simsong/bulk_extractor.git "$BULK_DST"

cd "$BULK_DST"

# Initialiser les sous-modules (requis par bulk_extractor)
git submodule update --init --recursive

mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local
make -j$(nproc)
make install

# Vérification
which bulk_extractor && bulk_extractor --version | head -1 || \
    { echo "ERROR: bulk_extractor install failed"; exit 1; }

echo "[OK] bulk_extractor installed"

apt clean
