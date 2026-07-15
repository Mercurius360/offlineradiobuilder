"""
App: the root Tk window and frame-switching controller.

Frames are simple tk.Frame subclasses that live in ui/*.py. Each one takes
(parent, controller) and can define an optional on_show(self) hook that the
controller calls every time that frame is raised, so screens can refresh
themselves from controller.project instead of caching stale state.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

try:
    from tkinterdnd2 import TkinterDnD
    _TK_BASE = TkinterDnD.Tk
    _DRAG_DROP_AVAILABLE = True
except ImportError:
    _TK_BASE = tk.Tk
    _DRAG_DROP_AVAILABLE = False

from project import ModProject
import theme
from ui.welcome_frame import WelcomeFrame
from ui.mod_setup_frame import ModSetupFrame
from ui.station_list_frame import StationListFrame
from ui.create_edit_station_frame import CreateEditStationFrame

WINDOW_TITLE = "Offline Radio Builder"
WINDOW_SIZE = "1000x720"

_STATUS_COLORS = {
    "info": None,       # filled in after theme import (theme.FG_MUTED)
    "success": None,    # theme.SUCCESS
    "error": None,      # theme.ERROR
    "warning": None,    # theme.WARNING
}


def _resource_path(filename: str) -> Path:
    """
    Resolve a bundled resource (e.g. icon.ico) whether running from source
    or from a PyInstaller-frozen exe, where bundled data files get
    extracted to a temp dir at sys._MEIPASS rather than living next to the
    script.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / filename


class App(_TK_BASE):
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(820, 600)
        theme.apply_theme(self)
        theme.configure_ttk_style(self)
        self._set_window_icon()

        # Shared state for the mod currently being built/edited.
        self.project: ModProject | None = None
        self.stations: list[dict] = []
        self.editing_station_index: int | None = None

        # True only if tkinterdnd2 is installed -- drag-and-drop is a bonus,
        # not a requirement (every drop target has a Browse-button fallback).
        self.drag_drop_available = _DRAG_DROP_AVAILABLE

        # Persistent status bar, docked to the bottom of the window and
        # shared by every screen via controller.set_status(...), used
        # instead of interrupting popups for routine confirmations.
        self._status_clear_job = None
        self.status_bar = tk.Label(
            self,
            text="",
            anchor="w",
            font=(theme.FONT_FAMILY, 9),
            fg=theme.FG_MUTED,
            bg=theme.BG_PANEL,
            padx=12,
            pady=6,
        )
        self.status_bar.pack(side="bottom", fill="x")  # must pack before the container below

        container = tk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames: dict[type, tk.Frame] = {}
        frame_classes = (
            WelcomeFrame,
            ModSetupFrame,
            StationListFrame,
            CreateEditStationFrame,
        )
        for FrameClass in frame_classes:
            frame = FrameClass(parent=container, controller=self)
            self.frames[FrameClass] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(WelcomeFrame)

    def _set_window_icon(self) -> None:
        """
        Sets the running window's titlebar/taskbar icon on Windows and
        Linux. Without this, the window manager shows a generic default
        icon while the app is open even though the built executable itself
        has a custom one -- those are separate things in Tk. Windows uses
        iconbitmap() with the .ico; Linux window managers use iconphoto()
        with a plain PNG instead (iconbitmap() expects XBM/ICO, which isn't
        the right format there). macOS is skipped entirely: the Dock/Finder
        icon comes from the .app bundle's Info.plist (set at build time in
        the .spec file) instead.
        """
        try:
            if sys.platform == "win32":
                icon_path = _resource_path("icon.ico")
                if icon_path.exists():
                    self.iconbitmap(default=str(icon_path))
            elif sys.platform.startswith("linux"):
                icon_path = _resource_path("icon.png")
                if icon_path.exists():
                    photo = tk.PhotoImage(file=str(icon_path))
                    self.iconphoto(True, photo)
                    self._window_icon_photo = photo  # keep a reference alive
        except Exception:
            pass  # cosmetic only; never let a missing/bad icon block startup

    def set_status(self, message: str, kind: str = "info", timeout_ms: int | None = 6000) -> None:
        """
        Show a message in the bottom status bar instead of an interrupting
        popup. kind picks the text color: info/success/error/warning.
        Clears itself after timeout_ms (pass None to leave it showing).
        """
        colors = {
            "info": theme.FG_MUTED,
            "success": theme.SUCCESS,
            "error": theme.ERROR,
            "warning": theme.WARNING,
        }
        self.status_bar.configure(text=message, fg=colors.get(kind, theme.FG_MUTED))

        if self._status_clear_job is not None:
            self.after_cancel(self._status_clear_job)
            self._status_clear_job = None
        if timeout_ms:
            self._status_clear_job = self.after(timeout_ms, lambda: self.status_bar.configure(text=""))

    def show_frame(self, frame_class: type) -> None:
        frame = self.frames[frame_class]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()


def run() -> None:
    App().mainloop()
