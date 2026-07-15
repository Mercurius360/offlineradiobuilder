from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import audio_metadata
import radio_sii
import theme
import track_ops
import tracks_sii

_AUDIO_EXTENSIONS = (".mp3", ".ogg")


class TrackListingFrame(tk.Frame):
    """
    Drag/drop (if tkinterdnd2 is installed) or Browse to add mp3/ogg files
    to the station being created/edited. Each imported track is copied into
    the station's music folder, tagged via ID3/Vorbis metadata where
    available, and shown as an editable Name/Artist row. Finish writes
    tracks.sii and returns to the station list.
    """

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._tracks: list[dict] = []
        self._row_vars: list[tuple[tk.StringVar, tk.StringVar]] = []

        outer = tk.Frame(self, padx=24, pady=20)
        outer.pack(fill="both", expand=True)

        self.heading_label = tk.Label(outer, text="Track Listing", font=("Segoe UI", 18, "bold"))
        self.heading_label.pack(anchor="w")
        theme.style_heading(self.heading_label)

        crossfade_row = tk.Frame(outer)
        crossfade_row.pack(anchor="w", pady=(10, 0))
        tk.Label(crossfade_row, text="Crossfade Duration (ms)", font=("Segoe UI", 10, "bold")).pack(
            side="left", padx=(0, 8)
        )
        self.crossfade_var = tk.StringVar(value="2000")
        tk.Entry(crossfade_row, textvariable=self.crossfade_var, width=8).pack(side="left")
        tk.Label(
            crossfade_row, text="(0 disables crossfade)", font=("Segoe UI", 9), fg=theme.FG_MUTED
        ).pack(side="left", padx=(8, 0))

        if not audio_metadata.MUTAGEN_AVAILABLE:
            tk.Label(
                outer,
                text=(
                    "Note: the 'mutagen' package isn't installed, so artist/title can't be "
                    "read from file tags -- names will default to the filename. "
                    "Run: pip install mutagen"
                ),
                font=("Segoe UI", 9),
                fg=theme.WARNING,
                wraplength=680,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))

        drop_text = "Drag mp3/ogg files here, or click Add Tracks"
        if not getattr(controller, "drag_drop_available", False):
            drop_text = "Click Add Tracks to import mp3/ogg files"

        self.drop_zone = tk.Label(
            outer,
            text=drop_text,
            font=("Segoe UI", 10),
            height=3,
        )
        theme.style_panel_box(self.drop_zone)
        self.drop_zone.pack(fill="x", pady=(12, 8))

        tk.Button(outer, text="Add Tracks...", command=self._browse_add).pack(anchor="w")

        list_container = tk.Frame(outer)
        list_container.pack(fill="both", expand=True, pady=(16, 0))

        header_row = tk.Frame(list_container)
        header_row.pack(fill="x", padx=(0, 18))  # 18px accounts for the scrollbar width, keeps columns aligned
        header_row.columnconfigure(0, weight=3)
        header_row.columnconfigure(1, weight=2)
        header_row.columnconfigure(2, minsize=76)
        tk.Label(header_row, text="Song Title", font=("Segoe UI", 9, "bold"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        tk.Label(header_row, text="Artist", font=("Segoe UI", 9, "bold"), anchor="w").grid(
            row=0, column=1, sticky="ew", padx=(0, 8)
        )

        canvas_container = tk.Frame(list_container)
        canvas_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(canvas_container, bg=theme.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
        self.rows_frame = tk.Frame(canvas)
        self.rows_frame.columnconfigure(0, weight=1)
        self.rows_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self._canvas_window = canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        # Keep rows_frame exactly as wide as the visible canvas, so the row
        # grid's column weights (below) actually have room to stretch into
        # instead of collapsing to their minimum content width.
        canvas.bind(
            "<Configure>", lambda e: canvas.itemconfig(self._canvas_window, width=e.width)
        )

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        nav_row = tk.Frame(outer)
        nav_row.pack(fill="x", pady=(16, 0))
        tk.Button(nav_row, text="Back", width=12, command=self._back).pack(side="left")
        finish_btn = tk.Button(
            nav_row, text="Finish", width=14, font=("Segoe UI", 10, "bold"), command=self._finish
        )
        finish_btn.pack(side="right")
        theme.style_primary_button(finish_btn)

        self._register_drop_target()

    def _register_drop_target(self) -> None:
        if not getattr(self.controller, "drag_drop_available", False):
            return
        try:
            from tkinterdnd2 import DND_FILES
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass  # drag-and-drop is a bonus; Add Tracks always works

    # ---- lifecycle -----------------------------------------------------

    def on_show(self) -> None:
        index = self.controller.editing_station_index
        fields = self.controller.stations[index]
        self._token = fields.get("id", "")
        self.heading_label.configure(text=f"Track Listing - {fields.get('name', '')}")
        self.crossfade_var.set(str(fields.get("music_crossfade_duration_ms", 2000)))

        self._tracks = tracks_sii.load_tracks(self.controller.project, self._token)
        self._render_rows()

    def _render_rows(self) -> None:
        for child in self.rows_frame.winfo_children():
            child.destroy()
        self._row_vars = []

        if not self._tracks:
            tk.Label(
                self.rows_frame, text="No tracks yet.", font=("Segoe UI", 10), fg=theme.FG_MUTED
            ).grid(row=0, column=0, sticky="w", pady=8)
            return

        for i, track in enumerate(self._tracks):
            row = tk.Frame(self.rows_frame)
            row.grid(row=i, column=0, sticky="ew", pady=3)
            row.columnconfigure(0, weight=3)
            row.columnconfigure(1, weight=2)
            row.columnconfigure(2, minsize=76)

            name_var = tk.StringVar(value=track.get("name", ""))
            artist_var = tk.StringVar(value=track.get("artist", ""))
            self._row_vars.append((name_var, artist_var))

            tk.Entry(row, textvariable=name_var).grid(row=0, column=0, sticky="ew", padx=(0, 8))
            tk.Entry(row, textvariable=artist_var).grid(row=0, column=1, sticky="ew", padx=(0, 8))
            tk.Button(row, text="Remove", command=lambda idx=i: self._remove(idx)).grid(
                row=0, column=2, sticky="e"
            )

    def _sync_edits_to_tracks(self) -> None:
        """
        Pull whatever's currently typed in the Name/Artist entries back into
        self._tracks. Must run before anything that calls _render_rows()
        (adding or removing a track) -- _render_rows() rebuilds every row's
        StringVar from self._tracks, so without this sync, any edit typed
        but not yet saved gets silently thrown away and reverts to
        whatever self._tracks still held (e.g. the original ID3 metadata
        value from when the track was first added).
        """
        for track, (name_var, artist_var) in zip(self._tracks, self._row_vars):
            track["name"] = name_var.get().strip() or track["name"]
            track["artist"] = artist_var.get().strip()

    # ---- actions ---------------------------------------------------------

    def _browse_add(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Choose audio files", filetypes=[("Audio", "*.mp3 *.ogg")]
        )
        if not paths:
            return
        self._import_files([Path(p) for p in paths])

    def _on_drop(self, event) -> None:
        raw_paths = self.tk.splitlist(event.data)
        paths = [Path(p) for p in raw_paths if p.lower().endswith(_AUDIO_EXTENSIONS)]
        if paths:
            self._import_files(paths)

    def _import_files(self, paths: list[Path]) -> None:
        self._sync_edits_to_tracks()  # preserve any unsaved edits before rebuilding rows
        errors = []
        for path in paths:
            try:
                track = track_ops.add_track(self.controller.project, self._token, path)
                self._tracks.append(track)
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        self._render_rows()
        if errors:
            messagebox.showerror("Some files couldn't be added", "\n".join(errors))

    def _remove(self, index: int) -> None:
        track = self._tracks[index]
        confirmed = messagebox.askyesno(
            "Remove track",
            f"Remove '{track.get('name', '(unnamed)')}'? This also deletes the copied audio file.",
        )
        if not confirmed:
            return
        self._sync_edits_to_tracks()  # preserve any unsaved edits on the remaining rows
        track_ops.remove_track_file(self.controller.project, track)
        del self._tracks[index]
        self._render_rows()

    def _back(self) -> None:
        from ui.station_images_frame import StationImagesFrame
        self.controller.show_frame(StationImagesFrame)

    def _finish(self) -> None:
        try:
            crossfade_ms = int(self.crossfade_var.get())
            if crossfade_ms < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Invalid value", "Crossfade Duration must be a non-negative whole number (in milliseconds)."
            )
            return

        self._sync_edits_to_tracks()

        tracks_sii.save_tracks(self.controller.project, self._token, self._tracks)

        index = self.controller.editing_station_index
        self.controller.stations[index]["music_crossfade_duration_ms"] = crossfade_ms
        radio_sii.save_stations(self.controller.project, self.controller.stations)

        from ui.station_list_frame import StationListFrame
        self.controller.show_frame(StationListFrame)
