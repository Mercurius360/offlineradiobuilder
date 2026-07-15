import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from project import ModProject
import theme


class WelcomeFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        wrapper = tk.Frame(self)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        title = tk.Label(wrapper, text="Offline Radio Builder", font=("Segoe UI", 22, "bold"))
        title.pack(pady=(0, 6))
        theme.style_heading(title)

        tk.Label(
            wrapper,
            text="Build offline radio station mods for ATS / ETS2.",
            font=("Segoe UI", 11),
            fg=theme.FG_MUTED,
        ).pack(pady=(0, 30))

        btn_row = tk.Frame(wrapper)
        btn_row.pack()

        new_btn = tk.Button(
            btn_row, text="New Mod", width=18, height=2, font=("Segoe UI", 11), command=self._new_mod
        )
        new_btn.grid(row=0, column=0, padx=10)
        theme.style_primary_button(new_btn)

        tk.Button(
            btn_row, text="Edit Existing Mod", width=18, height=2, font=("Segoe UI", 11), command=self._edit_mod
        ).grid(row=0, column=1, padx=10)

    def _new_mod(self) -> None:
        location = filedialog.askdirectory(title="Choose where to build the mod")
        if not location:
            return
        self.controller.project = ModProject(build_location=Path(location), mod_title="")
        from ui.mod_setup_frame import ModSetupFrame
        self.controller.show_frame(ModSetupFrame)

    def _edit_mod(self) -> None:
        folder = filedialog.askdirectory(title="Select the existing mod folder")
        if not folder:
            return
        try:
            self.controller.project = ModProject.load_from_existing(Path(folder))
        except FileNotFoundError as exc:
            messagebox.showerror("Can't open mod", str(exc))
            return

        from ui.mod_setup_frame import ModSetupFrame
        self.controller.show_frame(ModSetupFrame)
