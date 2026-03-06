#!/bin/bash
set -e

echo "=== Installing PLANAMO installer ==="

export DEBIAN_FRONTEND=noninteractive

apt install -y \
  dialog \
  parted \
  gdisk \
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
# PLANAMO INSTALLER — pas de set -e, on gère les erreurs manuellement

SQUASHFS="/cdrom/casper/filesystem.squashfs"
TITLE="PLANAMO Installer"
LOG="/tmp/planamo-install.log"

exec > >(tee -a "$LOG") 2>&1
echo "[*] PLANAMO Install started: $(date)"

error_exit() {
  clear
  dialog --title "$TITLE" --msgbox "ERREUR : $1\n\nConsultez le log : $LOG" 10 60
  exit 1
}

# --- Vérifications ---
[ "$(id -u)" -ne 0 ] && error_exit "Lancez avec sudo : sudo planamo-install"
[ ! -f "$SQUASHFS" ] && error_exit "filesystem.squashfs introuvable sur /cdrom/casper/"

command -v sgdisk   >/dev/null 2>&1 || error_exit "sgdisk manquant (gdisk non installé)"
command -v unsquashfs >/dev/null 2>&1 || error_exit "unsquashfs manquant"

# --- Sélection du disque ---
DISK_LIST=()
while IFS= read -r line; do
  DEV=$(echo "$line" | awk '{print $1}')
  SIZE=$(echo "$line" | awk '{print $2}')
  MODEL=$(cat "/sys/block/$DEV/device/model" 2>/dev/null | xargs || echo "Unknown")
  DISK_LIST+=("/dev/$DEV" "$SIZE  $MODEL")
done < <(lsblk -dn -o NAME,SIZE -e 7,11 2>/dev/null | grep -v "^loop")

[ ${#DISK_LIST[@]} -eq 0 ] && error_exit "Aucun disque détecté."

TARGET=$(dialog --title "$TITLE" \
  --menu "Choisissez le disque cible :\n(ATTENTION : sera entièrement effacé)" \
  15 70 8 \
  "${DISK_LIST[@]}" \
  3>&1 1>&2 2>&3) || { clear; echo "Annulé."; exit 0; }

# --- Confirmation ---
dialog --title "$TITLE" \
  --yesno "ATTENTION !\n\nToutes les données sur $TARGET seront EFFACÉES définitivement.\n\nInstaller PLANAMO sur $TARGET ?" \
  10 60 || { clear; echo "Annulé."; exit 0; }

clear
echo "======================================="
echo "  PLANAMO INSTALLATION"
echo "  Disque : $TARGET"
echo "  Log    : $LOG"
echo "======================================="

# --- Mode EFI ? ---
EFI_MODE=false
[ -d /sys/firmware/efi ] && EFI_MODE=true
echo "[*] Mode EFI : $EFI_MODE"

# --- Partitionnement ---
echo ""
echo "[1/6] Partitionnement..."

wipefs -af "$TARGET" || error_exit "wipefs échoué sur $TARGET"
sgdisk --zap-all "$TARGET" || error_exit "sgdisk zap échoué"

if $EFI_MODE; then
  sgdisk -n 1:0:+512M -t 1:EF00 -c 1:"EFI"  "$TARGET" || error_exit "Création partition EFI échouée"
  sgdisk -n 2:0:0     -t 2:8300 -c 2:"ROOT" "$TARGET" || error_exit "Création partition ROOT échouée"
  EFI_PART="${TARGET}1"
  ROOT_PART="${TARGET}2"
else
  sgdisk -n 1:0:+1M   -t 1:EF02 -c 1:"BIOS" "$TARGET" || error_exit "Création partition BIOS échouée"
  sgdisk -n 2:0:0     -t 2:8300 -c 2:"ROOT" "$TARGET" || error_exit "Création partition ROOT échouée"
  ROOT_PART="${TARGET}2"
fi

sleep 2
partprobe "$TARGET" 2>/dev/null || true
sleep 1

# --- Formatage ---
echo "[2/6] Formatage..."

if $EFI_MODE; then
  mkfs.fat -F32 -n EFI "$EFI_PART" || error_exit "Formatage EFI échoué"
fi
mkfs.ext4 -F -L PLANAMO "$ROOT_PART" || error_exit "Formatage ext4 échoué"

# --- Montage ---
echo "[3/6] Montage..."

MOUNT="/mnt/planamo-install"
mkdir -p "$MOUNT"
mount "$ROOT_PART" "$MOUNT" || error_exit "Montage root échoué"

if $EFI_MODE; then
  mkdir -p "$MOUNT/boot/efi"
  mount "$EFI_PART" "$MOUNT/boot/efi" || error_exit "Montage EFI échoué"
fi

# --- Décompression ---
echo "[4/6] Décompression du système (10-20 min)..."
echo "      Ne fermez pas cette fenêtre."

unsquashfs -f -d "$MOUNT" "$SQUASHFS"
UNSQUASH_EXIT=$?
[ $UNSQUASH_EXIT -ne 0 ] && error_exit "unsquashfs échoué (code $UNSQUASH_EXIT)"

# --- Configuration ---
echo "[5/6] Configuration..."

ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PART")
[ -z "$ROOT_UUID" ] && error_exit "UUID root introuvable"

{
  echo "UUID=$ROOT_UUID  /  ext4  errors=remount-ro  0  1"
  if $EFI_MODE; then
    EFI_UUID=$(blkid -s UUID -o value "$EFI_PART")
    echo "UUID=$EFI_UUID  /boot/efi  vfat  umask=0077  0  1"
  fi
  echo "tmpfs  /tmp  tmpfs  defaults,nosuid,nodev  0  0"
} > "$MOUNT/etc/fstab"

echo "planamo" > "$MOUNT/etc/hostname"

# Supprimer les configs live
rm -f "$MOUNT/etc/casper.conf" 2>/dev/null || true
rm -rf "$MOUNT/etc/initramfs-tools/conf.d/casper" 2>/dev/null || true

# --- GRUB ---
echo "[6/6] Installation GRUB..."

mount --bind /dev     "$MOUNT/dev"     || error_exit "bind /dev échoué"
mount --bind /dev/pts "$MOUNT/dev/pts" || true
mount --bind /proc    "$MOUNT/proc"    || error_exit "bind /proc échoué"
mount --bind /sys     "$MOUNT/sys"     || error_exit "bind /sys échoué"

if $EFI_MODE; then
  chroot "$MOUNT" grub-install \
    --target=x86_64-efi \
    --efi-directory=/boot/efi \
    --bootloader-id=PLANAMO \
    --recheck || error_exit "grub-install EFI échoué"
else
  chroot "$MOUNT" grub-install \
    --target=i386-pc \
    --recheck \
    "$TARGET" || error_exit "grub-install BIOS échoué"
fi

chroot "$MOUNT" update-grub || error_exit "update-grub échoué"

# --- Nettoyage ---
echo "[*] Nettoyage des mounts..."
umount -lf "$MOUNT/dev/pts" 2>/dev/null || true
umount -lf "$MOUNT/dev"     2>/dev/null || true
umount -lf "$MOUNT/proc"    2>/dev/null || true
umount -lf "$MOUNT/sys"     2>/dev/null || true
$EFI_MODE && umount -lf "$MOUNT/boot/efi" 2>/dev/null || true
umount -lf "$MOUNT"         2>/dev/null || true

echo ""
echo "======================================="
echo "  INSTALLATION TERMINÉE AVEC SUCCÈS !"
echo "======================================="

dialog --title "$TITLE" \
  --yesno "Installation terminée !\n\nRedémarrer maintenant ?\n(Retirez l'ISO avant de redémarrer)" \
  9 55 && reboot || true
EOF

chmod +x /usr/local/bin/planamo-install

# --- Wrapper GUI ---
cat > /usr/local/bin/planamo-install-gui << 'EOF'
#!/bin/bash
exec xfce4-terminal \
  --title="PLANAMO Installer" \
  --hide-menubar \
  -e "sudo /usr/local/bin/planamo-install"
EOF
chmod +x /usr/local/bin/planamo-install-gui

# --- Binaire rtfm (documentation) ---
cat > /usr/local/bin/rtfm << 'EOF'
#!/bin/bash
exec firefox /opt/planamo/docs/site/index.html
EOF
chmod +x /usr/local/bin/rtfm

# Alias planamo-doc aussi pour compatibilité
ln -sf /usr/local/bin/rtfm /usr/local/bin/planamo-doc

# --- sudoers : planamo-install sans mot de passe ---
echo "analyste ALL=(ALL) NOPASSWD: /usr/local/bin/planamo-install" \
  > /etc/sudoers.d/planamo-install
chmod 440 /etc/sudoers.d/planamo-install

echo "=== PLANAMO installer ready ==="
apt clean
