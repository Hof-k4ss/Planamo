#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== Installing OSINT tools ==="

apt update

apt install -y \
  firefox-esr \
  chromium-browser \
  tor \
  torsocks \
  proxychains4 \
  curl \
  wget \
  jq \
  ripgrep \
  whois \
  dnsutils \
  python3-pip \
  python3-venv \
  git

apt clean
