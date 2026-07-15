import tkinter as tk
from tkinter import messagebox, ttk

import station_ops
import theme
from radio_sii import load_stations
from tracks_sii import load_tracks


class StationListFrame(tk.Frame):
    """
    Radio Stations screen. Stations are shown as a selectable list
    (ttk.Treeview, multi-select): double-click a row to edit it, select one
    or more rows and click Delete (or press the Delete key) to remove them
    -- each removal deletes that station's folder, music, image assets, and
    its block in offline_radio.[mod].sii.
    """

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        outer = tk.Frame(self, padx=24, pady=20)
        outer.pack(fill="both", expand=True)

        heading = tk.Label(outer, text="Radio Stations", font=("Segoe UI", 18, "bold"))
        heading.pack(anchor="w")
        theme.style_heading(heading)

        self.mod_folder_label = tk.Label(outer, text="", font=("Segoe UI", 9), fg=theme.FG_MUTED)
        self.mod_folder_label.pack(anchor="w", pady=(2, 16))

        # Centered content block: pack()'s default behavior centers a
        # fixed-width, non-filled child horizontally within its parent.
        content = tk.Frame(outer, width=700)
        content.pack(pady=(0, 0))

        toolbar = tk.Frame(content)
        toolbar.pack(fill="x", pady=(0, 10))
        create_btn = tk.Button(toolbar, text="Create New Station", command=self._create_new)
        create_btn.pack(side="left")
        theme.style_primary_button(create_btn)

        self.delete_btn = tk.Button(
            toolbar, text="Delete Selected", command=self._delete_selected, state="disabled"
        )
        theme.style_danger_button(self.delete_btn)
        self.delete_btn.pack(side="left", padx=(8, 0))

        tk.Label(
            toolbar,
            text="Double-click to edit  \u00b7  click to select, Ctrl/Shift-click for multiple",
            font=("Segoe UI", 9),
            fg=theme.FG_MUTED,
        ).pack(side="left", padx=(14, 0))

        list_container = tk.Frame(content)
        list_container.pack(fill="both", expand=True)

        columns = ("name", "genre", "language", "tracks")
        self.tree = ttk.Treeview(
            list_container, columns=columns, show="headings", selectmode="extended", height=14
        )
        self.tree.heading("name", text="Station Name")
        self.tree.heading("genre", text="Genre")
        self.tree.heading("language", text="Lang")
        self.tree.heading("tracks", text="Tracks")
        self.tree.column("name", width=340, anchor="w")
        self.tree.column("genre", width=190, anchor="w")
        self.tree.column("language", width=60, anchor="center")
        self.tree.column("tracks", width=70, anchor="center")

        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_change)
        self.tree.bind("<Delete>", lambda e: self._delete_selected())

        bottom_row = tk.Frame(outer)
        bottom_row.pack(anchor="w", pady=(16, 0), fill="x")
        tk.Button(bottom_row, text="Back to Mod Setup", command=self._back).pack(side="left")

    # ---- lifecycle -----------------------------------------------------

    def on_show(self) -> None:
        project = self.controller.project
        self.mod_folder_label.configure(text=f"Mod folder: {project.mod_folder}")
        self.controller.stations = load_stations(project)
        self.controller.editing_station_index = None
        self._render_rows()

    def _render_rows(self) -> None:
        self.tree.delete(*self.tree.get_children())
        project = self.controller.project
        for i, fields in enumerate(self.controller.stations):
            station_id = fields.get("id", "")
            track_count = len(load_tracks(project, station_id)) if station_id else 0
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    fields.get("name", "(unnamed)"),
                    fields.get("genre", ""),
                    fields.get("language", ""),
                    track_count,
                ),
            )
        self._on_selection_change()

    def _on_selection_change(self, event=None) -> None:
        has_selection = bool(self.tree.selection())
        self.delete_btn.configure(state="normal" if has_selection else "disabled")

    # ---- actions ---------------------------------------------------------

    def _create_new(self) -> None:
        self.controller.editing_station_index = None
        from ui.create_edit_station_frame import CreateEditStationFrame
        self.controller.show_frame(CreateEditStationFrame)

    def _on_double_click(self, event) -> None:
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.controller.editing_station_index = int(item)
        from ui.create_edit_station_frame import CreateEditStationFrame
        self.controller.show_frame(CreateEditStationFrame)

    def _delete_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        indices = sorted((int(iid) for iid in selected), reverse=True)

        names = [self.controller.stations[i].get("name", "(unnamed)") for i in indices]
        preview = ", ".join(names[:5]) + ("..." if len(names) > 5 else "")
        confirmed = messagebox.askyesno(
            "Delete station(s)",
            f"Permanently delete {len(indices)} station(s): {preview}?\n\n"
            "This removes each station's folder, music, and image assets, and "
            "cannot be undone.",
        )
        if not confirmed:
            return

        stations = self.controller.stations
        try:
            for index in indices:  # descending order keeps earlier indices valid
                stations = station_ops.delete_station(self.controller.project, stations, index)
        except OSError as exc:
            messagebox.showerror("Can't delete", f"Something went wrong deleting a station:\n{exc}")

        self.controller.stations = stations
        self._render_rows()
        self.controller.set_status(f"Deleted {len(indices)} station(s).", kind="success")

    def _back(self) -> None:
        from ui.mod_setup_frame import ModSetupFrame
        self.controller.show_frame(ModSetupFrame)
