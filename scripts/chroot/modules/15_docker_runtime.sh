#!/bin/bash
set -e

echo "=== Configuring Docker Runtime ==="

mkdir -p /opt/planamo/docker

# ---------------------------------
# Script de chargement offline
# ---------------------------------
cat <<EOF > /opt/planamo/docker/load-images.sh
#!/bin/bash

echo "Loading Planamo Docker images..."

for image in /opt/planamo/docker-images/*.tar; do
    echo "Loading \$image"
    docker load -i "\$image"
done

echo "All images loaded."
EOF

chmod +x /opt/planamo/docker/load-images.sh

# ---------------------------------
# Wrapper MobSF
# ---------------------------------
cat <<EOF > /opt/planamo/docker/mobsf.sh
#!/bin/bash

docker run -d \
  -p 8000:8000 \
  --name mobsf \
  opensecurity/mobile-security-framework-mobsf:latest

sleep 8
firefox http://127.0.0.1:8000 &
EOF

chmod +x /opt/planamo/docker/mobsf.sh
ln -sf /opt/planamo/docker/mobsf.sh /usr/local/bin/mobsf

# ---------------------------------
# Wrapper REMnux
# ---------------------------------
cat <<EOF > /opt/planamo/docker/remnux.sh
#!/bin/bash

docker run -it \
  --rm \
  remnux/remnux-distro:latest
EOF

chmod +x /opt/planamo/docker/remnux.sh
ln -sf /opt/planamo/docker/remnux.sh /usr/local/bin/remnux
