# Changelog

## Unreleased

- macOS build support: `.icns` icon, PyInstaller now produces a proper `OfflineRadioBuilder.app` bundle on macOS (same `.spec` file handles both platforms), `build_mac.sh` for local builds, and CI now builds a distributable `.dmg` alongside the Windows `.exe`
- Window icon (titlebar/taskbar) is now Windows-only, since macOS gets its icon from the `.app` bundle instead

## 1.0.0

Initial release.

- Mod scaffolding: `manifest.sii`, `mod_description.txt`, auto-scaled `mod_icon.jpg` (276x162), with drag-and-drop or Browse
- Radio Stations list: multi-select, double-click to edit, batch delete (removes each station's folder, music, and image assets)
- Combined **Create/Edit Station** screen: station info, banner/mini player/font images (with per-image removal), and track listing all in one place, staged in memory until **Build Station** commits everything in a single pass
- Track chart with a side-panel editor for adjusting title/artist per song, backed by ID3/Vorbis tag reading with filename fallback
- Correct `.dds` output (DX10 header, exact pixel formats per asset) and `.mat`/`.tobj` generation, including the SDF material format required specifically for the font/title texture
- Enforces the SCS `token` attribute's 12-character/lowercase/underscore limit on station `id` values, and keeps a station's on-disk folder name in sync with its `id` (both undocumented requirements that silently break a mod if violated)
- Proper `"` escaping in all generated `.sii` text (an unescaped quote in a track title or station name can corrupt the rest of the file and crash the game on load)
- Dark theme throughout, custom app icon, embedded Windows version metadata
- PyInstaller build (`build.bat` / `OfflineRadioBuilder.spec`) producing a single-file, windowed `.exe`
