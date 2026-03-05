#!/bin/bash
set -ex

echo "=== Installing Non-APT Tools ==="

export DEBIAN_FRONTEND=noninteractive

apt install -y \
    wget \
    unzip \
    python3-venv \
    python3-pip \
    ca-certificates \
    fuse3

mkdir -p /opt/planamo/tools
mkdir -p /opt/planamo/venvs
mkdir -p /opt/planamo/wrappers

# -----------------------
# JADX
# -----------------------

mkdir -p /opt/planamo/tools/jadx
cd /opt/planamo/tools/jadx

JADX_VERSION="1.5.0"
JADX_URL="https://github.com/skylot/jadx/releases/download/v${JADX_VERSION}/jadx-${JADX_VERSION}.zip"

echo "Downloading JADX ${JADX_VERSION}..."
wget -O jadx.zip "$JADX_URL"

if [ ! -s jadx.zip ]; then
    echo "ERROR: JADX download failed or empty file."
    exit 1
fi

echo "Extracting JADX..."
unzip -q -o jadx.zip
rm -f jadx.zip

# Symlinks globaux
if [ -f /opt/planamo/tools/jadx/bin/jadx ]; then
    ln -sf /opt/planamo/tools/jadx/bin/jadx /usr/local/bin/jadx
else
    echo "ERROR: JADX binary not found after extraction."
    exit 1
fi

if [ -f /opt/planamo/tools/jadx/bin/jadx-gui ]; then
    ln -sf /opt/planamo/tools/jadx/bin/jadx-gui /usr/local/bin/jadx-gui
fi

# -----------------------
# RIZIN (build from source)
# -----------------------

echo "=== Building Rizin from source ==="

apt install -y \
  build-essential \
  meson \
  ninja-build \
  pkg-config \
  git \
  libssl-dev \
  libzip-dev \
  libzstd-dev \
  liblz4-dev \
  libpcre2-dev \
  libmagic-dev

mkdir -p /opt/planamo/tools/rizin-src
cd /opt/planamo/tools/rizin-src

RIZIN_VERSION="0.8.2"
RIZIN_TARBALL_URL="https://github.com/rizinorg/rizin/archive/refs/tags/v${RIZIN_VERSION}.tar.gz"

echo "Downloading Rizin ${RIZIN_VERSION} sources..."
wget -O rizin.tar.gz "$RIZIN_TARBALL_URL"

if [ ! -s rizin.tar.gz ]; then
  echo "ERROR: Rizin source download failed or empty file."
  exit 1
fi

rm -rf "rizin-${RIZIN_VERSION}"
tar -xzf rizin.tar.gz
rm -f rizin.tar.gz

cd "rizin-${RIZIN_VERSION}"

echo "Building Rizin..."
meson setup build --prefix=/opt/planamo/tools/rizin --buildtype=release
ninja -C build
ninja -C build install

# Symlink global
if [ -f /opt/planamo/tools/rizin/bin/rizin ]; then
  ln -sf /opt/planamo/tools/rizin/bin/rizin /usr/local/bin/rizin
else
  echo "ERROR: Rizin binary not found after install."
  exit 1
fi

echo "=== Rizin $(rizin -v 2>/dev/null | head -1) installed ==="

# -----------------------
# FRIDA
# -----------------------

python3 -m venv /opt/planamo/venvs/frida
/opt/planamo/venvs/frida/bin/pip install --upgrade pip
/opt/planamo/venvs/frida/bin/pip install frida-tools

cat <<'EOF' > /opt/planamo/wrappers/frida
#!/bin/bash
source /opt/planamo/venvs/frida/bin/activate
exec frida "$@"
EOF

chmod +x /opt/planamo/wrappers/frida
ln -sf /opt/planamo/wrappers/frida /usr/local/bin/frida

# -----------------------
# VOLATILITY3
# -----------------------

python3 -m venv /opt/planamo/venvs/volatility3
/opt/planamo/venvs/volatility3/bin/pip install --upgrade pip
/opt/planamo/venvs/volatility3/bin/pip install volatility3

cat <<'EOF' > /opt/planamo/wrappers/volatility3
#!/bin/bash
source /opt/planamo/venvs/volatility3/bin/activate
exec vol "$@"
EOF

chmod +x /opt/planamo/wrappers/volatility3
ln -sf /opt/planamo/wrappers/volatility3 /usr/local/bin/volatility3

apt clean
