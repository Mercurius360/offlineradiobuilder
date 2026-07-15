"""
Orchestrates a station's three UI image assets: converts the source
PNG/JPG the user picked into the exact .dds spec, writes the matching
.tobj, writes the .mat, and returns the sii field values to store on the
station (cover_img, miniplayer_img, miniplayer_title_pml).

The .mat/.tobj formats below are confirmed against real, working reference
files (not just general documentation) -- see tobj_writer.py for the byte-
level details. One important, non-obvious finding from those references:
the font/title texture uses a completely different .mat effect
("ui.sdf.rfx" with SDF aux parameters) than the banner/mini player icon
("ui.rfx"), and the .tobj embeds the DDS's full absolute in-mod path,
while the .mat embeds the .tobj's bare filename -- these are genuinely
different conventions, not a typo.
"""

from __future__ import annotations

import re
from pathlib import Path

import constants
import dds_writer
import tobj_writer

# (width, height) per image 4 in the spec.
BANNER_SIZE = (608, 166)
MINIPLAYER_SIZE = (64, 64)
FONT_SIZE = (256, 32)

_ASSET_BASE_PATH = "/material/ui/radio/offline_station"

# Plain image texture (banner, mini player icon).
_MAT_TEMPLATE_IMAGE = (
    'effect : "ui.rfx" {{\n'
    '\ttexture : "texture" {{\n'
    '\t\tsource : "{tobj_name}"\n'
    "\t\tu_address : clamp\n"
    "\t\tv_address : clamp\n"
    "\t\tmip_filter : none\n"
    "\t}}\n"
    "}}\n"
)

# Font/title texture: a different effect entirely (SDF rendering), with
# aux[0] carrying the texture's (width, height, spread, bias) and no
# mip_filter line. Confirmed field-for-field against a real working file.
_MAT_TEMPLATE_FONT = (
    'effect : "ui.sdf.rfx" {{\n'
    "\taux[0] : {{ {width:.5f}, {height:.5f}, 2.00000, 0.00000 }}\n"
    "\taux[1] : {{ 1.00000, 1.00000, 1.00000, 1.00000 }}\n"
    "\taux[2] : {{ 0.00000, 0.00000, 0.00000, 0.00000 }}\n"
    "\taux[3] : {{ 0.00000, 0.00000, 0.00000, 0.00000 }}\n"
    "\taux[4] : {{ 0.00000, 0.00000, 0.00000, 0.00000 }}\n"
    '\ttexture : "texture" {{\n'
    '\t\tsource : "{tobj_name}"\n'
    "\t\tu_address : clamp\n"
    "\t\tv_address : clamp\n"
    "\t}}\n"
    "}}\n"
)


def _asset_dir(project) -> Path:
    path = project.target_mod_folder.joinpath(*constants.STATION_ASSET_SUBPATH)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_asset_trio(
    asset_dir: Path, base_name: str, source_image: Path, size: tuple[int, int], *, is_font: bool
) -> None:
    dds_name = f"{base_name}.dds"
    mat_name = f"{base_name}.mat"
    tobj_name = f"{base_name}.tobj"

    width, height = size
    if is_font:
        dds_writer.write_r8_unorm_dds(source_image, asset_dir / dds_name, width, height)
    else:
        dds_writer.write_bgrx8_srgb_dds(source_image, asset_dir / dds_name, width, height)

    # The .tobj embeds the DDS's full absolute in-mod path (confirmed from
    # the reference files) -- NOT just the bare filename.
    dds_full_path = f"{_ASSET_BASE_PATH}/{dds_name}"
    tobj_writer.write_tobj(asset_dir / tobj_name, dds_full_path, is_font=is_font)

    # The .mat, in contrast, references the .tobj by bare filename.
    if is_font:
        mat_text = _MAT_TEMPLATE_FONT.format(tobj_name=tobj_name, width=float(width), height=float(height))
    else:
        mat_text = _MAT_TEMPLATE_IMAGE.format(tobj_name=tobj_name)
    (asset_dir / mat_name).write_text(mat_text, encoding="utf-8")


# Maps an image "kind" to (filename base suffix, sii field it controls).
_IMAGE_KIND_INFO = {
    "banner": ("", "cover_img"),
    "miniplayer": ("_small", "miniplayer_img"),
    "font": ("_font", "miniplayer_title_pml"),
}


def remove_image_asset(project, station_token: str, kind: str) -> str:
    """
    Delete the .dds/.mat/.tobj trio for one image kind ("banner",
    "miniplayer", or "font") and return the sii field key that should be
    cleared on the station (the caller is responsible for popping that key
    from the station's fields dict and re-saving).
    """
    suffix, field_key = _IMAGE_KIND_INFO[kind]
    base = f"{station_token}{suffix}"
    asset_dir = _asset_dir(project)
    for ext in ("dds", "mat", "tobj"):
        path = asset_dir / f"{base}.{ext}"
        if path.exists():
            path.unlink()
    return field_key


def apply_station_images(
    project,
    station_token: str,
    *,
    banner_source: Path | None,
    miniplayer_source: Path | None,
    font_source: Path | None,
) -> dict:
    """
    Convert whichever of the three source images were provided. Returns a
    dict of the sii fields to merge into the station (only keys for images
    that were actually provided -- all three are optional).
    """
    asset_dir = _asset_dir(project)
    updates: dict = {}

    if banner_source is not None:
        _write_asset_trio(asset_dir, station_token, banner_source, BANNER_SIZE, is_font=False)
        updates["cover_img"] = f"{_ASSET_BASE_PATH}/{station_token}.mat"

    if miniplayer_source is not None:
        base = f"{station_token}_small"
        _write_asset_trio(asset_dir, base, miniplayer_source, MINIPLAYER_SIZE, is_font=False)
        updates["miniplayer_img"] = f"{_ASSET_BASE_PATH}/{base}.mat"

    if font_source is not None:
        base = f"{station_token}_font"
        _write_asset_trio(asset_dir, base, font_source, FONT_SIZE, is_font=True)
        updates["miniplayer_title_pml"] = (
            "<align vstyle=center><color value=FFFFFFFF>"
            f"<img src={_ASSET_BASE_PATH}/{base}.mat height=18 width=144>"
            "</align>"
        )

    return updates


def find_missing_assets(project, fields: dict) -> list[str]:
    """
    A station's cover_img/miniplayer_img/miniplayer_title_pml fields can
    carry forward from a previous save even if the Images step was skipped
    this time (all three are optional, so Next doesn't force re-picking
    files). That leaves the .sii referencing .mat files that were never
    actually written. Returns a list of human-readable descriptions for
    any referenced .mat file that doesn't actually exist on disk, so the
    UI can warn instead of silently shipping a broken reference.
    """
    missing = []
    checks = [
        ("cover_img", "Banner"),
        ("miniplayer_img", "Mini Player Icon"),
        ("miniplayer_title_pml", "Font / Title Text"),
    ]
    for field_key, label in checks:
        value = fields.get(field_key)
        if not value:
            continue
        # miniplayer_title_pml embeds the .mat path inside an <img src=...> tag
        # rather than being the path itself.
        match = re.search(r"(/material/ui/radio/offline_station/[^\s\"<>]+\.mat)", value)
        mat_path_str = match.group(1) if match else value
        mat_path = project.target_mod_folder / mat_path_str.lstrip("/")
        if not mat_path.exists():
            missing.append(label)
    return missing
