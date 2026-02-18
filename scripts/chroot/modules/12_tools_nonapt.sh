#!/bin/bash
set -ex

echo "=== Installing Non-APT Tools ==="

export DEBIAN_FRONTEND=noninteractive
apt update || true

apt install -y \
    wget \
    unzip \
    python3-venv \
    python3-pip

mkdir -p /opt/planamo/tools
mkdir -p /opt/planamo/venvs
mkdir -p /opt/planamo/wrappers

# -----------------------
# JADx
# -----------------------

mkdir -p /opt/planamo/tools/jadx
cd /opt/planamo/tools/jadx

JADX_VERSION="1.5.0"
JADX_URL="https://github.com/skylot/jadx/releases/download/v${JADX_VERSION}/jadx-${JADX_VERSION}.zip"

echo "Downloading JADX ${JADX_VERSION}..."

wget -O jadx.zip "$JADX_URL"

# Vérification que le fichier n'est pas vide
if [ ! -s jadx.zip ]; then
    echo "ERROR: JADX download failed or empty file."
    exit 1
fi

echo "Extracting JADX..."
unzip -q jadx.zip
rm jadx.zip

# Symlink global
if [ -f /opt/planamo/tools/jadx/bin/jadx ]; then
    ln -sf /opt/planamo/tools/jadx/bin/jadx /usr/local/bin/jadx
else
    echo "ERROR: JADX binary not found after extraction."
    exit 1
fi

# -----------------------
# FRIDA
# -----------------------

python3 -m venv /opt/planamo/venvs/frida
/opt/planamo/venvs/frida/bin/pip install --upgrade pip
/opt/planamo/venvs/frida/bin/pip install frida-tools

cat <<EOF > /opt/planamo/wrappers/frida
#!/bin/bash
source /opt/planamo/venvs/frida/bin/activate
frida "\$@"
EOF

chmod +x /opt/planamo/wrappers/frida
ln -sf /opt/planamo/wrappers/frida /usr/local/bin/frida

# -----------------------
# VOLATILITY3
# -----------------------

python3 -m venv /opt/planamo/venvs/volatility3
/opt/planamo/venvs/volatility3/bin/pip install --upgrade pip
/opt/planamo/venvs/volatility3/bin/pip install volatility3

cat <<EOF > /opt/planamo/wrappers/volatility3
#!/bin/bash
source /opt/planamo/venvs/volatility3/bin/activate
vol "\$@"
EOF

chmod +x /opt/planamo/wrappers/volatility3
ln -sf /opt/planamo/wrappers/volatility3 /usr/local/bin/volatility3

apt clean
