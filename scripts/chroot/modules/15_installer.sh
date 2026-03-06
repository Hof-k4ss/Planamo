#!/bin/bash
set -e

echo "=== Installing PLANAMO installer ==="

export DEBIAN_FRONTEND=noninteractive

# Dépendances de l'installeur
apt install -y \
  dialog \
  parted \
  dosfstools \
  e2fsprogs \
  squashfs-tools \
  grub-pc-bin \
  grub-efi-amd64-bin \
  efibootmgr \
  rsync \
  os-prober

echo "=== Writing planamo-install script ==="

cat > /usr/local/bin/planamo-install << 'EOF'
#!/bin/bash
# ============================================================
#  PLANAMO INSTALLER
#  Usage : sudo planamo-install
# ============================================================
set -e

SQUASHFS="/cdrom/casper/filesystem.squashfs"
TITLE="PLANAMO Installer"

# --- Vérifications préliminaires ---
if [ "$(id -u)" -ne 0 ]; then
  echo "Ce script doit être lancé en root : sudo planamo-install"
  exit 1
fi

if ! mount | grep -q " on / type overlay"; then
  dialog --title "$TITLE" --msgbox \
    "ATTENTION : vous ne semblez pas être en mode Live.\nCe script est prévu pour une installation depuis le live." \
    8 60
fi

if [ ! -f "$SQUASHFS" ]; then
  dialog --title "$TITLE" --msgbox \
    "Erreur : filesystem.squashfs introuvable.\nVérifiez que l'ISO est bien montée sur /cdrom." \
    8 60
  exit 1
fi

# --- Sélection du disque ---
DISKS=()
while IFS= read -r line; do
  DEV=$(echo "$line" | awk '{print $1}')
  SIZE=$(echo "$line" | awk '{print $2}')
  MODEL=$(cat "/sys/block/$DEV/device/model" 2>/dev/null | xargs || echo "Unknown")
  DISKS+=("/dev/$DEV" "$SIZE - $MODEL")
done < <(lsblk -dn -o NAME,SIZE -e 7,11 | grep -v loop)

if [ ${#DISKS[@]} -eq 0 ]; then
  dialog --title "$TITLE" --msgbox "Aucun disque détecté." 6 40
  exit 1
fi

TARGET=$(dialog --title "$TITLE" \
  --menu "Sélectionnez le disque d'installation :\n(ATTENTION : le disque sera entièrement effacé)" \
  15 70 6 \
  "${DISKS[@]}" \
  3>&1 1>&2 2>&3) || { clear; echo "Installation annulée."; exit 0; }

# --- Confirmation ---
dialog --title "$TITLE" \
  --yesno "ATTENTION !\n\nTous les données sur $TARGET seront EFFACÉES.\n\nConfirmer l'installation sur $TARGET ?" \
  10 60 || { clear; echo "Installation annulée."; exit 0; }

clear
echo "======================================="
echo "  PLANAMO INSTALLATION EN COURS"
echo "  Disque cible : $TARGET"
echo "======================================="

# --- Détection mode EFI ---
EFI_MODE=false
[ -d /sys/firmware/efi ] && EFI_MODE=true
echo "[*] Mode EFI : $EFI_MODE"

# --- Partitionnement ---
echo "[1/6] Partitionnement de $TARGET..."

wipefs -af "$TARGET"
sgdisk --zap-all "$TARGET"

if $EFI_MODE; then
  sgdisk -n 1:0:+512M -t 1:EF00 -c 1:"EFI"  "$TARGET"
  sgdisk -n 2:0:0     -t 2:8300 -c 2:"ROOT" "$TARGET"
  EFI_PART="${TARGET}1"
  ROOT_PART="${TARGET}2"
else
  sgdisk -n 1:0:+1M   -t 1:EF02 -c 1:"BIOS" "$TARGET"
  sgdisk -n 2:0:0     -t 2:8300 -c 2:"ROOT" "$TARGET"
  ROOT_PART="${TARGET}2"
fi

# Attendre que les partitions soient reconnues
sleep 1
partprobe "$TARGET" 2>/dev/null || true
sleep 1

# --- Formatage ---
echo "[2/6] Formatage..."

if $EFI_MODE; then
  mkfs.fat -F32 -n EFI "$EFI_PART"
fi
mkfs.ext4 -F -L PLANAMO "$ROOT_PART"

# --- Montage ---
echo "[3/6] Montage..."

MOUNT="/mnt/planamo-install"
mkdir -p "$MOUNT"
mount "$ROOT_PART" "$MOUNT"

if $EFI_MODE; then
  mkdir -p "$MOUNT/boot/efi"
  mount "$EFI_PART" "$MOUNT/boot/efi"
fi

# --- Décompression squashfs ---
echo "[4/6] Décompression du système (peut prendre 10-20 minutes)..."
unsquashfs -f -d "$MOUNT" "$SQUASHFS"

# --- Configuration de base ---
echo "[5/6] Configuration du système installé..."

# fstab
ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PART")
{
  echo "UUID=$ROOT_UUID  /  ext4  errors=remount-ro  0  1"
  if $EFI_MODE; then
    EFI_UUID=$(blkid -s UUID -o value "$EFI_PART")
    echo "UUID=$EFI_UUID  /boot/efi  vfat  umask=0077  0  1"
  fi
  echo "tmpfs  /tmp  tmpfs  defaults,nosuid,nodev  0  0"
} > "$MOUNT/etc/fstab"

# Hostname
echo "planamo" > "$MOUNT/etc/hostname"

# Supprimer les configs live (casper)
rm -f "$MOUNT/etc/casper.conf" 2>/dev/null || true
rm -f "$MOUNT/etc/initramfs-tools/conf.d/casper" 2>/dev/null || true

# --- GRUB ---
echo "[6/6] Installation de GRUB..."

mount --bind /dev     "$MOUNT/dev"
mount --bind /dev/pts "$MOUNT/dev/pts"
mount --bind /proc    "$MOUNT/proc"
mount --bind /sys     "$MOUNT/sys"

if $EFI_MODE; then
  chroot "$MOUNT" grub-install --target=x86_64-efi \
    --efi-directory=/boot/efi \
    --bootloader-id=PLANAMO \
    --recheck
else
  chroot "$MOUNT" grub-install --target=i386-pc \
    --recheck \
    "$TARGET"
fi

chroot "$MOUNT" update-grub

# --- Nettoyage ---
umount -lf "$MOUNT/dev/pts" 2>/dev/null || true
umount -lf "$MOUNT/dev"     2>/dev/null || true
umount -lf "$MOUNT/proc"    2>/dev/null || true
umount -lf "$MOUNT/sys"     2>/dev/null || true
if $EFI_MODE; then
  umount "$MOUNT/boot/efi" 2>/dev/null || true
fi
umount "$MOUNT" 2>/dev/null || true

echo ""
echo "======================================="
echo "  INSTALLATION TERMINÉE !"
echo "  Vous pouvez retirer l'ISO et redémarrer."
echo "======================================="

dialog --title "$TITLE" \
  --yesno "Installation terminée avec succès !\n\nRedémarrer maintenant ?" \
  8 50 && reboot || true

EOF

chmod +x /usr/local/bin/planamo-install

# --- Wrapper terminal pour le .desktop ---
cat > /usr/local/bin/planamo-install-gui << 'EOF'
#!/bin/bash
exec xfce4-terminal --title="PLANAMO Installer" -e "sudo planamo-install"
EOF
chmod +x /usr/local/bin/planamo-install-gui

# --- Wrapper doc ---
cat > /usr/local/bin/planamo-doc << 'EOF'
#!/bin/bash
exec firefox /opt/planamo/docs/site/index.html
EOF
chmod +x /usr/local/bin/planamo-doc

# --- sudoers : autoriser analyste à lancer l'installeur sans mot de passe ---
echo "analyste ALL=(ALL) NOPASSWD: /usr/local/bin/planamo-install" \
  > /etc/sudoers.d/planamo-install
chmod 440 /etc/sudoers.d/planamo-install

echo "=== PLANAMO installer ready ==="

apt clean
