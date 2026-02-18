#!/bin/bash
set -e

echo "=== Creating analyst user ==="

adduser --disabled-password --gecos "" analyste
echo "analyste:P@ssw0rd" | chpasswd

usermod -aG sudo analyste

echo "analyste ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/analyste
chmod 440 /etc/sudoers.d/analyste
