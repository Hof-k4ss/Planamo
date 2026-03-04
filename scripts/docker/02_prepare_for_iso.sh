echo "=== Splitting docker tar files > 4GiB for ISO9660 ==="

TARGET_DIR="$WORKDIR/iso/docker-images"

# 3.9G pour rester safe sous 4GiB
SPLIT_SIZE="3900m"

find "$TARGET_DIR" -maxdepth 1 -type f -name "*.tar" -size +4096M -print0 | while IFS= read -r -d '' tar; do
  echo "[*] Splitting: $tar"
  split -b "$SPLIT_SIZE" -d -a 3 "$tar" "${tar}.part-"
  rm -f "$tar"
done

echo "=== Split done ==="
