#!/bin/bash
set -e

echo "=== Creating Docker Offline Loader ==="

mkdir -p /opt/planamo/scripts

cat <<EOF > /opt/planamo/scripts/load-docker-images.sh
#!/bin/bash

echo "Loading offline Docker images..."

for image in /opt/planamo/docker-images/*.tar; do
    echo "Loading \$image"
    docker load -i "\$image"
done

echo "Docker images loaded."
EOF

chmod +x /opt/planamo/scripts/load-docker-images.sh
