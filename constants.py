"""
Shared constants and small sanitization helpers for Offline Radio Builder.
"""

import re

MANIFEST_FILENAME = "manifest.sii"
DESCRIPTION_FILENAME = "mod_description.txt"
ICON_FILENAME = "mod_icon.jpg"
MATERIAL_DIR = "material"
RADIO_DIR = "offline_radio"

# Where station image assets (.dds/.mat/.tobj) live, added in Stage 3 but
# referenced here so Stage 2's station-rename logic knows where to look.
STATION_ASSET_SUBPATH = ("material", "ui", "radio", "offline_station")

MUSIC_SUBDIR = "music"
TRACKS_FILENAME = "tracks.sii"

# Standard ATS/ETS2 mod icon dimensions used by the in-game mod manager.
MOD_ICON_SIZE = (276, 162)

# Windows/general filesystem-illegal characters for folder names.
_ILLEGAL_FS_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_folder_name(name: str) -> str:
    """Strip characters that are illegal in Windows folder names, keep spaces/case."""
    name = name.strip()
    name = _ILLEGAL_FS_CHARS.sub("", name)
    name = name.rstrip(". ")  # Windows doesn't allow trailing dots/spaces
    return name


def sanitize_sii_token(name: str) -> str:
    """
    Build the lowercase, underscore-separated token used for filesystem
    names: offline_radio.<token>.sii, station folder/asset names, etc.
    Hyphens are allowed here since these are just file/folder names.
    """
    name = name.strip().lower()
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-z0-9_\-]", "", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def escape_sii_string(value: str) -> str:
    """
    Escape a value for use inside a quoted SII string. Without this, a
    literal " in a track title, artist name, station name, etc. (e.g.
    'Some Song (12" Mix)') breaks out of the quoted string mid-file and
    corrupts everything the game tries to parse after it -- which can
    crash the game entirely, not just fail to show that one field.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


def unescape_sii_string(value: str) -> str:
    """Inverse of escape_sii_string, for reading values back."""
    return re.sub(r"\\(.)", r"\1", value)


def sanitize_token_attr(value: str) -> str:
    """
    Build a value legal for the SiiNunit `token` attribute type, which per
    SCS's own spec allows only lowercase a-z, 0-9, and underscore (no
    hyphens) and a maximum length of 12 characters. Used specifically for
    the station `id` field -- NOT for folder/file names, which can be
    longer and may contain hyphens.
    """
    value = value.strip().lower().replace(" ", "_").replace("-", "_")
    value = re.sub(r"[^a-z0-9_]", "", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")
