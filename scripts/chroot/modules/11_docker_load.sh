cat <<'EOF' > /usr/local/bin/planamo-docker-load
#!/bin/bash
set -euo pipefail

LIVE_SRC="/cdrom/docker-images"
INST_SRC="/opt/planamo/docker-images"

is_live_overlay() {
  mount | grep -q " on / type overlay"
}

load_all_from_dir() {
  local SRC="$1"

  [ -d "$SRC" ] || { echo "[!] $SRC not found"; return 1; }
  command -v docker >/dev/null 2>&1 || { echo "[!] docker not found"; return 1; }

  echo "[*] Loading ALL docker images from $SRC"
  shopt -s nullglob

  for tar in "$SRC"/*.tar; do
    echo "[+] docker load -i $tar"
    docker load -i "$tar"
  done

  bases=$(ls "$SRC"/*.tar.part-[0-9][0-9][0-9] 2>/dev/null | sed 's/\.part-...$//' | sort -u || true)
  for base in $bases; do
    echo "[+] docker load (split) from ${base}.part-000..."
    ls "${base}".part-[0-9][0-9][0-9] | sort | cat | docker load
  done

  echo "[OK] Done."
}

load_mobsf_live_only() {
  local SRC="$LIVE_SRC"
  local MOBSF_TAR="$SRC/opensecurity_mobile-security-framework-mobsf_latest.tar"

  [ -f "$MOBSF_TAR" ] || { echo "[!] MobSF tar not found: $MOBSF_TAR"; return 1; }
  command -v dockerd >/dev/null 2>&1 || { echo "[!] dockerd not found"; return 1; }

  echo "[*] Live mode detected (overlay): loading MobSF only (temporary dockerd vfs)"

  sudo systemctl stop docker >/dev/null 2>&1 || true
  sudo rm -rf /tmp/planamo-docker-vfs
  sudo mkdir -p /tmp/planamo-docker-vfs

  sudo dockerd \
    --data-root=/tmp/planamo-docker-vfs \
    --storage-driver=vfs \
    -H unix:///tmp/planamo-docker.sock \
    >/tmp/planamo-dockerd.log 2>&1 &

  for i in {1..30}; do
    if sudo docker -H unix:///tmp/planamo-docker.sock info >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done

  echo "[+] docker load -i $MOBSF_TAR"
  sudo docker -H unix:///tmp/planamo-docker.sock load -i "$MOBSF_TAR"

  echo "[OK] MobSF loaded (live)."
  echo "    Docker socket: /tmp/planamo-docker.sock"
}

main() {
  if is_live_overlay; then
    load_mobsf_live_only
    exit $?
  fi
  load_all_from_dir "$INST_SRC"
}

main "$@"
EOF
chmod +x /usr/local/bin/planamo-docker-load

# --- Wrapper MobSF corrigé ---
# Attend que MobSF soit réellement prêt avant d'ouvrir Firefox
cat <<'EOF' > /usr/local/bin/mobsf
#!/bin/bash
CONTAINER="mobsf"
PORT="8000"
URL="http://127.0.0.1:$PORT"
IMAGE="opensecurity/mobile-security-framework-mobsf:latest"

echo "[*] Démarrage de MobSF..."
docker rm -f "$CONTAINER" 2>/dev/null || true
docker run -d -p ${PORT}:${PORT} --name "$CONTAINER" "$IMAGE"

echo "[*] Attente que MobSF soit prêt (peut prendre 30-60 secondes)..."
TIMEOUT=120
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
  STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$URL" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ] || [ "$STATUS" = "302" ]; then
    echo "[+] MobSF est prêt !"
    break
  fi
  sleep 3
  ELAPSED=$((ELAPSED + 3))
  echo "[*] En attente... ($ELAPSED/${TIMEOUT}s) [HTTP $STATUS]"
done

if [ $ELAPSED -ge $TIMEOUT ]; then
  echo "[!] Timeout — MobSF tarde à démarrer"
fi

echo "[+] MobSF disponible : $URL"
firefox "$URL" >/dev/null 2>&1 &
EOF
chmod +x /usr/local/bin/mobsf

# --- Wrapper REMnux corrigé ---
# Lance avec répertoire partagé et image noble
cat <<'EOF' > /usr/local/bin/remnux
#!/bin/bash
IMAGE="remnux/remnux-distro:noble"
WORKDIR="$HOME/remnux-workdir"

mkdir -p "$WORKDIR"

echo "[*] Lancement de REMnux"
echo "[*] Répertoire partagé : $WORKDIR -> /home/remnux/files"
echo ""

docker run --rm -it \
  -u remnux \
  -v "$WORKDIR":/home/remnux/files \
  --name remnux-session \
  "$IMAGE" bash
EOF
chmod +x /usr/local/bin/remnux

# --- Wrapper MobSF LIVE ---
cat <<'EOF' > /usr/local/bin/mobsf-live
#!/bin/bash
set -euo pipefail

LIVE_SRC="/cdrom/docker-images"
SOCK="unix:///tmp/planamo-docker.sock"
DATA="/tmp/planamo-docker-vfs"
LOG="/tmp/planamo-dockerd.log"

is_live_overlay() {
  mount | grep -q " on / type overlay"
}

start_temp_dockerd() {
  command -v dockerd >/dev/null 2>&1 || { echo "[!] dockerd not found"; exit 1; }

  sudo systemctl stop docker >/dev/null 2>&1 || true
  sudo rm -rf "$DATA"
  sudo mkdir -p "$DATA"
  sudo pkill -f "dockerd.*planamo-docker.sock" >/dev/null 2>&1 || true
  sudo rm -f /tmp/planamo-docker.sock

  sudo dockerd \
    --data-root="$DATA" \
    --storage-driver=vfs \
    -H "$SOCK" \
    >"$LOG" 2>&1 &

  for i in {1..60}; do
    if sudo docker -H "$SOCK" info >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done

  echo "[!] dockerd not ready (see $LOG)"
  exit 1
}

load_mobsf_image() {
  local tar1="$LIVE_SRC/opensecurity_mobile-security-framework-mobsf_latest.tar"
  if [ -f "$tar1" ]; then
    echo "[+] Loading MobSF tar: $tar1"
    sudo docker -H "$SOCK" load -i "$tar1"
    return 0
  fi

  local base
  base="$(ls "$LIVE_SRC"/opensecurity_mobile-security-framework-mobsf_latest.tar.part-000 2>/dev/null | sed 's/\.part-...$//' || true)"
  if [ -n "$base" ]; then
    echo "[+] Loading MobSF split: ${base}.part-000..."
    ls "${base}".part-[0-9][0-9][0-9] | sort | cat | sudo docker -H "$SOCK" load
    return 0
  fi

  echo "[!] MobSF image tar not found in $LIVE_SRC"
  exit 1
}

run_mobsf() {
  sudo docker -H "$SOCK" rm -f mobsf 2>/dev/null || true
  sudo docker -H "$SOCK" run -d -p 8000:8000 --name mobsf \
    opensecurity/mobile-security-framework-mobsf:latest

  echo "[*] Attente que MobSF soit prêt..."
  TIMEOUT=120
  ELAPSED=0
  while [ $ELAPSED -lt $TIMEOUT ]; do
    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ] || [ "$STATUS" = "302" ]; then
      echo "[+] MobSF est prêt !"
      break
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    echo "[*] En attente... ($ELAPSED/${TIMEOUT}s) [HTTP $STATUS]"
  done

  firefox http://127.0.0.1:8000 >/dev/null 2>&1 &
  echo "[+] MobSF running (LIVE): http://127.0.0.1:8000"
  echo "    Docker socket: $SOCK"
}

main() {
  if ! is_live_overlay; then
    echo "[!] Not in live overlay mode. Use: mobsf"
    exit 1
  fi
  start_temp_dockerd
  load_mobsf_image
  run_mobsf
}

main "$@"
EOF
chmod +x /usr/local/bin/mobsf-live
