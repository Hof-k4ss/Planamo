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

apt install -y tar xz-utils libgtk-3-0t64 libdbus-glib-1-2 libasound2t64 || true

cd /tmp

wget -O firefox.tar.xz "https://download.mozilla.org/?product=firefox-latest&os=linux64&lang=fr"

if [ ! -s firefox.tar.xz ]; then
  echo "ERROR: Firefox download failed"
  exit 1
fi

rm -rf /opt/firefox
tar -xJf firefox.tar.xz -C /opt/
rm -f firefox.tar.xz

ln -sf /opt/firefox/firefox /usr/local/bin/firefox

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

# Enregistrer Firefox comme navigateur par defaut (exo-open / XFCE)
update-alternatives --install /usr/bin/x-www-browser x-www-browser /usr/local/bin/firefox 100 || true
update-alternatives --set x-www-browser /usr/local/bin/firefox || true

mkdir -p /usr/share/xfce4/helpers
cat > /usr/share/xfce4/helpers/custom-WebBrowser.desktop << 'HELPEREOF'
[Desktop Entry]
NoDisplay=true
Version=0.9.0
Type=X-XFCE-Helper
X-XFCE-Binaries=firefox;
X-XFCE-Category=WebBrowser
X-XFCE-CommandsWithParameter=firefox "%s";
Icon=firefox
Name=Firefox
X-XFCE-Commands=firefox;
HELPEREOF

mkdir -p /etc/xdg/xfce4
cat > /etc/xdg/xfce4/helpers.rc << 'HELPEREOF'
WebBrowser=custom-WebBrowser
HELPEREOF

# =============================
# Tor Browser (latest via API)
# =============================

echo "=== Installing Tor Browser (latest) ==="

apt install -y wget tar xz-utils ca-certificates jq || true

TB_FALLBACK_VERSION="15.0.7"

echo "[*] Fetching latest Tor Browser version from API..."
TB_VERSION=$(curl -sf --max-time 15 \
  "https://aus1.torproject.org/torbrowser/update_3/release/downloads.json" \
  | jq -r '.version' 2>/dev/null || true)

if [ -z "$TB_VERSION" ]; then
  echo "[!] API unreachable, falling back to version $TB_FALLBACK_VERSION"
  TB_VERSION="$TB_FALLBACK_VERSION"
else
  echo "[*] Latest Tor Browser version: $TB_VERSION"
fi

TB_URL="https://www.torproject.org/dist/torbrowser/${TB_VERSION}/tor-browser-linux-x86_64-${TB_VERSION}.tar.xz"

echo "[*] Downloading: $TB_URL"
cd /tmp
wget -O torbrowser.tar.xz "$TB_URL"

if [ ! -s torbrowser.tar.xz ]; then
  echo "ERROR: Tor Browser download failed (version $TB_VERSION)"
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

echo "=== Tor Browser $TB_VERSION installed successfully ==="

apt clean
