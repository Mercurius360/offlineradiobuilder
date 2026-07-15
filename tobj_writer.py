"""
Writes binary .tobj files.

.tobj is an SCS-proprietary binary format that isn't officially published.
The header layout here is confirmed against two real, working reference
files provided directly (a banner-type and a font-type .tobj extracted
from an actual mod), decoded field-by-field -- not just the struct layout
from ConverterPIX (https://github.com/mwl4/ConverterPIX), but the actual
byte values a working file uses. Every field below is a literal match to
those reference files except mag_filter/min_filter, which is the one
documented difference between a plain image texture and a font/SDF
texture.
"""

import struct
from pathlib import Path

_SUPPORTED_MAGIC = 1890650625  # prism::tobj_header_t::SUPPORTED_MAGIC

_HEADER_FORMAT = "<5IH18B"


def _build_header(*, is_font: bool) -> bytes:
    # mag_filter/min_filter: 1,1 for a plain image texture (banner/miniplayer),
    # 3,3 for a font/SDF texture -- confirmed from the two reference files.
    mag_filter, min_filter = (3, 3) if is_font else (1, 1)

    return struct.pack(
        _HEADER_FORMAT,
        _SUPPORTED_MAGIC,  # m_version
        0,                 # m_unkn1
        0,                 # m_unkn0
        0,                 # m_unkn2
        0,                 # m_unkn3
        1,                 # m_unkn4 (u16) -- confirmed 1 in both reference files
        0,                 # m_bias
        0,                 # m_unkn4_0
        2,                 # m_type -- generic (2D texture)
        0,                 # m_unkn5
        mag_filter,        # m_mag_filter
        min_filter,        # m_min_filter
        2,                 # m_mip_filter -- nomips
        0,                 # m_unkn6
        2,                 # m_addr_u -- confirmed 2 (not 1) in both reference files
        2,                 # m_addr_v -- confirmed 2 (not 1) in both reference files
        0,                 # m_addr_w -- confirmed 0 in both reference files
        1,                 # m_compress -- uncompressed DXGI formats
        0,                 # m_unkn7
        0,                 # m_anisotropic -- confirmed 0 (not 1) in both reference files
        0,                 # m_unkn9
        1,                 # m_unkn10 -- confirmed 1 in both reference files
        0,                 # m_color_space -- confirmed 0 in both reference files (incl. font)
        0,                 # m_unkn11
    )


def write_tobj(dest: Path, dds_path: str, *, is_font: bool = False) -> None:
    """
    Write a .tobj that points at dds_path. Confirmed from the reference
    files that this must be the FULL absolute in-mod path (e.g.
    "/material/ui/radio/offline_station/mystation.dds"), NOT just the bare
    filename -- unlike the .mat file's texture source, which does use a
    bare filename. Set is_font=True for the font/title texture; banner and
    mini player icon both use is_font=False.
    """
    header = _build_header(is_font=is_font)

    path_bytes = dds_path.encode("ascii")
    texture_entry = struct.pack("<II", len(path_bytes), 0)

    with open(dest, "wb") as f:
        f.write(header)
        f.write(texture_entry)
        f.write(path_bytes)
