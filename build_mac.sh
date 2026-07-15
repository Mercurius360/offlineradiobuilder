#!/bin/bash
# Build OfflineRadioBuilder.app on macOS.
#
# Run this ON a Mac -- PyInstaller can't cross-compile, so a macOS build
# has to actually run on macOS (same reason build.bat has to run on Windows).
set -e

echo "============================================"
echo " Building Offline Radio Builder.app"
echo "============================================"

python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

python3 -m PyInstaller OfflineRadioBuilder.spec --noconfirm

echo
echo "============================================"
echo " Done. App is at: dist/OfflineRadioBuilder.app"
echo "============================================"
echo
echo "First launch note: since this isn't signed with an Apple Developer"
echo "certificate, macOS Gatekeeper will block it the first time you open"
echo "it. Either right-click the app -> Open (and confirm), or run:"
echo "  xattr -cr dist/OfflineRadioBuilder.app"
