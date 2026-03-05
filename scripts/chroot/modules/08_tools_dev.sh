#!/bin/bash
set -e

echo "=== Installing Dev Tools (Docker, VSCode, Terminator) ==="

apt update

# ------------------------
# Base utilities
# ------------------------
apt install -y \
    terminator \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# ------------------------
# Docker Official Repo
# ------------------------

install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu noble stable" \
  > /etc/apt/sources.list.d/docker.list

apt update

apt install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

systemctl enable docker
usermod -aG docker analyste

# ------------------------
# VS Code Official Repo
# ------------------------

curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg

chmod a+r /etc/apt/keyrings/microsoft.gpg

echo \
  "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] \
  https://packages.microsoft.com/repos/code stable main" \
  > /etc/apt/sources.list.d/vscode.list

apt update

apt install -y code

# Fix VS Code sandbox issue in live environment
#sed -i 's|Exec=/usr/share/code/code|Exec=/usr/share/code/code --no-sandbox|g' \
#    /usr/share/applications/code.desktop

apt clean
