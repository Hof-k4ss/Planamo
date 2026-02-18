# macOS

```bash
brew install python3 libusb sqlite3 virtualenv
brew install --cask android-platform-tools
virtualenv -p python3 mvt-extended
source mvt-extended/bin/activate
cd mvt-extended
pip3 install .
```

# Linux

```bash
sudo apt install python3 python3-pip libusb-1.0-0 sqlite3
wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
unzip platform-tools-latest-linux.zip
virtualenv -p python3 mvt-extended
source mvt-extended/bin/activate
cd mvt-extended
pip3 install .
```

