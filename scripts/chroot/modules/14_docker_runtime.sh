#!/bin/bash
set -e

echo "=== Docker Runtime Setup ==="

cat <<'EOF' > /usr/local/bin/planamo-docker-init
#!/bin/bash

DOCKER_IMAGE_DIR="/opt/planamo/docker-images"
MARKER="/opt/planamo/.docker_initialized"

if [ -f "$MARKER" ]; then
    exit 0
fi

sleep 5

if systemctl is-active --quiet docker; then
    for file in "$DOCKER_IMAGE_DIR"/*.tar; do
        [ -f "$file" ] || continue
        echo "Loading Docker image: $file"
        docker load -i "$file"
        rm -f "$file"
    done

    touch "$MARKER"
fi
EOF

chmod +x /usr/local/bin/planamo-docker-init

cat <<EOF > /etc/systemd/system/planamo-docker-init.service
[Unit]
Description=Planamo Docker First Boot Initialization
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/planamo-docker-init

[Install]
WantedBy=multi-user.target
EOF

systemctl enable planamo-docker-init.service

echo "Docker runtime service installed."
