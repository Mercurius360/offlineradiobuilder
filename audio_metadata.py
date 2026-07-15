"""
Reads artist/title tags from mp3 (ID3) and ogg (Vorbis comments) files via
mutagen's format-agnostic "easy" interface. If mutagen isn't installed, or
a file has no usable tags, callers fall back to the filename -- this module
never raises for a missing-tag situation, only returns (None, None).

MUTAGEN_AVAILABLE is exposed so the UI can tell the difference between
"mutagen isn't installed" and "this particular file has no tags" instead
of both silently looking like a blank artist field.
"""

from __future__ import annotations

from pathlib import Path

try:
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


def read_artist_title(path: Path) -> tuple[str | None, str | None]:
    if not MUTAGEN_AVAILABLE:
        return None, None

    artist = title = None

    try:
        audio = MutagenFile(path, easy=True)
    except Exception:
        audio = None

    if audio is not None:
        artist = audio.get("artist", [None])[0] if "artist" in audio else None
        title = audio.get("title", [None])[0] if "title" in audio else None
        if artist is None and "albumartist" in audio:
            artist = audio.get("albumartist", [None])[0]

    # Some mp3 files (particularly older/ID3v1-tagged or oddly-encoded ones)
    # don't surface cleanly through the "easy" interface. Fall back to
    # reading raw ID3 frames directly before giving up.
    if str(path).lower().endswith(".mp3") and (artist is None or title is None):
        try:
            from mutagen.id3 import ID3
            tags = ID3(path)
            if artist is None and "TPE1" in tags:
                artist = str(tags["TPE1"].text[0])
            if artist is None and "TPE2" in tags:  # album artist, common fallback
                artist = str(tags["TPE2"].text[0])
            if title is None and "TIT2" in tags:
                title = str(tags["TIT2"].text[0])
        except Exception:
            pass

    return artist, title
