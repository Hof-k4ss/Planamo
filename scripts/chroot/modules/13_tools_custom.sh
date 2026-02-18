#!/bin/bash
set -e

echo "=== Installing Custom Tools ==="

mkdir -p /opt/planamo/tools/mobile
mkdir -p /opt/planamo/venvs
mkdir -p /opt/planamo/wrappers

# -----------------------
# ANDROIDQF
# -----------------------

mkdir -p /opt/planamo/tools/mobile/androidqf
cp -r /root/outils/androidqf/* /opt/planamo/tools/mobile/androidqf/

chmod +x /opt/planamo/tools/mobile/androidqf/androidqf_v1.7.0_linux_amd64

ln -s /opt/planamo/tools/mobile/androidqf/androidqf_v1.7.0_linux_amd64 \
      /usr/local/bin/androidqf


# -----------------------
# CALID_PCR
# -----------------------

cp -r /root/outils/calid_pcr /opt/planamo/tools/mobile/


# -----------------------
# MVT (venv)
# -----------------------

cp -r /root/outils/mvt/20250317_mvt-extended \
      /opt/planamo/tools/mobile/mvt

python3 -m venv /opt/planamo/venvs/mvt

source /opt/planamo/venvs/mvt/bin/activate

pip install --upgrade pip
pip install libusb1 sqlite-utils
pip install /opt/planamo/tools/mobile/mvt

deactivate


# Wrapper MVT Android
cat <<EOF > /opt/planamo/wrappers/mvt-android
#!/bin/bash
source /opt/planamo/venvs/mvt/bin/activate
mvt-android "\$@"
EOF

chmod +x /opt/planamo/wrappers/mvt-android
ln -s /opt/planamo/wrappers/mvt-android /usr/local/bin/mvt-android


# Wrapper MVT iOS
cat <<EOF > /opt/planamo/wrappers/mvt-ios
#!/bin/bash
source /opt/planamo/venvs/mvt/bin/activate
mvt-ios "\$@"
EOF

chmod +x /opt/planamo/wrappers/mvt-ios
ln -s /opt/planamo/wrappers/mvt-ios /usr/local/bin/mvt-ios
