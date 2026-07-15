"""
Reads/writes the offline_radio_station blocks inside offline_radio.[mod].sii.

Stations are represented as plain dicts (not a dataclass) so that fields
Stage 2 doesn't manage yet (cover_img, miniplayer_img, miniplayer_title_pml,
future track-related keys) round-trip untouched when this stage only edits
the basic info fields.

Every save re-renders the whole container from the in-memory station list,
so on-disk _nameless.N indices always end up contiguous (0..N-1) in list
order -- this is what gives us "delete renumbers the rest" for free.
"""

from __future__ import annotations

import re

from constants import escape_sii_string, unescape_sii_string

# Order controls how fields are written out. Keys not present on a given
# station are simply skipped -- that's how optional fields (added by later
# stages) stay optional here.
FIELD_ORDER = [
    "id",
    "name",
    "genre",
    "language",
    "stream_safe",
    "recently_played_history_size_fraction",
    "min_num_tracks_between_same_artist",
    "cover_img",
    "miniplayer_img",
    "miniplayer_title_pml",
    "music_crossfade_duration_ms",
]

# Fields that must always be quoted strings when written. `id` is
# deliberately NOT in this set: per SCS's own spec, `token`-type attributes
# (which `id` is) are written bare/unquoted, e.g. `id: mymod_stn0`.
_STRING_FIELDS = {"name", "genre", "language", "cover_img", "miniplayer_img", "miniplayer_title_pml"}
_BOOL_FIELDS = {"stream_safe"}

_STATION_BLOCK_RE = re.compile(
    r"offline_radio_station\s*:\s*_nameless\.(\d+)\s*\{(.*?)^\}",
    re.DOTALL | re.MULTILINE,
)
_KEY_VALUE_RE = re.compile(r"^\s*([a-zA-Z_]+)\s*:\s*(.+?)\s*$", re.MULTILINE)


def parse_stations(container_text: str) -> list[dict]:
    """Return every station block as a dict, ordered by their on-disk index."""
    found = []
    for match in _STATION_BLOCK_RE.finditer(container_text):
        index = int(match.group(1))
        body = match.group(2)
        fields = {}
        for kv in _KEY_VALUE_RE.finditer(body):
            key, raw_value = kv.group(1), kv.group(2)
            fields[key] = _parse_value(key, raw_value)
        found.append((index, fields))

    found.sort(key=lambda pair: pair[0])
    return [fields for _, fields in found]


def _parse_value(key: str, raw: str):
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return unescape_sii_string(raw[1:-1])
    if key in _BOOL_FIELDS:
        return raw == "true"
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def _format_value(key: str, value) -> str:
    if key in _STRING_FIELDS:
        return f'"{escape_sii_string(str(value))}"'
    if key in _BOOL_FIELDS:
        return "true" if value else "false"
    return str(value)


def render_station_block(fields: dict, index: int) -> str:
    lines = [f"offline_radio_station : _nameless.{index}", "{"]
    for key in FIELD_ORDER:
        value = fields.get(key)
        if value is None or value == "":
            continue
        lines.append(f"\t{key}: {_format_value(key, value)}")
    lines.append("}")
    return "\n".join(lines)


def render_container(stations: list[dict]) -> str:
    if not stations:
        return "SiiNunit\n{\n\n}\n"
    blocks = "\n\n".join(render_station_block(s, i) for i, s in enumerate(stations))
    return f"SiiNunit\n{{\n\n{blocks}\n\n}}\n"


# ---- convenience wrappers tied to a ModProject -------------------------


def load_stations(project) -> list[dict]:
    if not project.radio_sii_filename:
        return []
    path = project.radio_dir / project.radio_sii_filename
    if not path.exists():
        return []
    return parse_stations(path.read_text(encoding="utf-8"))


def save_stations(project, stations: list[dict]) -> None:
    path = project.radio_dir / project.radio_sii_filename
    path.write_text(render_container(stations), encoding="utf-8")
