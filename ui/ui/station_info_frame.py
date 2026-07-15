import tkinter as tk
from tkinter import messagebox

import station_ops
import theme


class StationInfoFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        outer = tk.Frame(self, padx=24, pady=20)
        outer.pack(fill="both", expand=True)

        self.heading_label = tk.Label(outer, text="Station Info", font=("Segoe UI", 18, "bold"))
        self.heading_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))
        theme.style_heading(self.heading_label)

        self.name_var = tk.StringVar()
        self.genre_var = tk.StringVar()
        self.language_var = tk.StringVar()
        self.stream_safe_var = tk.BooleanVar(value=False)
        self.history_var = tk.StringVar(value="0.5")
        self.min_tracks_var = tk.StringVar(value="0")

        self._labeled_entry(outer, 1, "Station Name", self.name_var)
        self._labeled_entry(outer, 2, "Genre", self.genre_var)
        self._labeled_entry(outer, 3, "Language (2-letter code)", self.language_var, width=6)

        tk.Label(outer, text="Stream Safe", font=("Segoe UI", 10, "bold")).grid(
            row=4, column=0, sticky="w", pady=6
        )
        tk.Checkbutton(outer, variable=self.stream_safe_var).grid(row=4, column=1, sticky="w", pady=6)

        self._labeled_entry(
            outer, 5, "History Size (0.0 - 1.0)", self.history_var, width=8
        )
        self._labeled_entry(
            outer, 6, "Min Tracks Between Same Artist", self.min_tracks_var, width=8
        )

        nav_row = tk.Frame(outer)
        nav_row.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(28, 0))
        tk.Button(nav_row, text="Cancel", width=12, command=self._cancel).pack(side="left")
        next_btn = tk.Button(
            nav_row, text="Next", width=14, font=("Segoe UI", 10, "bold"), command=self._next
        )
        next_btn.pack(side="right")
        theme.style_primary_button(next_btn)

    def _labeled_entry(self, parent, row, label, var, width=35):
        tk.Label(parent, text=label, font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=6
        )
        tk.Entry(parent, textvariable=var, width=width).grid(row=row, column=1, sticky="w", pady=6)

    # ---- lifecycle -----------------------------------------------------

    def on_show(self) -> None:
        index = self.controller.editing_station_index
        if index is None:
            self.heading_label.configure(text="New Station")
            self.name_var.set("")
            self.genre_var.set("")
            self.language_var.set("")
            self.stream_safe_var.set(False)
            self.history_var.set("0.5")
            self.min_tracks_var.set("0")
        else:
            self.heading_label.configure(text="Edit Station")
            fields = self.controller.stations[index]
            self.name_var.set(fields.get("name", ""))
            self.genre_var.set(fields.get("genre", ""))
            self.language_var.set(fields.get("language", ""))
            self.stream_safe_var.set(bool(fields.get("stream_safe", False)))
            self.history_var.set(str(fields.get("recently_played_history_size_fraction", 0.5)))
            self.min_tracks_var.set(str(fields.get("min_num_tracks_between_same_artist", 0)))

    # ---- actions ---------------------------------------------------------

    def _cancel(self) -> None:
        from ui.station_list_frame import StationListFrame
        self.controller.show_frame(StationListFrame)

    def _next(self) -> None:
        name = self.name_var.get().strip()
        genre = self.genre_var.get().strip()
        language = self.language_var.get().strip()

        if not name:
            messagebox.showwarning("Missing info", "Station Name is required.")
            return
        if len(language) != 2 or not language.isalpha():
            messagebox.showwarning("Invalid language", "Language must be a 2-letter code, e.g. EN.")
            return

        try:
            history_fraction = float(self.history_var.get())
            if not (0.0 <= history_fraction <= 1.0):
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid value", "History Size must be a number between 0.0 and 1.0.")
            return

        try:
            min_tracks = int(self.min_tracks_var.get())
            if min_tracks < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Invalid value", "Min Tracks Between Same Artist must be a non-negative whole number."
            )
            return

        try:
            self.controller.stations = station_ops.create_or_update_station(
                self.controller.project,
                self.controller.stations,
                self.controller.editing_station_index,
                name=name,
                genre=genre,
                language=language.upper(),
                stream_safe=self.stream_safe_var.get(),
                history_fraction=history_fraction,
                min_tracks_between_artist=min_tracks,
            )
        except (ValueError, FileExistsError, OSError) as exc:
            messagebox.showerror("Can't save station", str(exc))
            return

        # The station now exists (folder + sii block). Figure out its index
        # so the next screen knows which station to attach images to.
        if self.controller.editing_station_index is None:
            self.controller.editing_station_index = len(self.controller.stations) - 1

        # NOTE: Stage 4 (tracks) will be inserted after images, before
        # returning to the station list.
        from ui.station_images_frame import StationImagesFrame
        self.controller.show_frame(StationImagesFrame)
