"""
Create/Edit Station: combines station info, the three UI images (banner,
mini player icon, font/title), and the track listing into one screen.

Everything is staged in memory (self._image_sources / self._staged_tracks /
etc.) as you edit -- nothing touches disk until you click "Build Station",
which runs the actual station-info save, image conversion, and track
copying in one go behind a progress dialog. Cancel/Back at any point before
that discards all staged changes without touching disk.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import audio_metadata
import constants
import material_assets
import radio_sii
import station_ops
import theme
import track_ops
import tracks_sii
from constants import sanitize_sii_token
from ui.build_progress_dialog import BuildProgressDialog

PREVIEW_SIZE = (120, 60)
_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
_AUDIO_EXTENSIONS = (".mp3", ".ogg")

_IMAGE_KINDS = [
    ("banner", "Banner", "608 x 166"),
    ("miniplayer", "Mini Player Icon", "64 x 64"),
    ("font", "Font / Title Text", "256 x 32"),
]


class CreateEditStationFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self._image_photos: dict[str, ImageTk.PhotoImage] = {}
        self._image_preview_labels: dict[str, tk.Label] = {}
        self._image_remove_buttons: dict[str, tk.Button] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, minsize=260)
        self.grid_rowconfigure(1, weight=1)

        # ---- heading ----------------------------------------------------
        self.heading_label = tk.Label(self, text="Create Station", font=("Segoe UI", 18, "bold"))
        self.heading_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(18, 8))
        theme.style_heading(self.heading_label)

        # ---- left: scrollable main content -------------------------------
        main_container = tk.Frame(self)
        main_container.grid(row=1, column=0, sticky="nsew", padx=(24, 12))

        canvas = tk.Canvas(main_container, bg=theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        self._content = tk.Frame(canvas)
        self._content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._canvas_window = canvas.create_window((0, 0), window=self._content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self._canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._build_info_section(self._content)
        self._build_images_section(self._content)
        self._build_tracks_section(self._content)

        # ---- right: side panel for editing a selected track --------------
        self._build_side_panel()

        # ---- bottom: local status -----------------------------------------
        status_row = tk.Frame(self)
        status_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=24, pady=(8, 0))
        self.local_status_label = tk.Label(
            status_row, text="", font=("Segoe UI", 9), fg=theme.FG_MUTED, anchor="w"
        )
        self.local_status_label.pack(side="left", fill="x", expand=True)

        # ---- bottom nav ----------------------------------------------------
        nav_row = tk.Frame(self)
        nav_row.grid(row=3, column=0, columnspan=2, sticky="ew", padx=24, pady=(10, 16))
        tk.Button(nav_row, text="Cancel", width=12, command=self._cancel).pack(side="left")
        build_btn = tk.Button(
            nav_row, text="Build Station", width=16, font=("Segoe UI", 10, "bold"), command=self._build_station
        )
        build_btn.pack(side="right")
        theme.style_primary_button(build_btn)

    # ==================================================================
    # Section builders
    # ==================================================================

    def _build_info_section(self, parent: tk.Frame) -> None:
        section = tk.Frame(parent, pady=4)
        section.pack(fill="x")

        self.name_var = tk.StringVar()
        self.genre_var = tk.StringVar()
        self.language_var = tk.StringVar()
        self.stream_safe_var = tk.BooleanVar(value=False)
        self.history_var = tk.StringVar(value="0.5")
        self.min_tracks_var = tk.StringVar(value="0")
        self.crossfade_var = tk.StringVar(value="2000")

        self._labeled_entry(section, 0, "Station Name", self.name_var)
        self._labeled_entry(section, 1, "Genre", self.genre_var)
        self._labeled_entry(section, 2, "Language (2-letter code)", self.language_var, width=6)

        tk.Label(section, text="Stream Safe", font=("Segoe UI", 10, "bold")).grid(
            row=3, column=0, sticky="w", pady=6
        )
        tk.Checkbutton(section, variable=self.stream_safe_var).grid(row=3, column=1, sticky="w", pady=6)

        self._labeled_entry(section, 4, "History Size (0.0 - 1.0)", self.history_var, width=8)
        self.history_hint_label = tk.Label(
            section, text="", font=("Segoe UI", 9), fg=theme.FG_MUTED, wraplength=420, justify="left"
        )
        self.history_hint_label.grid(row=5, column=1, sticky="w", padx=(8, 0), pady=(0, 6))
        self.history_var.trace_add("write", lambda *a: self._update_history_hint())

        self._labeled_entry(section, 6, "Min Tracks Between Same Artist", self.min_tracks_var, width=8)
        self._labeled_entry(section, 7, "Crossfade Duration (ms)", self.crossfade_var, width=8)

    def _update_history_hint(self) -> None:
        track_count = len(getattr(self, "_staged_tracks", []))
        raw = self.history_var.get().strip()
        try:
            fraction = float(raw)
        except ValueError:
            self.history_hint_label.configure(text="")
            return

        if track_count == 0:
            self.history_hint_label.configure(
                text=f"This is the share of the playlist ({fraction:.0%}) that must play before a song repeats. "
                "Add songs to see how many that is."
            )
            return

        songs_before_repeat = round(track_count * fraction)
        self.history_hint_label.configure(
            text=f"With {track_count} song{'s' if track_count != 1 else ''} in this station, about "
            f"{songs_before_repeat} will play before any song can repeat ({fraction:.0%} of the playlist)."
        )

    def _labeled_entry(self, parent, row, label, var, width=35):
        tk.Label(parent, text=label, font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=6
        )
        tk.Entry(parent, textvariable=var, width=width).grid(row=row, column=1, sticky="w", pady=6, padx=(8, 0))

    def _build_images_section(self, parent: tk.Frame) -> None:
        section = tk.Frame(parent, pady=10)
        section.pack(fill="x")

        header = tk.Label(section, text="Images", font=("Segoe UI", 12, "bold"))
        header.pack(anchor="w", pady=(6, 2))
        theme.style_heading(header)

        hint = "All three are optional. Images are stretched to fit the required size."
        if getattr(self.controller, "drag_drop_available", False):
            hint += " Drag an image onto a box, Browse, or Remove an existing one."
        tk.Label(section, text=hint, font=("Segoe UI", 9), fg=theme.FG_MUTED, wraplength=520, justify="left").pack(
            anchor="w", pady=(0, 8)
        )

        for kind, label, dims in _IMAGE_KINDS:
            self._build_image_row(section, kind, label, dims)

    def _build_image_row(self, parent, kind: str, label: str, dims: str) -> None:
        row = tk.Frame(parent)
        row.pack(fill="x", pady=6)

        tk.Label(row, text=f"{label} ({dims})", font=("Segoe UI", 10, "bold"), width=22, anchor="w").pack(
            side="left"
        )

        preview = tk.Label(row, text="No image", width=16, height=3)
        theme.style_panel_box(preview)
        preview.pack(side="left", padx=(0, 10))
        self._image_preview_labels[kind] = preview
        self._register_image_drop_target(kind, preview)

        tk.Button(row, text="Browse...", command=lambda k=kind: self._browse_image(k)).pack(side="left", padx=(0, 6))
        remove_btn = tk.Button(row, text="Remove", command=lambda k=kind: self._remove_image(k))
        remove_btn.pack(side="left")
        self._image_remove_buttons[kind] = remove_btn

    def _build_tracks_section(self, parent: tk.Frame) -> None:
        section = tk.Frame(parent, pady=10)
        section.pack(fill="both", expand=True)

        header_row = tk.Frame(section)
        header_row.pack(fill="x", pady=(6, 2))
        header = tk.Label(header_row, text="Tracks", font=("Segoe UI", 12, "bold"))
        header.pack(side="left")
        theme.style_heading(header)
        self.track_count_label = tk.Label(
            header_row, text="0 songs", font=("Segoe UI", 10), fg=theme.FG_MUTED
        )
        self.track_count_label.pack(side="left", padx=(10, 0))

        drop_text = "Drag mp3/ogg files here, or click Add Tracks"
        if not getattr(self.controller, "drag_drop_available", False):
            drop_text = "Click Add Tracks to import mp3/ogg files"
        self.drop_zone = tk.Label(section, text=drop_text, font=("Segoe UI", 10), height=2)
        theme.style_panel_box(self.drop_zone)
        self.drop_zone.pack(fill="x", pady=(0, 6))

        toolbar = tk.Frame(section)
        toolbar.pack(fill="x", pady=(0, 6))
        tk.Button(toolbar, text="Add Tracks...", command=self._browse_add_tracks).pack(side="left")
        self.delete_tracks_btn = tk.Button(
            toolbar, text="Delete Selected", command=self._delete_selected_tracks, state="disabled"
        )
        theme.style_danger_button(self.delete_tracks_btn)
        self.delete_tracks_btn.pack(side="left", padx=(8, 0))
        tk.Label(
            toolbar, text="Double-click a song to edit it", font=("Segoe UI", 9), fg=theme.FG_MUTED
        ).pack(side="left", padx=(14, 0))

        tree_container = tk.Frame(section)
        tree_container.pack(fill="both", expand=True)

        columns = ("title", "artist", "filename")
        self.track_tree = ttk.Treeview(
            tree_container, columns=columns, show="headings", selectmode="extended", height=10
        )
        self.track_tree.heading("title", text="Song Title")
        self.track_tree.heading("artist", text="Artist")
        self.track_tree.heading("filename", text="File Name")
        self.track_tree.column("title", width=220, anchor="w")
        self.track_tree.column("artist", width=150, anchor="w")
        self.track_tree.column("filename", width=180, anchor="w")

        track_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.track_tree.yview)
        self.track_tree.configure(yscrollcommand=track_scrollbar.set)
        self.track_tree.pack(side="left", fill="both", expand=True)
        track_scrollbar.pack(side="right", fill="y")

        self._register_track_drop_target()  # both drop_zone and track_tree now exist

        self.track_tree.bind("<Double-1>", self._on_track_double_click)
        self.track_tree.bind("<<TreeviewSelect>>", self._on_track_selection_change)
        self.track_tree.bind("<Delete>", lambda e: self._delete_selected_tracks())

    def _build_side_panel(self) -> None:
        panel = tk.Frame(self, padx=16, pady=18, bg=theme.BG_PANEL, highlightthickness=1,
                          highlightbackground=theme.BORDER, highlightcolor=theme.BORDER)
        panel.grid(row=1, column=1, sticky="nsew", padx=(0, 24))
        self._side_panel = panel

        header = tk.Label(panel, text="Edit Song", font=("Segoe UI", 12, "bold"), bg=theme.BG_PANEL)
        header.pack(anchor="w")
        theme.style_heading(header)

        self._side_placeholder = tk.Label(
            panel,
            text="Double-click a song in the list to edit its title and artist.",
            font=("Segoe UI", 9),
            fg=theme.FG_MUTED,
            bg=theme.BG_PANEL,
            wraplength=220,
            justify="left",
        )
        self._side_placeholder.pack(anchor="w", pady=(10, 0))

        self._side_form = tk.Frame(panel, bg=theme.BG_PANEL)
        # not packed yet -- shown only while editing a track

        self.side_title_var = tk.StringVar()
        self.side_artist_var = tk.StringVar()

        tk.Label(self._side_form, text="Song Title", font=("Segoe UI", 9, "bold"), bg=theme.BG_PANEL).pack(
            anchor="w", pady=(4, 2)
        )
        tk.Entry(self._side_form, textvariable=self.side_title_var, width=28).pack(anchor="w")

        tk.Label(self._side_form, text="Artist", font=("Segoe UI", 9, "bold"), bg=theme.BG_PANEL).pack(
            anchor="w", pady=(10, 2)
        )
        tk.Entry(self._side_form, textvariable=self.side_artist_var, width=28).pack(anchor="w")

        tk.Label(self._side_form, text="File", font=("Segoe UI", 9, "bold"), bg=theme.BG_PANEL).pack(
            anchor="w", pady=(10, 2)
        )
        self.side_filename_label = tk.Label(
            self._side_form, text="", font=("Segoe UI", 9), fg=theme.FG_MUTED, bg=theme.BG_PANEL,
            wraplength=220, justify="left",
        )
        self.side_filename_label.pack(anchor="w")

        btn_row = tk.Frame(self._side_form, bg=theme.BG_PANEL)
        btn_row.pack(anchor="w", pady=(18, 0), fill="x")
        tk.Button(btn_row, text="Cancel", width=9, command=self._cancel_track_edit).pack(side="left")
        confirm_btn = tk.Button(btn_row, text="Confirm", width=9, command=self._confirm_track_edit)
        confirm_btn.pack(side="left", padx=(6, 0))
        theme.style_primary_button(confirm_btn)

    # ==================================================================
    # Lifecycle
    # ==================================================================

    def on_show(self) -> None:
        index = self.controller.editing_station_index
        self._editing_index = index

        self._image_sources: dict[str, Path | None] = {"banner": None, "miniplayer": None, "font": None}
        self._image_remove_flags: dict[str, bool] = {"banner": False, "miniplayer": False, "font": False}
        self._image_had_existing: dict[str, bool] = {"banner": False, "miniplayer": False, "font": False}
        self._staged_tracks: list[dict] = []
        self._removed_existing_tracks: list[dict] = []
        self._editing_track_index: int | None = None

        if index is None:
            self.heading_label.configure(text="Create Station")
            self.name_var.set("")
            self.genre_var.set("")
            self.language_var.set("")
            self.stream_safe_var.set(False)
            self.history_var.set("0.5")
            self.min_tracks_var.set("0")
            self.crossfade_var.set("2000")
        else:
            self.heading_label.configure(text="Edit Station")
            fields = self.controller.stations[index]
            self.name_var.set(fields.get("name", ""))
            self.genre_var.set(fields.get("genre", ""))
            self.language_var.set(fields.get("language", ""))
            self.stream_safe_var.set(bool(fields.get("stream_safe", False)))
            self.history_var.set(str(fields.get("recently_played_history_size_fraction", 0.5)))
            self.min_tracks_var.set(str(fields.get("min_num_tracks_between_same_artist", 0)))
            self.crossfade_var.set(str(fields.get("music_crossfade_duration_ms", 2000)))

            self._image_had_existing["banner"] = bool(fields.get("cover_img"))
            self._image_had_existing["miniplayer"] = bool(fields.get("miniplayer_img"))
            self._image_had_existing["font"] = bool(fields.get("miniplayer_title_pml"))

            station_id = fields.get("id", "")
            if station_id:
                for t in tracks_sii.load_tracks(self.controller.project, station_id):
                    self._staged_tracks.append(
                        {
                            "name": t.get("name", ""),
                            "artist": t.get("artist", ""),
                            "filename": Path(t.get("ufs_path", "")).name,
                            "source_path": None,
                            "ufs_path": t.get("ufs_path"),
                        }
                    )

        for kind, _, _ in _IMAGE_KINDS:
            self._refresh_image_preview(kind)
        self._render_track_chart()
        self._reset_side_panel()
        self._set_local_status("")

    # ==================================================================
    # Images
    # ==================================================================

    def _register_image_drop_target(self, kind: str, widget: tk.Widget) -> None:
        if not getattr(self.controller, "drag_drop_available", False):
            return
        try:
            from tkinterdnd2 import DND_FILES
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", lambda event, k=kind: self._on_image_drop(k, event))
        except Exception:
            pass

    def _browse_image(self, kind: str) -> None:
        path = filedialog.askopenfilename(title="Choose image", filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not path:
            return
        self._image_sources[kind] = Path(path)
        self._image_remove_flags[kind] = False
        self._refresh_image_preview(kind)
        self.controller.set_status(f"{kind.title()} image staged (converted when you Build Station).")

    def _on_image_drop(self, kind: str, event) -> None:
        raw_paths = self.tk.splitlist(event.data)
        image_paths = [p for p in raw_paths if p.lower().endswith(_IMAGE_EXTENSIONS)]
        if not image_paths:
            messagebox.showwarning("Not an image", "Drop a PNG or JPG file here.")
            return
        self._image_sources[kind] = Path(image_paths[0])
        self._image_remove_flags[kind] = False
        self._refresh_image_preview(kind)
        self.controller.set_status(f"{kind.title()} image staged (converted when you Build Station).")

    def _remove_image(self, kind: str) -> None:
        if self._image_sources[kind] is None and not self._image_had_existing[kind]:
            return  # nothing to remove
        self._image_sources[kind] = None
        self._image_remove_flags[kind] = True
        self._refresh_image_preview(kind)
        self.controller.set_status(f"{kind.title()} image will be removed when you Build Station.", kind="warning")

    def _refresh_image_preview(self, kind: str) -> None:
        label = self._image_preview_labels[kind]
        source = self._image_sources[kind]
        if source is not None:
            try:
                with Image.open(source) as img:
                    img = img.copy()
                    img.thumbnail(PREVIEW_SIZE)
                    photo = ImageTk.PhotoImage(img)
                self._image_photos[kind] = photo
                label.configure(image=photo, text="")
            except Exception as exc:
                messagebox.showerror("Image error", f"Couldn't load that image:\n{exc}")
            return

        label.configure(image="")
        if self._image_remove_flags[kind]:
            label.configure(text="Will be removed")
        elif self._image_had_existing[kind]:
            label.configure(text="Already set\n(pick to replace)")
        else:
            default_text = "No image"
            if getattr(self.controller, "drag_drop_available", False):
                default_text = "No image\n(drag here)"
            label.configure(text=default_text)

    # ==================================================================
    # Tracks
    # ==================================================================

    def _register_track_drop_target(self) -> None:
        if not getattr(self.controller, "drag_drop_available", False):
            return
        try:
            from tkinterdnd2 import DND_FILES
            for widget in (self.drop_zone, self.track_tree):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_track_drop)
        except Exception:
            pass

    def _browse_add_tracks(self) -> None:
        paths = filedialog.askopenfilenames(title="Choose audio files", filetypes=[("Audio", "*.mp3 *.ogg")])
        if not paths:
            return
        self._stage_tracks([Path(p) for p in paths])

    def _on_track_drop(self, event) -> None:
        raw_paths = self.tk.splitlist(event.data)
        paths = [Path(p) for p in raw_paths if p.lower().endswith(_AUDIO_EXTENSIONS)]
        if paths:
            self._stage_tracks(paths)

    def _stage_tracks(self, paths: list[Path]) -> None:
        self._sync_track_edits()  # preserve any in-progress side-panel edit state before rebuilding rows

        total = len(paths)
        errors = []
        for i, path in enumerate(paths, start=1):
            self._set_local_status(f"Reading {path.name}... ({i}/{total})")
            try:
                artist, title = audio_metadata.read_artist_title(path)
                self._staged_tracks.append(
                    {
                        "name": title or path.stem,
                        "artist": artist or "",
                        "filename": path.name,
                        "source_path": path,
                        "ufs_path": None,
                    }
                )
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
            self.update_idletasks()

        self._render_track_chart()
        if errors:
            messagebox.showerror("Some files couldn't be added", "\n".join(errors))
            self._set_local_status(f"Added {total - len(errors)} of {total} file(s).", kind="warning")
        else:
            self._set_local_status(f"Added {total} file(s).", kind="success")
        self.controller.set_status(f"{total} track(s) staged (copied when you Build Station).")

    def _render_track_chart(self) -> None:
        self.track_tree.delete(*self.track_tree.get_children())
        for i, track in enumerate(self._staged_tracks):
            self.track_tree.insert(
                "", "end", iid=str(i),
                values=(track.get("name", ""), track.get("artist", ""), track.get("filename", "")),
            )
        self._on_track_selection_change()

        count = len(self._staged_tracks)
        self.track_count_label.configure(text=f"{count} song{'s' if count != 1 else ''}")
        self._update_history_hint()

    def _on_track_selection_change(self, event=None) -> None:
        has_selection = bool(self.track_tree.selection())
        self.delete_tracks_btn.configure(state="normal" if has_selection else "disabled")

    def _delete_selected_tracks(self) -> None:
        selected = self.track_tree.selection()
        if not selected:
            return
        confirmed = messagebox.askyesno(
            "Remove track(s)", f"Remove {len(selected)} song(s) from this station?"
        )
        if not confirmed:
            return

        self._sync_track_edits()
        indices = sorted((int(iid) for iid in selected), reverse=True)
        for idx in indices:
            track = self._staged_tracks[idx]
            if track.get("ufs_path"):
                self._removed_existing_tracks.append(track)
            del self._staged_tracks[idx]

        if self._editing_track_index in indices:
            self._reset_side_panel()

        self._render_track_chart()
        self.controller.set_status(f"Removed {len(indices)} song(s) (applied when you Build Station).")

    def _on_track_double_click(self, event) -> None:
        item = self.track_tree.identify_row(event.y)
        if not item:
            return
        self._sync_track_edits()
        self._open_track_editor(int(item))

    def _open_track_editor(self, index: int) -> None:
        track = self._staged_tracks[index]
        self._editing_track_index = index
        self.side_title_var.set(track.get("name", ""))
        self.side_artist_var.set(track.get("artist", ""))
        self.side_filename_label.configure(text=track.get("filename", ""))

        self._side_placeholder.pack_forget()
        self._side_form.pack(fill="x")

    def _reset_side_panel(self) -> None:
        self._editing_track_index = None
        self.side_title_var.set("")
        self.side_artist_var.set("")
        self.side_filename_label.configure(text="")
        self._side_form.pack_forget()
        self._side_placeholder.pack(anchor="w", pady=(10, 0))

    def _confirm_track_edit(self) -> None:
        if self._editing_track_index is None:
            return
        track = self._staged_tracks[self._editing_track_index]
        track["name"] = self.side_title_var.get().strip() or track["name"]
        track["artist"] = self.side_artist_var.get().strip()
        self._render_track_chart()
        self._reset_side_panel()
        self.controller.set_status("Song info updated.", kind="success")

    def _cancel_track_edit(self) -> None:
        self._reset_side_panel()

    def _sync_track_edits(self) -> None:
        """If a song is mid-edit in the side panel, keep those changes before any rebuild."""
        if self._editing_track_index is not None:
            self._confirm_track_edit()

    # ==================================================================
    # Status/progress helpers
    # ==================================================================

    def _set_local_status(self, message: str, kind: str = "info") -> None:
        colors = {"info": theme.FG_MUTED, "success": theme.SUCCESS, "error": theme.ERROR, "warning": theme.WARNING}
        self.local_status_label.configure(text=message, fg=colors.get(kind, theme.FG_MUTED))

    # ==================================================================
    # Cancel / Build
    # ==================================================================

    def _cancel(self) -> None:
        from ui.station_list_frame import StationListFrame
        self.controller.show_frame(StationListFrame)

    def _validate_info(self):
        name = self.name_var.get().strip()
        genre = self.genre_var.get().strip()
        language = self.language_var.get().strip()

        if not name:
            messagebox.showwarning("Missing info", "Station Name is required.")
            return None
        if len(language) != 2 or not language.isalpha():
            messagebox.showwarning("Invalid language", "Language must be a 2-letter code, e.g. EN.")
            return None
        try:
            history_fraction = float(self.history_var.get())
            if not (0.0 <= history_fraction <= 1.0):
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid value", "History Size must be a number between 0.0 and 1.0.")
            return None
        try:
            min_tracks = int(self.min_tracks_var.get())
            if min_tracks < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Invalid value", "Min Tracks Between Same Artist must be a non-negative whole number."
            )
            return None
        try:
            crossfade_ms = int(self.crossfade_var.get())
            if crossfade_ms < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Invalid value", "Crossfade Duration must be a non-negative whole number (in milliseconds)."
            )
            return None

        return {
            "name": name,
            "genre": genre,
            "language": language.upper(),
            "stream_safe": self.stream_safe_var.get(),
            "history_fraction": history_fraction,
            "min_tracks_between_artist": min_tracks,
            "crossfade_ms": crossfade_ms,
        }

    def _build_station(self) -> None:
        self._sync_track_edits()
        info = self._validate_info()
        if info is None:
            return

        project = self.controller.project
        dialog = BuildProgressDialog(self)

        try:
            stations = station_ops.create_or_update_station(
                project,
                self.controller.stations,
                self._editing_index,
                name=info["name"],
                genre=info["genre"],
                language=info["language"],
                stream_safe=info["stream_safe"],
                history_fraction=info["history_fraction"],
                min_tracks_between_artist=info["min_tracks_between_artist"],
            )
            index = self._editing_index if self._editing_index is not None else len(stations) - 1
            stations[index]["music_crossfade_duration_ms"] = info["crossfade_ms"]
            self.controller.stations = stations
            self.controller.editing_station_index = index
            station_id = stations[index]["id"]

            for kind in ("banner", "miniplayer", "font"):
                if self._image_remove_flags[kind]:
                    field_key = material_assets.remove_image_asset(project, station_id, kind)
                    stations[index].pop(field_key, None)

            if any(self._image_sources.values()):
                updates = material_assets.apply_station_images(
                    project,
                    station_id,
                    banner_source=self._image_sources["banner"],
                    miniplayer_source=self._image_sources["miniplayer"],
                    font_source=self._image_sources["font"],
                )
                stations[index].update(updates)

            radio_sii.save_stations(project, stations)

            for track in self._removed_existing_tracks:
                track_ops.remove_track_file(project, track)

            final_tracks = []
            for track in self._staged_tracks:
                if track.get("source_path") is not None:
                    new_track = track_ops.add_track(project, station_id, track["source_path"])
                    new_track["name"] = track.get("name") or new_track["name"]
                    new_track["artist"] = track.get("artist", "")
                    final_tracks.append(new_track)
                else:
                    final_tracks.append(
                        {"artist": track.get("artist", ""), "name": track.get("name", ""), "ufs_path": track["ufs_path"]}
                    )

            tracks_sii.save_tracks(project, station_id, final_tracks)

        except Exception as exc:
            dialog.fail()
            messagebox.showerror("Build failed", f"Something went wrong building the station:\n{exc}")
            return

        def _finish():
            self.controller.set_status(f"'{info['name']}' is complete and ready in-game.", kind="success")
            from ui.station_list_frame import StationListFrame
            self.controller.show_frame(StationListFrame)

        dialog.complete("Offline Radio Station is complete!", _finish)
