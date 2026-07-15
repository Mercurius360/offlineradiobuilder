"""
Writes DDS files with an explicit DX10 header, matching the exact formats
required for radio station UI assets (see image 4 in the spec):

  - Banner / mini player icon: B8G8R8X8_UNORM_SRGB, no mipmaps
  - Font/title image:          R8_UNORM (single channel), no mipmaps

This follows the public Microsoft DDS file format specification directly
(magic + DDS_HEADER + DDS_HEADER_DXT10 + raw pixel data). Unlike .tobj,
this format is fully documented, so this is not guesswork.
"""

import struct
from pathlib import Path

from PIL import Image

_DDS_MAGIC = b"DDS "

_DDSD_CAPS = 0x1
_DDSD_HEIGHT = 0x2
_DDSD_WIDTH = 0x4
_DDSD_PITCH = 0x8
_DDSD_PIXELFORMAT = 0x1000
_DDSD_MIPMAPCOUNT = 0x20000

_DDPF_FOURCC = 0x4
_DDSCAPS_TEXTURE = 0x1000

_D3D10_RESOURCE_DIMENSION_TEXTURE2D = 3
_DDS_ALPHA_MODE_OPAQUE = 1

# DXGI_FORMAT values (standard Microsoft enum).
DXGI_FORMAT_R8_UNORM = 61
DXGI_FORMAT_B8G8R8X8_UNORM_SRGB = 93


def _build_dds_header(width: int, height: int, bytes_per_pixel: int) -> bytes:
    flags = _DDSD_CAPS | _DDSD_HEIGHT | _DDSD_WIDTH | _DDSD_PITCH | _DDSD_PIXELFORMAT | _DDSD_MIPMAPCOUNT
    pitch = width * bytes_per_pixel

    header = struct.pack(
        "<7I",
        124,      # dwSize
        flags,    # dwFlags
        height,   # dwHeight
        width,    # dwWidth
        pitch,    # dwPitchOrLinearSize
        0,        # dwDepth
        1,        # dwMipMapCount
    )
    header += b"\x00" * 44  # dwReserved1[11]

    pixelformat = struct.pack(
        "<II4sIIIII",
        32,             # ddspf.dwSize
        _DDPF_FOURCC,   # ddspf.dwFlags
        b"DX10",        # ddspf.dwFourCC
        0, 0, 0, 0, 0,  # dwRGBBitCount + 4 masks (unused when FOURCC is set)
    )
    header += pixelformat

    header += struct.pack(
        "<5I",
        _DDSCAPS_TEXTURE,  # dwCaps
        0, 0, 0, 0,        # dwCaps2, dwCaps3, dwCaps4, dwReserved2
    )
    return header


def _build_dx10_header(dxgi_format: int) -> bytes:
    return struct.pack(
        "<5I",
        dxgi_format,
        _D3D10_RESOURCE_DIMENSION_TEXTURE2D,
        0,                        # miscFlag
        1,                        # arraySize
        _DDS_ALPHA_MODE_OPAQUE,   # miscFlags2
    )


def _write_dds(dest: Path, width: int, height: int, dxgi_format: int, bytes_per_pixel: int, pixel_data: bytes) -> None:
    expected_len = width * height * bytes_per_pixel
    if len(pixel_data) != expected_len:
        raise ValueError(f"Pixel data size mismatch: got {len(pixel_data)}, expected {expected_len}")

    with open(dest, "wb") as f:
        f.write(_DDS_MAGIC)
        f.write(_build_dds_header(width, height, bytes_per_pixel))
        f.write(_build_dx10_header(dxgi_format))
        f.write(pixel_data)


def write_bgrx8_srgb_dds(source_image_path: Path, dest: Path, width: int, height: int) -> None:
    """Banner / mini player icon: resize to exact dims, write as B8G8R8X8_UNORM_SRGB."""
    with Image.open(source_image_path) as img:
        img = img.convert("RGBA").resize((width, height), Image.LANCZOS)
        r, g, b, _a = img.split()
        x = Image.new("L", (width, height), 255)
        bgrx = Image.merge("RGBA", (b, g, r, x))
        pixel_data = bgrx.tobytes()

    _write_dds(dest, width, height, DXGI_FORMAT_B8G8R8X8_UNORM_SRGB, 4, pixel_data)


def write_r8_unorm_dds(source_image_path: Path, dest: Path, width: int, height: int) -> None:
    """Font/title image: resize to exact dims, write as single-channel R8_UNORM."""
    with Image.open(source_image_path) as img:
        img = img.convert("L").resize((width, height), Image.LANCZOS)
        pixel_data = img.tobytes()

    _write_dds(dest, width, height, DXGI_FORMAT_R8_UNORM, 1, pixel_data)
