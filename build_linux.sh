#!/bin/bash
# Build OfflineRadioBuilder on Linux: a onefile binary at dist/OfflineRadioBuilder,
# plus a self-contained dist/OfflineRadioBuilder-x86_64.AppImage that works
# across distros without the user needing Python installed at all.
#
# Run this ON Linux -- PyInstaller can't cross-compile (same reason
# build.bat needs Windows and build_mac.sh needs macOS).
set -e

echo "============================================"
echo " Building Offline Radio Builder (Linux)"
echo "============================================"

# tkinter itself isn't pip-installable -- it needs to come from your distro's
# package manager. Most systems already have it if you can run "python3 -m
# tkinter" successfully; if not:
#   Debian/Ubuntu:  sudo apt install python3-tk
#   Fedora:         sudo dnf install python3-tkinter
#   Arch:           sudo pacman -S tk
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "ERROR: tkinter isn't available for this Python."
    echo "Install it via your distro's package manager (see comments in this script) and try again."
    exit 1
fi

python3 -m venv --system-site-packages .build-venv
source .build-venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

python3 -m PyInstaller OfflineRadioBuilder.spec --noconfirm

echo
echo "Binary built: dist/OfflineRadioBuilder"
echo

# --- Package as an AppImage too, if appimagetool is available -------------
APPIMAGETOOL="./appimagetool.AppImage"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "Downloading appimagetool..."
    curl -L -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage" \
        || wget -O "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

rm -rf AppDir
mkdir -p AppDir/usr/bin
cp dist/OfflineRadioBuilder AppDir/usr/bin/
cp offlineradiobuilder.desktop AppDir/
cp icon.png AppDir/offlineradiobuilder.png
cat > AppDir/AppRun << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "${HERE}/usr/bin/OfflineRadioBuilder" "$@"
EOF
chmod +x AppDir/AppRun

ARCH=x86_64 "$APPIMAGETOOL" AppDir dist/OfflineRadioBuilder-x86_64.AppImage
rm -rf AppDir

echo
echo "============================================"
echo " Done."
echo "   Binary:   dist/OfflineRadioBuilder"
echo "   AppImage: dist/OfflineRadioBuilder-x86_64.AppImage"
echo "============================================"
echo
echo "The AppImage is the recommended way to share this -- it's a single"
echo "file, works across most distros, and needs nothing pre-installed."
echo "Just: chmod +x OfflineRadioBuilder-x86_64.AppImage && ./OfflineRadioBuilder-x86_64.AppImage"
