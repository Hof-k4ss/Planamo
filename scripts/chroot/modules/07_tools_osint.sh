#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== Installing OSINT tools ==="

apt update

apt install -y \
  proxychains4 \
  tor \
  torsocks \
  curl \
  wget \
  jq \
  ripgrep \
  whois \
  dnsutils \
  python3-pip \
  python3-venv \
  git \
  ca-certificates

# =============================
# Firefox (official Mozilla tar)
# =============================

echo "=== Installing Firefox (Mozilla tarball) ==="

# Firefox téléchargé par Mozilla = tar.xz -> besoin de xz-utils
apt install -y tar xz-utils libgtk-3-0t64 libdbus-glib-1-2 libasound2t64 || true

cd /tmp

# Téléchargement officiel Mozilla (64-bit Linux)
wget -O firefox.tar.xz "https://download.mozilla.org/?product=firefox-latest&os=linux64&lang=fr"

if [ ! -s firefox.tar.xz ]; then
  echo "ERROR: Firefox download failed"
  exit 1
fi

# Installation propre dans /opt
rm -rf /opt/firefox
tar -xJf firefox.tar.xz -C /opt/
rm -f firefox.tar.xz

# Lien global
ln -sf /opt/firefox/firefox /usr/local/bin/firefox

# Desktop entry
cat > /usr/share/applications/firefox.desktop <<'EOF'
[Desktop Entry]
Name=Firefox
Exec=firefox
Icon=/opt/firefox/browser/chrome/icons/default/default128.png
Terminal=false
Type=Application
Categories=Network;
OnlyShowIn=XFCE;
EOF

echo "=== Firefox installed successfully ==="

# =============================
# Tor Browser (official tar - pinned)
# =============================

echo "=== Installing Tor Browser (official tarball) ==="

apt install -y wget tar xz-utils ca-certificates || true

cd /tmp

TB_URL="https://www.torproject.org/dist/torbrowser/15.0.7/tor-browser-linux-x86_64-15.0.7.tar.xz"

echo "[*] Tor Browser URL: $TB_URL"
wget -O torbrowser.tar.xz "$TB_URL"

if [ ! -s torbrowser.tar.xz ]; then
  echo "ERROR: Tor Browser download failed"
  exit 1
fi

rm -rf /opt/tor-browser
mkdir -p /opt/tor-browser
tar -xJf torbrowser.tar.xz -C /opt/tor-browser --strip-components=1
rm -f torbrowser.tar.xz

ln -sf /opt/tor-browser/Browser/start-tor-browser /usr/local/bin/tor-browser

cat > /usr/share/applications/tor-browser.desktop <<'EOF'
[Desktop Entry]
Name=Tor Browser
Exec=/opt/tor-browser/Browser/start-tor-browser --detach
Icon=/opt/tor-browser/Browser/browser/chrome/icons/default/default128.png
Terminal=false
Type=Application
Categories=Network;
OnlyShowIn=XFCE;
EOF

echo "=== Tor Browser installed successfully ==="

apt clean
