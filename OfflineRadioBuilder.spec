# -*- mode: python ; coding: utf-8 -*-
#
# Build with:  pyinstaller OfflineRadioBuilder.spec --noconfirm
# (or just run build.bat on Windows / build_mac.sh on macOS)
#
# PyInstaller can't cross-compile -- this spec must be run ON the target
# OS to produce a working build for it (Windows -> .exe, macOS -> .app).
# It's written to handle both from the same file: on Windows it produces
# a single-file windowed .exe with the app icon + version info embedded;
# on macOS it additionally wraps that into a proper OfflineRadioBuilder.app
# bundle with the .icns icon.

import sys

from PyInstaller.utils.hooks import collect_data_files

datas = [("icon.ico", ".")]
hiddenimports = [
    # mutagen picks its format handler dynamically at runtime, so these
    # need to be listed explicitly or PyInstaller's static analysis won't
    # find them.
    "mutagen.mp3",
    "mutagen.id3",
    "mutagen.easyid3",
    "mutagen.oggvorbis",
    "mutagen.ogg",
    "mutagen.flac",
    "mutagen.wave",
    "mutagen.easymp4",
    "mutagen.mp4",
]

# tkinterdnd2 is optional (drag-and-drop bonus). Only bundle it if it's
# actually installed in the environment doing the build.
try:
    import tkinterdnd2  # noqa: F401
    datas += collect_data_files("tkinterdnd2")
    hiddenimports.append("tkinterdnd2")
except ImportError:
    pass

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="OfflineRadioBuilder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # windowed app, no console popup
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # .ico only means anything on Windows; on macOS the app's icon comes
    # from the BUNDLE step below instead.
    icon="icon.ico" if sys.platform == "win32" else None,
    version="version_info.txt",
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="OfflineRadioBuilder.app",
        icon="icon.icns",
        bundle_identifier="com.mercurius.offlineradiobuilder",
        info_plist={
            "NSPrincipalClass": "NSApplication",
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
        },
    )
