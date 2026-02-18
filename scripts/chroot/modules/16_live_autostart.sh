#!/bin/bash
set -e

echo "=== Configuring Live Autostart ==="

# Wrapper MobSF propre (évite double lancement)
cat <<'EOF' > /usr/local/bin/mobsf
#!/bin/bash

if ! docker ps | grep -q mobile-security-framework-mobsf; then
    docker run -d -p 8000:8000 opensecurity/mobile-security-framework-mobsf
    sleep 8
fi

firefox http://127.0.0.1:8000 &
EOF

chmod +x /usr/local/bin/mobsf

mkdir -p /etc/xdg/autostart

cat <<EOF > /etc/xdg/autostart/planamo-mobsf.desktop
[Desktop Entry]
Type=Application
Exec=/usr/local/bin/mobsf
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Planamo MobSF
Comment=Auto start MobSF on Live boot
EOF

echo "Live autostart configured."
