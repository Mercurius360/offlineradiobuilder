"""
Small modal dialog shown once Build Station finishes writing everything to
disk. Building is fast enough (station info + image conversion + track
copying all happen synchronously in well under a second for realistic
playlists) that a step-by-step progress bar isn't worth the visual noise --
this just confirms completion with an OK button.
"""

import tkinter as tk

import theme


class BuildProgressDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Building Station")
        self.configure(bg=theme.BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._outer = tk.Frame(self, padx=28, pady=22, bg=theme.BG)
        self._outer.pack()

        self.message_label = tk.Label(
            self._outer,
            text="Building station...",
            font=(theme.FONT_FAMILY, 10),
            fg=theme.FG,
            bg=theme.BG,
            width=40,
            anchor="w",
        )
        self.message_label.pack(anchor="w")

        # Center over the parent window.
        self.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

        self.protocol("WM_DELETE_WINDOW", lambda: None)  # not closeable until complete() runs

    def complete(self, message: str, on_ok) -> None:
        """Switch the dialog to a completion state with an OK button."""
        self.message_label.configure(text=message, fg=theme.SUCCESS)

        def _confirm():
            self.grab_release()
            self.destroy()
            on_ok()

        ok_btn = tk.Button(self._outer, text="OK", width=10, command=_confirm)
        theme.style_primary_button(ok_btn)
        ok_btn.pack(pady=(14, 0))
        self.protocol("WM_DELETE_WINDOW", _confirm)
        ok_btn.focus_set()

    def fail(self) -> None:
        self.grab_release()
        self.destroy()
