import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

import constants
import theme

ICON_PREVIEW_SIZE = (96, 96)
_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


class ModSetupFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._icon_photo = None  # keep a reference so Tk doesn't garbage-collect it

        outer = tk.Frame(self, padx=24, pady=20)
        outer.pack(fill="both", expand=True)

        heading = tk.Label(outer, text="Mod Setup", font=("Segoe UI", 18, "bold"))
        heading.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 16))
        theme.style_heading(heading)

        self.mod_title_var = tk.StringVar()
        self.name_of_mod_var = tk.StringVar()
        self.author_var = tk.StringVar()

        self._labeled_entry(outer, 1, "Mod Title (folder name)", self.mod_title_var)
        self._labeled_entry(outer, 2, "Name of Mod (display name)", self.name_of_mod_var)
        self._labeled_entry(outer, 3, "Author", self.author_var)

        tk.Label(outer, text="Description", font=("Segoe UI", 10, "bold")).grid(
            row=4, column=0, sticky="nw", pady=(10, 0)
        )
        self.description_text = tk.Text(outer, width=50, height=6, font=("Segoe UI", 10), wrap="word")
        self.description_text.grid(row=4, column=1, columnspan=2, sticky="w", pady=(10, 0))

        tk.Label(outer, text="Mod Image", font=("Segoe UI", 10, "bold")).grid(
            row=5, column=0, sticky="nw", pady=(14, 0)
        )
        icon_row = tk.Frame(outer)
        icon_row.grid(row=5, column=1, columnspan=2, sticky="w", pady=(14, 0))

        default_icon_text = "No image\n(drag PNG, JPEG,\n or JPG here)"
        if getattr(controller, "drag_drop_available", False):
            default_icon_text = "No image\n(drag PNG, JPEG,\n or JPG here)"
        self.icon_preview_label = tk.Label(
            icon_row, text=default_icon_text, width=14, height=6
        )
        theme.style_panel_box(self.icon_preview_label)
        self.icon_preview_label.pack(side="left", padx=(0, 12))
        tk.Button(icon_row, text="Browse...", command=self._browse_icon).pack(side="left")
        self._register_drop_target()

        tk.Label(
            outer,
            text=f"Scaled automatically to {constants.MOD_ICON_SIZE[0]} x {constants.MOD_ICON_SIZE[1]} px.",
            font=("Segoe UI", 9),
            fg=theme.FG_MUTED,
        ).grid(row=6, column=1, columnspan=2, sticky="w", pady=(4, 0))

        nav_row = tk.Frame(outer)
        nav_row.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(28, 0))
        tk.Button(nav_row, text="Back", width=12, command=self._back).pack(side="left")
        continue_btn = tk.Button(
            nav_row, text="Continue", width=14, font=("Segoe UI", 10, "bold"), command=self._continue
        )
        continue_btn.pack(side="right")
        theme.style_primary_button(continue_btn)

    def _labeled_entry(self, parent, row, label, var):
        tk.Label(parent, text=label, font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=6
        )
        tk.Entry(parent, textvariable=var, width=45).grid(row=row, column=1, columnspan=2, sticky="w", pady=6)

    def _register_drop_target(self) -> None:
        if not getattr(self.controller, "drag_drop_available", False):
            return
        try:
            from tkinterdnd2 import DND_FILES
            self.icon_preview_label.drop_target_register(DND_FILES)
            self.icon_preview_label.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass  # drag-and-drop is a bonus; Browse always works

    # ---- lifecycle -----------------------------------------------------

    def on_show(self) -> None:
        project = self.controller.project
        self.mod_title_var.set(project.mod_title)
        self.name_of_mod_var.set(project.name_of_mod)
        self.author_var.set(project.author)

        self.description_text.delete("1.0", "end")
        self.description_text.insert("1.0", project.description)

        preview_path = project.icon_source_path or project.icon_preview_path
        if preview_path:
            self._show_icon_preview(preview_path)
        else:
            self._icon_photo = None
            default_text = "No image"
            if getattr(self.controller, "drag_drop_available", False):
                default_text = "No image\n(drag here)"
            self.icon_preview_label.configure(image="", text=default_text)

    # ---- actions ---------------------------------------------------------

    def _browse_icon(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose mod icon",
            filetypes=[("Images", "*.png *.jpg *.jpeg")],
        )
        if not path:
            return
        self.controller.project.icon_source_path = Path(path)
        self._show_icon_preview(Path(path))

    def _on_drop(self, event) -> None:
        raw_paths = self.tk.splitlist(event.data)
        image_paths = [p for p in raw_paths if p.lower().endswith(_IMAGE_EXTENSIONS)]
        if not image_paths:
            messagebox.showwarning("Not an image", "Drop a PNG or JPG file here.")
            return
        path = Path(image_paths[0])
        self.controller.project.icon_source_path = path
        self._show_icon_preview(path)

    def _show_icon_preview(self, path: Path) -> None:
        try:
            with Image.open(path) as img:
                img = img.copy()
                img.thumbnail(ICON_PREVIEW_SIZE)
                self._icon_photo = ImageTk.PhotoImage(img)
            self.icon_preview_label.configure(image=self._icon_photo, text="")
        except Exception as exc:
            messagebox.showerror("Image error", f"Couldn't load that image:\n{exc}")

    def _back(self) -> None:
        from ui.welcome_frame import WelcomeFrame
        self.controller.show_frame(WelcomeFrame)

    def _continue(self) -> None:
        project = self.controller.project

        mod_title = self.mod_title_var.get().strip()
        name_of_mod = self.name_of_mod_var.get().strip()
        if not mod_title:
            messagebox.showwarning("Missing info", "Mod Title is required.")
            return
        if not name_of_mod:
            messagebox.showwarning("Missing info", "Name of Mod is required.")
            return

        project.mod_title = mod_title
        project.name_of_mod = name_of_mod
        project.author = self.author_var.get().strip()
        project.description = self.description_text.get("1.0", "end-1c")

        try:
            mod_folder = project.save()
        except FileExistsError as exc:
            messagebox.showerror("Can't save", str(exc))
            return
        except OSError as exc:
            messagebox.showerror("Can't save", f"Something went wrong writing to disk:\n{exc}")
            return

        self.controller.set_status(
            f"'{project.name_of_mod}' is built and ready to add stations.  ({mod_folder})",
            kind="success",
        )

        from ui.station_list_frame import StationListFrame
        self.controller.show_frame(StationListFrame)
