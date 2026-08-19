#!/bin/bash
set -e

echo "=== Installing Mobile Forensics Tools ==="

apt install -y \
    adb \
    fastboot \
    android-sdk-platform-tools \
    androguard \
    apktool \
    radare2 \
    binwalk \
    sleuthkit \
    libimage-exiftool-perl \
    sqlitebrowser \
    python3-pip \
    git \
    curl \
    wget \
    libimobiledevice-utils \
    usbmuxd \
    libimobiledevice6 \
    libplist-utils \
    autopsy \
    hexedit \
    foremost  

apt clean
