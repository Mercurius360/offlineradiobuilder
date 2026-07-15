<div align="center">

<img src="docs/screenshots/icon_preview.png" width="96" height="96" alt="Offline Radio Builder icon" />

# Offline Radio Builder

**A desktop tool for building offline radio station mods for American Truck Simulator and Euro Truck Simulator 2.**

No manual `.sii` editing, no hand-crafted `.dds`/`.tobj` files, no guessing at SCS's undocumented formats.

*Windows and macOS builds available.*

</div>

---

## What it does

Offline Radio Builder walks you through everything needed to ship a working offline-radio mod:

- **Mod scaffolding** — generates `manifest.sii`, `mod_description.txt`, and a properly-sized `mod_icon.jpg` (auto-scaled to 276x162)
- **Station management** — create, edit, and delete as many stations as you want, each with its own genre, language, stream-safe flag, history size, and crossfade duration
- **UI images** — drop in a banner, mini player icon, and font/title image via `.jpg` or `.png`; the app converts them to the exact `.dds` format the game expects (correct pixel format, correct dimensions, correct `.mat`/`.tobj` pairing — including the SDF material format the font texture specifically needs) and lets you remove any of them later
- **Track listing** — drag and drop `.mp3`/`.ogg` files in, reads ID3/Vorbis tags automatically, falls back to the filename when tags are missing, and lets you edit any track's title/artist by hand
- **One-click build** — nothing touches disk until you hit **Build Station**; everything is staged first, then written in one pass with a progress dialog

Everything is generated to match the real, in-game-tested `.sii`/`.dds`/`.mat`/`.tobj` formats — including several undocumented details (the `token` attribute's 12-character limit, the exact binary `.tobj` header layout, and the fact that a station's on-disk folder name must exactly equal its `id`) that aren't written down anywhere official and will silently break a mod if you get them wrong.

## Screenshots & Tutorial Video

| Welcome | Mod Setup |
|---|---|
| ![Welcome](docs/screenshots/01_welcome.png) | ![Mod Setup](docs/screenshots/02_mod_setup.png) |

| Radio Stations |
|---|
| ![Radio Stations](docs/screenshots/03_station_list.png) |

| Create / Edit Station |
|---|
| ![Create/Edit Station](docs/screenshots/04_create_edit_station.png) |
| ![Track chart with the song editor panel](docs/screenshots/05_tracks_chart.png) |

| Tutorial Video|
|---|
| [![Watch the video](https://youtube.com)](https://youtu.be/-Fn6TG2eERg) |

## Getting started

### Option 1 — Download the build

Grab the latest build for your platform from [Releases](../../releases):

- **Windows** — `OfflineRadioBuilder.exe`, no install needed
- **macOS** — `OfflineRadioBuilder.dmg`, open it and drag the app to Applications

**macOS note:** the app isn't signed with an Apple Developer certificate, so Gatekeeper will block it on first launch ("cannot be opened because the developer cannot be verified"). Either right-click the app → **Open** → confirm, or run `xattr -cr /Applications/OfflineRadioBuilder.app` in Terminal once.

### Option 2 — Run from source

```bash
git clone https://github.com/<your-username>/OfflineRadioBuilder.git
cd OfflineRadioBuilder
pip install -r requirements.txt
python main.py
```

Requires Python 3.9+. `tkinterdnd2` is optional (enables drag-and-drop); everything also works via the Browse buttons without it.

### Building your own executable

```bash
# Windows
build.bat

# macOS
./build_mac.sh
```

Both install `pyinstaller` and everything in `requirements.txt`, then build a windowed executable with the app's icon and version metadata embedded — `dist\OfflineRadioBuilder.exe` on Windows, `dist/OfflineRadioBuilder.app` on macOS. PyInstaller can't cross-compile, so each has to actually run on that OS; the same `.spec` file handles both.

## How a mod gets built

1. **New Mod** → pick a folder → fill in title, display name, author, description, and (optionally) an icon
2. **Create Station** → name, genre, language, and playback settings
3. Drop in banner/mini player/font images and your track list
4. **Build Station** — the app writes the station's `.sii` block, converts and writes every image asset, copies your tracks into place, and updates `tracks.sii`
5. Repeat for as many stations as you want, then copy the mod folder into your `mod` directory (or package it as a `.scs`) as usual

## Project structure

```
main.py                    Entry point
project.py                 Mod-level state: manifest.sii, description, icon
station_ops.py              Station create/edit/delete, folder & id management
radio_sii.py / tracks_sii.py   .sii readers/writers
dds_writer.py               DX10 DDS file writer (public Microsoft spec)
tobj_writer.py               Binary .tobj writer (reverse-engineered, see file for notes)
material_assets.py          Orchestrates image -> .dds/.mat/.tobj conversion
track_ops.py / audio_metadata.py   Track copying + ID3/Vorbis tag reading
theme.py                     Dark theme applied across the whole UI
ui/                          Tkinter screens

OfflineRadioBuilder.spec     PyInstaller build config (Windows .exe + macOS .app, same file)
build.bat / build_mac.sh     One-command local builds for Windows / macOS
icon.ico / icon.icns         App icons (Windows / macOS)
version_info.txt             Embedded Windows file version metadata
.github/workflows/build.yml  CI: builds both platforms on every version tag
```

## Requirements

- Python 3.9+
- [Pillow](https://pypi.org/project/Pillow/) — image conversion
- [mutagen](https://pypi.org/project/mutagen/) — ID3/Vorbis tag reading
- [tkinterdnd2](https://pypi.org/project/tkinterdnd2/) *(optional)* — drag-and-drop

## A note on the `.tobj` format

`.dds` follows the public Microsoft DDS specification directly, so that part is fully documented and reliable. SCS has never published the `.tobj` binary format, though — this project's writer is built against real, working reference files and cross-checked against the open-source [ConverterPIX](https://github.com/mwl4/ConverterPIX) project, but it isn't officially confirmed. If a station's banner or icon doesn't show up in-game, that's the file to suspect first.

## License

[MIT](LICENSE) — do whatever you want with it.

## Credits

Built by Mercurius for the ATS/ETS2 modding community.
