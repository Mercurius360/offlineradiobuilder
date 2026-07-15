"""
Minimal, tolerant parsers for reading back values this app itself wrote.
Not a general SII parser -- just enough to support Edit mode.
"""

from __future__ import annotations

import re

from constants import unescape_sii_string


def parse_manifest_fields(manifest_text: str) -> dict:
    """Pull display_name / author out of a manifest.sii file's text."""
    fields = {"display_name": "", "author": ""}
    for key in fields:
        # (?:[^"\\]|\\.)* allows escaped \" sequences inside the value
        # instead of stopping at the first quote.
        match = re.search(rf'{key}\s*:\s*"((?:[^"\\]|\\.)*)"', manifest_text)
        if match:
            fields[key] = unescape_sii_string(match.group(1))
    return fields


def find_station_ids(radio_sii_text: str) -> list[str]:
    """
    Return every station id token found in an offline_radio.[mod].sii file,
    e.g. ["mystation_stn0", "mystation_stn1"].
    Used by later stages to populate the station list; included here so the
    file format stays consistent from stage 1 onward.
    """
    return re.findall(r"^\s*id:\s*(\S+)", radio_sii_text, flags=re.MULTILINE)
