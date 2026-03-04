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

  # 1) .tar simples
  for tar in "$SRC"/*.tar; do
    echo "[+] docker load -i $tar"
    docker load -i "$tar"
  done

  # 2) split numériques: *.tar.part-000 ...
  bases=$(ls "$SRC"/*.tar.part-[0-9][0-9][0-9] 2>/dev/null | sed 's/\.part-...$//' | sort -u || true)
  for base in $bases; do
    echo "[+] docker load (split) from ${base}.part-000..."
    ls "${base}".part-[0-9][0-9][0-9] | sort | cat | docker load
  done

  echo "[✓] Done."
}

load_mobsf_live_only() {
  local SRC="$LIVE_SRC"
  local MOBSF_TAR="$SRC/opensecurity_mobile-security-framework-mobsf_latest.tar"

  [ -f "$MOBSF_TAR" ] || { echo "[!] MobSF tar not found: $MOBSF_TAR"; return 1; }
  command -v dockerd >/dev/null 2>&1 || { echo "[!] dockerd not found"; return 1; }

  echo "[*] Live mode detected (overlay): loading MobSF only (temporary dockerd vfs)"

  # stop docker service if present
  sudo systemctl stop docker >/dev/null 2>&1 || true

  sudo rm -rf /tmp/planamo-docker-vfs
  sudo mkdir -p /tmp/planamo-docker-vfs

  # start temporary dockerd
  sudo dockerd \
    --data-root=/tmp/planamo-docker-vfs \
    --storage-driver=vfs \
    -H unix:///tmp/planamo-docker.sock \
    >/tmp/planamo-dockerd.log 2>&1 &

  # wait until ready
  for i in {1..30}; do
    if sudo docker -H unix:///tmp/planamo-docker.sock info >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done

  echo "[+] docker load -i $MOBSF_TAR"
  sudo docker -H unix:///tmp/planamo-docker.sock load -i "$MOBSF_TAR"

  echo "[✓] MobSF loaded (live)."
  echo "    Docker socket: /tmp/planamo-docker.sock"
}

main() {
  if is_live_overlay; then
    load_mobsf_live_only
    exit $?
  fi

  # système installé
  load_all_from_dir "$INST_SRC"
}

main "$@"
EOF

chmod +x /usr/local/bin/planamo-docker-load

# --- Wrapper MobSF ---
cat <<'EOF' > /usr/local/bin/mobsf
#!/bin/bash
set -e

# Démarre MobSF (assume image déjà loadée)
docker rm -f mobsf 2>/dev/null || true
docker run -d -p 8000:8000 --name mobsf opensecurity/mobile-security-framework-mobsf:latest

sleep 5
firefox http://127.0.0.1:8000 >/dev/null 2>&1 || true
echo "[+] MobSF running: http://127.0.0.1:8000"
EOF
chmod +x /usr/local/bin/mobsf

# --- Wrapper REMnux ---
cat <<'EOF' > /usr/local/bin/remnux
#!/bin/bash
set -e

# Shell interactif dans REMnux (assume image déjà loadée)
docker run --rm -it remnux/remnux-distro:latest bash
EOF
chmod +x /usr/local/bin/remnux

# --- Wrapper MobSF (LIVE) ---
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

  # kill old dockerd if any
  sudo pkill -f "dockerd.*planamo-docker.sock" >/dev/null 2>&1 || true
  sudo rm -f /tmp/planamo-docker.sock

  sudo dockerd \
    --data-root="$DATA" \
    --storage-driver=vfs \
    -H "$SOCK" \
    >"$LOG" 2>&1 &

  # wait ready
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
  # tar standard
  local tar1="$LIVE_SRC/opensecurity_mobile-security-framework-mobsf_latest.tar"
  if [ -f "$tar1" ]; then
    echo "[+] Loading MobSF tar: $tar1"
    sudo docker -H "$SOCK" load -i "$tar1"
    return 0
  fi

  # split: ...tar.part-000 ...
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
  sudo docker -H "$SOCK" run -d -p 8000:8000 --name mobsf opensecurity/mobile-security-framework-mobsf:latest

  sleep 5

  # ouvre navigateur si dispo
  if command -v firefox >/dev/null 2>&1; then
    firefox http://127.0.0.1:8000 >/dev/null 2>&1 || true
  elif command -v tor-browser >/dev/null 2>&1; then
    tor-browser http://127.0.0.1:8000 >/dev/null 2>&1 || true
  fi

  echo "[+] MobSF running (LIVE): http://127.0.0.1:8000"
  echo "    Docker socket: $SOCK"
  echo "    Logs: $LOG"
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
