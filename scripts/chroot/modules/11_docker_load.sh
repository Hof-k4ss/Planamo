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
