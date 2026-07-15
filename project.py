"""
ModProject: holds all state for the mod currently being built/edited and
knows how to write itself to disk (Stage 1: manifest, description, icon,
folder scaffold, empty radio container file) and how to load itself back
from an existing mod folder (Edit mode).
"""

from __future__ import annotations

import glob
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

import constants
import sii_templates
from sii_parser import parse_manifest_fields


@dataclass
class ModProject:
    build_location: Path            # parent directory the mod folder lives in
    mod_title: str                  # raw folder name as typed by the user
    name_of_mod: str = ""           # -> display_name, and the radio sii token
    author: str = ""
    description: str = ""
    icon_source_path: Path | None = None   # newly picked image, if any

    # Populated once the project exists on disk / is loaded from disk.
    mod_folder: Path | None = None
    radio_sii_filename: str | None = None  # literal filename, may predate a rename

    # ---- paths -----------------------------------------------------

    @property
    def folder_name(self) -> str:
        return constants.sanitize_folder_name(self.mod_title)

    @property
    def target_mod_folder(self) -> Path:
        return self.build_location / self.folder_name

    @property
    def radio_dir(self) -> Path:
        return self.target_mod_folder / constants.RADIO_DIR

    @property
    def expected_radio_sii_filename(self) -> str:
        token = constants.sanitize_sii_token(self.name_of_mod)
        return f"offline_radio.{token}.sii"

    # ---- create / save ----------------------------------------------

    def save(self) -> Path:
        """
        Create the folder scaffold if needed, write manifest/description/icon,
        and ensure the offline_radio container .sii exists. Returns the mod
        folder path. Safe to call again later (Edit -> Continue) to update
        an existing mod in place, including renaming the folder if the mod
        title changed.
        """
        new_folder = self.target_mod_folder

        if self.mod_folder and self.mod_folder != new_folder and self.mod_folder.exists():
            # Folder was renamed via the Mod Title field during Edit.
            new_folder.parent.mkdir(parents=True, exist_ok=True)
            if new_folder.exists():
                raise FileExistsError(f"A folder named '{new_folder.name}' already exists.")
            shutil.move(str(self.mod_folder), str(new_folder))

        new_folder.mkdir(parents=True, exist_ok=True)
        (new_folder / constants.MATERIAL_DIR).mkdir(exist_ok=True)
        (new_folder / constants.RADIO_DIR).mkdir(exist_ok=True)

        if self.icon_source_path is not None:
            self._save_icon(new_folder / constants.ICON_FILENAME)

        has_icon = (new_folder / constants.ICON_FILENAME).exists()
        manifest_text = sii_templates.build_manifest_sii(self.name_of_mod, self.author, has_icon=has_icon)
        (new_folder / constants.MANIFEST_FILENAME).write_text(manifest_text, encoding="utf-8")

        (new_folder / constants.DESCRIPTION_FILENAME).write_text(
            self.description, encoding="utf-8"
        )

        self._ensure_radio_sii(new_folder / constants.RADIO_DIR)

        self.mod_folder = new_folder
        return new_folder

    def _save_icon(self, dest: Path) -> None:
        with Image.open(self.icon_source_path) as img:
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")
            # Same approach as the station .dds exports: stretch to the
            # exact required dimensions rather than leaving the source
            # image at whatever resolution it was uploaded at.
            img = img.resize(constants.MOD_ICON_SIZE, Image.LANCZOS)
            img.save(dest, "JPEG", quality=95)

    def _ensure_radio_sii(self, radio_dir: Path) -> None:
        """
        Make sure exactly one offline_radio.*.sii file exists for this mod.
        If the mod name changed since the last save, rename the existing
        file (and everything it points to keeps working, since station
        blocks reference their own subfolders, not the container filename).
        """
        expected_name = self.expected_radio_sii_filename
        expected_path = radio_dir / expected_name

        existing = sorted(glob.glob(str(radio_dir / "offline_radio.*.sii")))
        if not existing:
            expected_path.write_text(sii_templates.build_empty_radio_sii(), encoding="utf-8")
            self.radio_sii_filename = expected_name
            return

        current_path = Path(existing[0])
        if current_path.name != expected_name and not expected_path.exists():
            current_path.rename(expected_path)
        self.radio_sii_filename = expected_name

    # ---- load existing (Edit mode) -----------------------------------

    @classmethod
    def load_from_existing(cls, mod_folder: Path) -> "ModProject":
        manifest_path = mod_folder / constants.MANIFEST_FILENAME
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"'{constants.MANIFEST_FILENAME}' not found in {mod_folder}. "
                "This doesn't look like an Offline Radio Builder mod folder."
            )

        fields = parse_manifest_fields(manifest_path.read_text(encoding="utf-8"))

        description_path = mod_folder / constants.DESCRIPTION_FILENAME
        description = description_path.read_text(encoding="utf-8") if description_path.exists() else ""

        project = cls(
            build_location=mod_folder.parent,
            mod_title=mod_folder.name,
            name_of_mod=fields.get("display_name", ""),
            author=fields.get("author", ""),
            description=description,
        )
        project.mod_folder = mod_folder

        radio_dir = mod_folder / constants.RADIO_DIR
        existing = sorted(glob.glob(str(radio_dir / "offline_radio.*.sii")))
        project.radio_sii_filename = Path(existing[0]).name if existing else None

        return project

    @property
    def icon_preview_path(self) -> Path | None:
        """Existing mod_icon.jpg on disk, for showing a preview in Edit mode."""
        if self.mod_folder:
            candidate = self.mod_folder / constants.ICON_FILENAME
            if candidate.exists():
                return candidate
        return None
