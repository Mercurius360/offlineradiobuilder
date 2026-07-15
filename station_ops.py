"""
Station-level operations that keep three things in sync:
  1. The in-memory station list
  2. offline_radio.[mod].sii on disk
  3. The station's folder/music subfolder and .dds/.mat/.tobj asset files,
     including renaming them if the station's name changes.

IMPORTANT: per SCS's own spec (modding.scssoft.com/wiki/Documentation/Engine/Game_Radio),
the station's on-disk folder name MUST be exactly equal to its `id` field --
the game derives the tracks.sii path as /offline_radio/<id>/tracks.sii
directly from `id`, with no separate lookup field. So `id` is used as the
one and only folder/asset-naming token throughout this module; there is no
separate "name-based token" anymore.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import constants
from constants import sanitize_sii_token, sanitize_token_attr
from radio_sii import save_stations

_ASSET_SUFFIXES = ("", "_font", "_small")
_ASSET_EXTS = ("dds", "mat", "tobj")

# Per SCS's own modding wiki, the SiiNunit "token" attribute type (which the
# station's `id` field uses) is capped at 12 characters, lowercase
# alphanumeric + underscore only.
_MAX_TOKEN_ATTR_LEN = 12


def build_station_id(name: str, taken_ids: set[str] | None = None) -> str:
    """
    The station's `id` -- also used as its folder name and asset base name.
    Mirrors the display name directly (lowercased, sanitized, truncated to
    the 12-char token limit). A numeric suffix is only added if that would
    collide with another station's id.
    """
    taken_ids = taken_ids or set()
    base = sanitize_token_attr(sanitize_sii_token(name))[:_MAX_TOKEN_ATTR_LEN]
    if not base:
        base = "station"

    if base not in taken_ids:
        return base

    for n in range(2, 1000):
        suffix = str(n)
        candidate = base[: _MAX_TOKEN_ATTR_LEN - len(suffix)] + suffix
        if candidate not in taken_ids:
            return candidate

    raise ValueError("Couldn't generate a unique id for this station name -- try something more distinct.")


def _asset_dir(project) -> Path:
    return project.target_mod_folder.joinpath(*constants.STATION_ASSET_SUBPATH)


def _asset_paths(asset_dir: Path, station_id: str) -> list[Path]:
    return [
        asset_dir / f"{station_id}{suffix}.{ext}"
        for suffix in _ASSET_SUFFIXES
        for ext in _ASSET_EXTS
    ]


def create_or_update_station(
    project,
    stations: list[dict],
    editing_index: int | None,
    *,
    name: str,
    genre: str,
    language: str,
    stream_safe: bool,
    history_fraction: float,
    min_tracks_between_artist: int,
) -> list[dict]:
    """Add a new station or update one in place. Returns the updated list."""
    if not sanitize_sii_token(name):
        raise ValueError("Station Name must contain at least one letter or number.")

    if editing_index is None:
        fields: dict = {}
        old_id = None
        index = len(stations)
    else:
        fields = dict(stations[editing_index])  # keep any fields this stage doesn't manage
        old_id = fields.get("id")
        index = editing_index

    taken_ids = {
        s.get("id") for i, s in enumerate(stations) if i != index and s.get("id")
    }
    new_id = build_station_id(name, taken_ids)

    fields.update(
        {
            "name": name,
            "genre": genre,
            "language": language,
            "stream_safe": stream_safe,
            "recently_played_history_size_fraction": history_fraction,
            "min_num_tracks_between_same_artist": min_tracks_between_artist,
        }
    )
    fields.setdefault("music_crossfade_duration_ms", 2000)
    fields["id"] = new_id

    _sync_station_filesystem(project, old_id, new_id)
    if old_id and old_id != new_id:
        _rewrite_asset_field_paths(fields, old_id, new_id)

    if editing_index is None:
        stations.append(fields)
    else:
        stations[editing_index] = fields

    save_stations(project, stations)
    return stations


def _rewrite_asset_field_paths(fields: dict, old_id: str, new_id: str) -> None:
    """
    cover_img / miniplayer_img / miniplayer_title_pml embed the station id
    in their filenames (e.g. ".../old_id.mat", ".../old_id_small.mat").
    After _sync_station_filesystem has renamed the actual files, update
    these stored path strings to match, using a boundary-safe replace so
    "stn1" doesn't also clobber a real id like "stn10".
    """
    pattern = re.compile(rf"/{re.escape(old_id)}(?=[._])")
    for key in ("cover_img", "miniplayer_img", "miniplayer_title_pml"):
        value = fields.get(key)
        if not value:
            continue
        fields[key] = pattern.sub(f"/{new_id}", value)


def delete_station(project, stations: list[dict], index: int) -> list[dict]:
    """Delete a station's folder/music/assets and its block, renumbering the rest."""
    fields = stations[index]
    station_id = fields.get("id") or ""

    if station_id:
        station_dir = project.radio_dir / station_id
        if station_dir.exists():
            shutil.rmtree(station_dir)

        asset_dir = _asset_dir(project)
        for path in _asset_paths(asset_dir, station_id):
            if path.exists():
                path.unlink()

    del stations[index]
    save_stations(project, stations)
    return stations


def _sync_station_filesystem(project, old_id: str | None, new_id: str) -> None:
    station_dir_new = project.radio_dir / new_id

    if old_id and old_id != new_id:
        station_dir_old = project.radio_dir / old_id
        if station_dir_old.exists():
            if station_dir_new.exists():
                raise FileExistsError(f"A station folder named '{new_id}' already exists.")
            shutil.move(str(station_dir_old), str(station_dir_new))

        asset_dir = _asset_dir(project)
        if asset_dir.exists():
            old_paths = _asset_paths(asset_dir, old_id)
            new_paths = _asset_paths(asset_dir, new_id)
            for old_path, new_path in zip(old_paths, new_paths):
                if old_path.exists() and not new_path.exists():
                    old_path.rename(new_path)

    station_dir_new.mkdir(parents=True, exist_ok=True)
    (station_dir_new / constants.MUSIC_SUBDIR).mkdir(exist_ok=True)
