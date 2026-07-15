"""
Higher-level track operations: copying a source mp3/ogg into a station's
music folder (handling filename collisions), reading its metadata, and
cleaning up the copied file when a track is removed from the list.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import audio_metadata
import constants


def music_dir(project, station_token: str) -> Path:
    path = project.radio_dir / station_token / constants.MUSIC_SUBDIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _unique_dest_path(target_dir: Path, filename: str) -> Path:
    dest = target_dir / filename
    if not dest.exists():
        return dest
    stem, suffix = Path(filename).stem, Path(filename).suffix
    n = 2
    while True:
        candidate = target_dir / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def add_track(project, station_token: str, source_path: Path) -> dict:
    """Copy source_path into the station's music folder and build its track entry."""
    dest_dir = music_dir(project, station_token)
    dest_path = _unique_dest_path(dest_dir, source_path.name)
    shutil.copy2(source_path, dest_path)

    artist, title = audio_metadata.read_artist_title(dest_path)
    name = title or dest_path.stem
    artist = artist or ""

    ufs_path = f"/{constants.RADIO_DIR}/{station_token}/{constants.MUSIC_SUBDIR}/{dest_path.name}"
    return {"artist": artist, "name": name, "ufs_path": ufs_path}


def remove_track_file(project, track: dict) -> None:
    """Delete the music file a track entry points to, if it exists."""
    ufs_path = track.get("ufs_path", "")
    parts = ufs_path.strip("/").split("/")
    if len(parts) < 4 or parts[0] != constants.RADIO_DIR:
        return
    token, filename = parts[1], parts[-1]
    file_path = project.radio_dir / token / constants.MUSIC_SUBDIR / filename
    if file_path.exists():
        file_path.unlink()
