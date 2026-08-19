#!/bin/bash
set -e

echo "=== Installing PLANAMO installer ==="

export DEBIAN_FRONTEND=noninteractive

apt install -y \
  whiptail \
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
# PLANAMO INSTALLER — whiptail, pas de set -e

SQUASHFS="/cdrom/casper/filesystem.squashfs"
TITLE="PLANAMO Installer"
LOG="/tmp/planamo-install.log"

exec > >(tee -a "$LOG") 2>&1
echo "[*] PLANAMO Install started: $(date)"

error_exit() {
  clear
  whiptail --title "$TITLE" --msgbox "ERREUR : $1\n\nConsultez le log : $LOG" 12 65
  exit 1
}

# --- Verifications ---
[ "$(id -u)" -ne 0 ] && error_exit "Lancez avec sudo : sudo planamo-install"
[ ! -f "$SQUASHFS" ] && error_exit "filesystem.squashfs introuvable sur /cdrom/casper/"
command -v sgdisk      >/dev/null 2>&1 || error_exit "sgdisk manquant"
command -v unsquashfs  >/dev/null 2>&1 || error_exit "unsquashfs manquant"

# --- Selection du disque ---
DISK_LIST=()
while IFS= read -r line; do
  DEV=$(echo "$line" | awk '{print $1}')
  SIZE=$(echo "$line" | awk '{print $2}')
  MODEL=$(cat "/sys/block/$DEV/device/model" 2>/dev/null | xargs || echo "Unknown")
  DISK_LIST+=("/dev/$DEV" "$SIZE $MODEL")
done < <(lsblk -dn -o NAME,SIZE -e 7,11 2>/dev/null | grep -v "^loop")

[ ${#DISK_LIST[@]} -eq 0 ] && error_exit "Aucun disque detecte."

TARGET=$(whiptail --title "$TITLE" \
  --menu "Choisissez le disque cible :\n(ATTENTION : sera entierement efface)" \
  18 70 8 \
  "${DISK_LIST[@]}" \
  3>&1 1>&2 2>&3) || { clear; echo "Annule."; exit 0; }

# --- Confirmation ---
whiptail --title "$TITLE" \
  --yesno "ATTENTION !\n\nToutes les donnees sur $TARGET seront EFFACEES.\n\nInstaller PLANAMO sur $TARGET ?" \
  12 65 || { clear; echo "Annule."; exit 0; }

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
wipefs -af "$TARGET"    || error_exit "wipefs echoue sur $TARGET"
sgdisk --zap-all "$TARGET" || error_exit "sgdisk zap echoue"

# Prefixe partition : nvme/mmcblk utilisent 'p' (nvme0n1p1), sata non (sda1)
if echo "$TARGET" | grep -qE '(nvme|mmcblk)'; then
  PART_PREFIX="${TARGET}p"
else
  PART_PREFIX="${TARGET}"
fi

if $EFI_MODE; then
  sgdisk -n 1:0:+512M -t 1:EF00 -c 1:"EFI"  "$TARGET" || error_exit "Partition EFI echouee"
  sgdisk -n 2:0:0     -t 2:8300 -c 2:"ROOT" "$TARGET" || error_exit "Partition ROOT echouee"
  EFI_PART="${PART_PREFIX}1"
  ROOT_PART="${PART_PREFIX}2"
else
  sgdisk -n 1:0:+1M   -t 1:EF02 -c 1:"BIOS" "$TARGET" || error_exit "Partition BIOS echouee"
  sgdisk -n 2:0:0     -t 2:8300 -c 2:"ROOT" "$TARGET" || error_exit "Partition ROOT echouee"
  ROOT_PART="${PART_PREFIX}2"
fi

sleep 2
partprobe "$TARGET" 2>/dev/null || true
sleep 1

# --- Formatage ---
echo "[2/6] Formatage..."
$EFI_MODE && { mkfs.fat -F32 -n EFI "$EFI_PART" || error_exit "Formatage EFI echoue"; }
mkfs.ext4 -F -L PLANAMO "$ROOT_PART" || error_exit "Formatage ext4 echoue"

# --- Montage ---
echo "[3/6] Montage..."
MOUNT="/mnt/planamo-install"
mkdir -p "$MOUNT"
mount "$ROOT_PART" "$MOUNT" || error_exit "Montage root echoue"
if $EFI_MODE; then
  mkdir -p "$MOUNT/boot/efi"
  mount "$EFI_PART" "$MOUNT/boot/efi" || error_exit "Montage EFI echoue"
fi

# --- Decompression ---
echo "[4/6] Decompression du systeme (10-20 min)..."
echo "      Ne fermez pas cette fenetre."
unsquashfs -f -d "$MOUNT" "$SQUASHFS"
[ $? -ne 0 ] && error_exit "unsquashfs echoue"

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
rm -f "$MOUNT/etc/casper.conf" 2>/dev/null || true
rm -rf "$MOUNT/etc/initramfs-tools/conf.d/casper" 2>/dev/null || true

# Copier kernel depuis casper/
echo "[*] Copie du kernel..."
mkdir -p "$MOUNT/boot"
VMLINUZ=$(ls /cdrom/casper/vmlinuz* 2>/dev/null | sort -V | tail -1)
INITRD=$(ls /cdrom/casper/initrd*   2>/dev/null | sort -V | tail -1)
[ -z "$VMLINUZ" ] && error_exit "vmlinuz introuvable dans /cdrom/casper/"
[ -z "$INITRD"  ] && error_exit "initrd introuvable dans /cdrom/casper/"
KVER=$(ls "$MOUNT/lib/modules/" 2>/dev/null | sort -V | tail -1)
[ -z "$KVER" ] && error_exit "Aucun module kernel trouve"
cp "$VMLINUZ" "$MOUNT/boot/vmlinuz-$KVER"
cp "$INITRD"  "$MOUNT/boot/initrd.img-$KVER"
ln -sf "vmlinuz-$KVER"    "$MOUNT/boot/vmlinuz"
ln -sf "initrd.img-$KVER" "$MOUNT/boot/initrd.img"
echo "[OK] Kernel : $KVER"

# --- GRUB ---
echo "[6/6] Installation GRUB..."
mount --bind /dev     "$MOUNT/dev"  || error_exit "bind /dev echoue"
mount --bind /dev/pts "$MOUNT/dev/pts" || true
mount --bind /proc    "$MOUNT/proc" || error_exit "bind /proc echoue"
mount -t sysfs sysfs  "$MOUNT/sys"  || error_exit "mount /sys echoue"
$EFI_MODE && mount -t efivarfs efivarfs "$MOUNT/sys/firmware/efi/efivars" 2>/dev/null || true

echo "[*] Regeneration initramfs..."
chroot "$MOUNT" update-initramfs -u -k all || echo "[!] update-initramfs warning"

if $EFI_MODE; then
  chroot "$MOUNT" grub-install \
    --target=x86_64-efi --efi-directory=/boot/efi \
    --bootloader-id=PLANAMO --recheck || error_exit "grub-install EFI echoue"
else
  chroot "$MOUNT" grub-install \
    --target=i386-pc --recheck \
    "$TARGET" || error_exit "grub-install BIOS echoue"
fi

chroot "$MOUNT" update-grub || error_exit "update-grub echoue"
[ -f "$MOUNT/boot/grub/grub.cfg" ] || error_exit "grub.cfg absent"
echo "[OK] grub.cfg genere : $(wc -l < "$MOUNT/boot/grub/grub.cfg") lignes"

# --- Copie images Docker ---
echo "[*] Copie des images Docker depuis l'ISO..."
DOCKER_SRC="/cdrom/docker-images"
DOCKER_DST="$MOUNT/opt/planamo/docker"

if [ -d "$DOCKER_SRC" ] && ls "$DOCKER_SRC"/*.tar "$DOCKER_SRC"/*.tar.part-* 2>/dev/null | head -1 | grep -q .; then
  mkdir -p "$DOCKER_DST"
  cp -rf "$DOCKER_SRC"/. "$DOCKER_DST/"
  echo "[OK] Images Docker copiées"

  # Service systemd pour charger les images Docker au premier boot
  cat > "$MOUNT/etc/systemd/system/planamo-docker-load.service" << 'SVCEOF'
[Unit]
Description=PLANAMO Load Docker Images
After=docker.service
Requires=docker.service
ConditionPathExists=/opt/planamo/docker

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/planamo-docker-load
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

  # Script de chargement avec reassemblage des fichiers splittés
  cat > "$MOUNT/usr/local/bin/planamo-docker-load" << 'LDEOF'
#!/bin/bash
DOCKER_DIR="/opt/planamo/docker"
FLAG="/opt/planamo/.docker-loaded"

[ -f "$FLAG" ] && { echo "[*] Images already loaded"; exit 0; }

echo "[*] Loading Docker images from $DOCKER_DIR..."

# Reassembler les fichiers splittés
for base in "$DOCKER_DIR"/*.tar.part-000; do
  [ -f "$base" ] || continue
  name="${base%.tar.part-000}"
  tarfile="${name}.tar"
  if [ ! -f "$tarfile" ]; then
    echo "[*] Reassembling $(basename "$name")..."
    cat "${name}".tar.part-* > "$tarfile"
    echo "[OK] Reassembled: $(basename "$tarfile")"
  fi
done

# Charger tous les .tar
for tar in "$DOCKER_DIR"/*.tar; do
  [ -f "$tar" ] || continue
  echo "[*] Loading: $(basename "$tar")..."
  docker load -i "$tar" && echo "[OK] Loaded: $(basename "$tar")"
done

touch "$FLAG"
echo "[*] All Docker images loaded."
LDEOF
  chmod +x "$MOUNT/usr/local/bin/planamo-docker-load"

  # Activer le service
  chroot "$MOUNT" systemctl enable planamo-docker-load.service 2>/dev/null || true
  echo "[OK] Service planamo-docker-load activé"
else
  echo "[!] Aucune image Docker trouvée dans $DOCKER_SRC — skip"
fi

# --- Nettoyage ---
echo "[*] Nettoyage..."
umount -lf "$MOUNT/dev/pts"  2>/dev/null || true
umount -lf "$MOUNT/dev"      2>/dev/null || true
umount -lf "$MOUNT/proc"     2>/dev/null || true
umount -lf "$MOUNT/sys"      2>/dev/null || true
$EFI_MODE && umount -lf "$MOUNT/boot/efi" 2>/dev/null || true
umount -lf "$MOUNT"          2>/dev/null || true

echo ""
echo "======================================="
echo "  INSTALLATION TERMINEE AVEC SUCCES !"
echo "======================================="

# Supprimer icone install du bureau live
rm -f /home/analyste/Desktop/Install-PLANAMO.desktop 2>/dev/null || true
# Recharger le bureau en tant qu'analyste
ANALYSTE_UID=$(id -u analyste 2>/dev/null || echo 1000)
sudo -u analyste DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${ANALYSTE_UID}/bus" \
  xfdesktop --reload 2>/dev/null || true

whiptail --title "$TITLE" \
  --yesno "Installation terminee !\n\nRedemarrer maintenant ?\n(Retirez l'ISO avant de redemarrer)" \
  10 60 && reboot || true
EOF

chmod +x /usr/local/bin/planamo-install

# --- Wrapper GUI ---
cat > /usr/local/bin/planamo-install-gui << 'EOF'
#!/bin/bash
exec xterm \
  -title "PLANAMO Installer" \
  -fa "Monospace" -fs 11 \
  -geometry 100x35 \
  -e "sudo TERM=linux /usr/local/bin/planamo-install"
EOF
chmod +x /usr/local/bin/planamo-install-gui

# S'assurer que xterm est installe
apt-get install -y xterm 2>/dev/null || true

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
