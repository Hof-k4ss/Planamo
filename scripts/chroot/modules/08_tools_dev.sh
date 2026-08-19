# ------------------------
# Base utilities
# ------------------------
apt install -y \
    terminator \
    ca-certificates \
    curl \
    gnupg \
    tmux \
    lsb-release

# ------------------------
# Docker Official Repo
# ------------------------

install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

chmod a+r /etc/apt/keyrings/docker.gpg

# Détection dynamique du codename Ubuntu (au lieu d'un "noble" en dur) :
# le dépôt Docker officiel met parfois un peu de temps à publier la suite
# correspondant à une release Ubuntu tout juste sortie. On teste la suite
# courante, et on retombe sur la dernière LTS connue de Docker si absente.
DOCKER_CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"

if ! curl -fsSL "https://download.docker.com/linux/ubuntu/dists/${DOCKER_CODENAME}/Release" \
      -o /dev/null 2>/dev/null; then
  echo "[!] Pas de dépôt Docker pour '${DOCKER_CODENAME}', repli sur 'noble'"
  DOCKER_CODENAME="noble"
fi

echo \
  "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu ${DOCKER_CODENAME} stable" \
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

# Fix VS Code sandbox issue (no-sandbox requis en root/live)
sed -i 's|Exec=/usr/share/code/code |Exec=/usr/share/code/code --no-sandbox |g'     /usr/share/applications/code.desktop 2>/dev/null || true

# Installation des extensions VS Code pour l'utilisateur analyste
VSCODE_EXTENSIONS=(
  "bbannier.zeek-language-server"
  "yzhang.markdown-all-in-one"
  "eamodio.gitlens"
  "james-yu.latex-workshop"
  "ms-azuretools.vscode-docker"
  "ms-kubernetes-tools.vscode-kubernetes-tools"
  "ms-python.debugpy"
  "ms-python.python"
  "ms-python.vscode-pylance"
  "ms-toolsai.jupyter"
  "ms-toolsai.jupyter-keymap"
  "ms-toolsai.jupyter-renderers"
  "ms-toolsai.vscode-jupyter-cell-tags"
  "ms-toolsai.vscode-jupyter-slideshow"
  "ms-vscode-remote.remote-containers"
  "ms-vscode-remote.remote-ssh"
  "ms-vscode-remote.remote-ssh-edit"
  "ms-vscode.remote-explorer"
  "njpwerner.autodocstring"
  "redhat.vscode-yaml"
  "splunk.splunk"
  "stamusnetworks.suricata-ls"
)

echo "=== Installing VS Code extensions ==="
for ext in "${VSCODE_EXTENSIONS[@]}"; do
  echo "[*] Installing extension: $ext"
  sudo -u analyste code --no-sandbox --install-extension "$ext"     --extensions-dir /home/analyste/.vscode/extensions     --user-data-dir /home/analyste/.config/Code 2>/dev/null ||   HOME=/home/analyste code --no-sandbox --install-extension "$ext" 2>/dev/null ||   echo "[!] Extension $ext non installée (réseau requis au premier lancement)"
done

# Pré-créer le dossier extensions pour analyste
mkdir -p /home/analyste/.vscode/extensions
mkdir -p /home/analyste/.config/Code/User
chown -R analyste:analyste /home/analyste/.vscode /home/analyste/.config/Code 2>/dev/null || true

# Settings VS Code par défaut
cat > /home/analyste/.config/Code/User/settings.json << 'JSONEOF'
{
  "editor.fontSize": 13,
  "editor.fontFamily": "monospace",
  "editor.tabSize": 4,
  "editor.renderWhitespace": "boundary",
  "terminal.integrated.fontSize": 13,
  "workbench.colorTheme": "Default Dark+",
  "python.defaultInterpreterPath": "/usr/bin/python3",
  "extensions.autoUpdate": false
}
JSONEOF
chown analyste:analyste /home/analyste/.config/Code/User/settings.json 2>/dev/null || true

apt clean
