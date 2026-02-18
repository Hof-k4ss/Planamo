#!/bin/bash
set -euo pipefail

echo "============================================="
echo "       PLANAMO DOCKER OFFLINE FETCH PRO      "
echo "============================================="

IMAGEDIR="$(pwd)/docker-images"
LOGDIR="$(pwd)/docker-logs"

mkdir -p "$IMAGEDIR"
mkdir -p "$LOGDIR"

IMAGES=(
  "opensecurity/mobile-security-framework-mobsf:latest"
  "remnux/remnux-distro:latest"
)

MAX_JOBS=2
CURRENT_JOBS=0

pull_and_save() {
    IMAGE="$1"
    SAFE_NAME=$(echo "$IMAGE" | tr '/:' '__')
    TARFILE="$IMAGEDIR/$SAFE_NAME.tar"
    LOGFILE="$LOGDIR/$SAFE_NAME.log"

    echo "--------------------------------------------------"
    echo "Processing: $IMAGE"

    # Pull avec timeout (évite blocage)
    if docker image inspect "$IMAGE" > /dev/null 2>&1; then
        echo "Image already present locally."
    else
        echo "Pulling image..."
        if ! timeout 600 docker pull "$IMAGE" >> "$LOGFILE" 2>&1; then
            echo "⚠️  Failed to pull $IMAGE"
            return
        fi
    fi

    if [ -f "$TARFILE" ]; then
        echo "Tar already exists → skipping save"
    else
        echo "Saving image..."
        docker save "$IMAGE" -o "$TARFILE" >> "$LOGFILE" 2>&1
        echo "Saved: $TARFILE"
    fi

    echo "Done: $IMAGE"
}

for IMAGE in "${IMAGES[@]}"; do
(
    pull_and_save "$IMAGE"
) &

    CURRENT_JOBS=$((CURRENT_JOBS+1))

    if [ "$CURRENT_JOBS" -ge "$MAX_JOBS" ]; then
        wait
        CURRENT_JOBS=0
    fi
done

wait

echo ""
echo "============================================="
echo " ALL DOCKER IMAGES READY FOR ISO INJECTION  "
echo "============================================="

du -sh "$IMAGEDIR"
