"""
Reads/writes the offline_radio_track blocks inside a station's tracks.sii
(offline_radio/<station_token>/tracks.sii). Mirrors radio_sii.py's approach
but for the simpler, always-string track fields.
"""

from __future__ import annotations

import re

from constants import escape_sii_string, unescape_sii_string

FIELD_ORDER = ["artist", "name", "ufs_path"]

_TRACK_BLOCK_RE = re.compile(
    r"offline_radio_track\s*:\s*_nameless\.(\d+)\s*\{(.*?)^\}",
    re.DOTALL | re.MULTILINE,
)
# (?:[^"\\]|\\.)* -- allows escaped \" and \\ sequences inside the string
# instead of stopping at the first quote. Without this, a literal " in a
# track title (e.g. a 12" Mix) breaks the match and corrupts parsing of
# everything after it.
_KEY_VALUE_RE = re.compile(r'^\s*([a-zA-Z_]+)\s*:\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)


def parse_tracks(container_text: str) -> list[dict]:
    found = []
    for match in _TRACK_BLOCK_RE.finditer(container_text):
        index = int(match.group(1))
        body = match.group(2)
        fields = {
            key: unescape_sii_string(value) for key, value in _KEY_VALUE_RE.findall(body)
        }
        found.append((index, fields))
    found.sort(key=lambda pair: pair[0])
    return [fields for _, fields in found]


def render_track_block(fields: dict, index: int) -> str:
    lines = [f"offline_radio_track : _nameless.{index}", "{"]
    for key in FIELD_ORDER:
        value = fields.get(key, "")
        lines.append(f'\t{key}: "{escape_sii_string(value)}"')
    lines.append("}")
    return "\n".join(lines)


def render_container(tracks: list[dict]) -> str:
    if not tracks:
        return "SiiNunit\n{\n\n}\n"
    blocks = "\n\n".join(render_track_block(t, i) for i, t in enumerate(tracks))
    return f"SiiNunit\n{{\n\n{blocks}\n\n}}\n"


# ---- convenience wrappers tied to a ModProject -------------------------

import constants


def _tracks_path(project, station_token: str):
    return project.radio_dir / station_token / constants.TRACKS_FILENAME


def load_tracks(project, station_token: str) -> list[dict]:
    path = _tracks_path(project, station_token)
    if not path.exists():
        return []
    return parse_tracks(path.read_text(encoding="utf-8"))


def save_tracks(project, station_token: str, tracks: list[dict]) -> None:
    path = _tracks_path(project, station_token)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_container(tracks), encoding="utf-8")
