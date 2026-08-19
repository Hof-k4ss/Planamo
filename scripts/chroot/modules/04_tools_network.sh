#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== Installing Network / Transfer Tools ==="

apt install -y \
  openssh-client \
  openssh-server \
  rsync \
  netcat-openbsd \
  tcpdump \
  nmap \
  iputils-ping \
  dnsutils \
  whois \
  socat \
  usbutils \
  pciutils

systemctl enable ssh || true

apt clean
