#!/bin/bash
# =============================================================================
# 02_user.sh — Création de l'utilisateur analyste
# =============================================================================
# Crée l'utilisateur principal "analyste" avec mot de passe, groupe sudo,
# et prépare la structure de répertoires nécessaire aux modules suivants.
# Le skeleton XFCE (panel, bureau) est configuré dans 16_finalize.sh.
# =============================================================================
set -e

echo "=== Creating analyst user ==="

# Création de l'utilisateur sans mot de passe interactif
adduser --disabled-password --gecos "" analyste

# Définition du mot de passe
echo "analyste:P@ssw0rd" | chpasswd

# Ajout au groupe sudo
usermod -aG sudo analyste

# Sudo sans mot de passe pour l'utilisateur analyste (environnement forensique)
echo "analyste ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/analyste
chmod 440 /etc/sudoers.d/analyste

echo "=== User 'analyste' created ==="
