import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

import material_assets
from radio_sii import save_stations
import theme

PREVIEW_SIZE = (140, 60)
_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


class StationImagesFrame(tk.Frame):
    """
    Import Banner, Mini Player Icon, and Font/Title Text images for the
    station currently being created/edited (controller.editing_station_index).
    All three are optional -- Next converts whichever were picked and
    writes the .dds/.mat/.tobj trio for each, then updates the station's
    sii fields.
    """

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._photos = {}       # keep PhotoImage refs alive
        self._sources = {}      # kind -> Path of newly picked source image

        outer = tk.Frame(self, padx=24, pady=20)
        outer.pack(fill="both", expand=True)

        self.heading_label = tk.Label(outer, text="Station Images", font=("Segoe UI", 18, "bold"))
        self.heading_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        theme.style_heading(self.heading_label)

        hint = "All three are optional. Images are stretched to fit the required size."
        if getattr(controller, "drag_drop_available", False):
            hint += " Drag an image onto a box, or use Browse."
        tk.Label(outer, text=hint, font=("Segoe UI", 9), fg=theme.FG_MUTED, wraplength=680, justify="left").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 16)
        )

        self._rows = {}
        self._build_row(outer, 2, "banner", "Banner", "608 x 166")
        self._build_row(outer, 3, "miniplayer", "Mini Player Icon", "64 x 64")
        self._build_row(outer, 4, "font", "Font / Title Text", "256 x 32")

        nav_row = tk.Frame(outer)
        nav_row.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(28, 0))
        tk.Button(nav_row, text="Back", width=12, command=self._back).pack(side="left")
        next_btn = tk.Button(
            nav_row, text="Next", width=14, font=("Segoe UI", 10, "bold"), command=self._next
        )
        next_btn.pack(side="right")
        theme.style_primary_button(next_btn)

    def _build_row(self, parent, row, kind, label, dims):
        tk.Label(parent, text=f"{label} ({dims})", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=8
        )
        default_text = "No image"
        if getattr(self.controller, "drag_drop_available", False):
            default_text = "No image\n(drag JPG, JPEG, or \n PNG here)"
        preview = tk.Label(
            parent, text=default_text, width=18, height=4
        )
        theme.style_panel_box(preview)
        preview.grid(row=row, column=1, padx=(0, 12), pady=8)
        tk.Button(parent, text="Browse...", command=lambda k=kind: self._browse(k)).grid(
            row=row, column=2, pady=8
        )
        self._rows[kind] = preview
        self._register_drop_target(kind, preview)

    def _register_drop_target(self, kind: str, widget: tk.Widget) -> None:
        if not getattr(self.controller, "drag_drop_available", False):
            return
        try:
            from tkinterdnd2 import DND_FILES
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", lambda event, k=kind: self._on_drop(k, event))
        except Exception:
            pass  # drag-and-drop is a bonus; Browse always works

    # ---- lifecycle -----------------------------------------------------

    def on_show(self) -> None:
        index = self.controller.editing_station_index
        fields = self.controller.stations[index]
        self.heading_label.configure(text=f"Station Images - {fields.get('name', '')}")

        self._sources = {}
        default_text = "No image\n(drag JPG, JPEG, or \n PNG here)" if getattr(self.controller, "drag_drop_available", False) else "No image"
        for kind, preview in self._rows.items():
            preview.configure(image="", text=default_text)
        self._photos.clear()

        existing = {
            "banner": fields.get("cover_img"),
            "miniplayer": fields.get("miniplayer_img"),
            "font": fields.get("miniplayer_title_pml"),
        }
        for kind, value in existing.items():
            if value:
                self._rows[kind].configure(text="Already set\n(pick a file to replace)")

    # ---- actions ---------------------------------------------------------

    def _browse(self, kind: str) -> None:
        path = filedialog.askopenfilename(
            title="Choose image", filetypes=[("Images", "*.png *.jpg *.jpeg")]
        )
        if not path:
            return
        self._sources[kind] = Path(path)
        self._show_preview(kind, Path(path))

    def _on_drop(self, kind: str, event) -> None:
        raw_paths = self.tk.splitlist(event.data)
        image_paths = [p for p in raw_paths if p.lower().endswith(_IMAGE_EXTENSIONS)]
        if not image_paths:
            messagebox.showwarning("Not an image", "Drop a PNG or JPG file here.")
            return
        path = Path(image_paths[0])  # one image per box; use the first if several were dropped
        self._sources[kind] = path
        self._show_preview(kind, path)

    def _show_preview(self, kind: str, path: Path) -> None:
        try:
            with Image.open(path) as img:
                img = img.copy()
                img.thumbnail(PREVIEW_SIZE)
                photo = ImageTk.PhotoImage(img)
            self._photos[kind] = photo
            self._rows[kind].configure(image=photo, text="")
        except Exception as exc:
            messagebox.showerror("Image error", f"Couldn't load that image:\n{exc}")

    def _back(self) -> None:
        from ui.station_info_frame import StationInfoFrame
        self.controller.show_frame(StationInfoFrame)

    def _next(self) -> None:
        project = self.controller.project
        index = self.controller.editing_station_index
        fields = self.controller.stations[index]
        token = fields.get("id", "")

        try:
            updates = material_assets.apply_station_images(
                project,
                token,
                banner_source=self._sources.get("banner"),
                miniplayer_source=self._sources.get("miniplayer"),
                font_source=self._sources.get("font"),
            )
        except Exception as exc:
            messagebox.showerror("Can't convert images", f"Something went wrong converting an image:\n{exc}")
            return

        fields.update(updates)
        save_stations(project, self.controller.stations)

        missing = material_assets.find_missing_assets(project, fields)
        if missing:
            proceed = messagebox.askyesno(
                "Images not actually saved",
                "This station's info references image files that don't exist on disk yet: "
                + ", ".join(missing)
                + ".\n\nThis usually means those boxes were left empty this time (all three "
                "are optional, so Next doesn't require picking anything). "
                "Continue anyway, or go back and pick the file(s)?",
            )
            if not proceed:
                return

        from ui.track_listing_frame import TrackListingFrame
        self.controller.show_frame(TrackListingFrame)
