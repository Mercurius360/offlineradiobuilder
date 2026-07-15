"""
A single dark color palette + a function that installs it as the default
for every widget via Tk's option database (root.option_add). Individual
frames only need to override colors for things that must stand out (panel
boxes, muted/help text, primary action buttons) -- everything else (plain
Frames, Labels, Entries, Checkbuttons, Canvases, Scrollbars) picks up the
theme automatically since option_add applies globally by widget class.
"""

import tkinter as tk

BG = "#1e1e1e"            # window / frame background
BG_PANEL = "#2a2a2d"       # preview boxes, drop zones
BG_INPUT = "#2d2d30"       # entries / text widgets
BORDER = "#3f3f42"

FG = "#e8e8e8"             # primary text
FG_MUTED = "#9a9a9a"       # secondary / help text
FG_FAINT = "#707070"       # placeholder-style text

ACCENT = "#4fa3ff"         # headings, primary buttons
ACCENT_HOVER = "#6db4ff"
ACCENT_TEXT = "#0b1b2b"    # text color on top of ACCENT

BTN_BG = "#3a3d41"
BTN_ACTIVE_BG = "#4a4d51"
BTN_FG = "#f0f0f0"

ERROR = "#ff6b6b"
WARNING = "#e0a458"
SUCCESS = "#6bcf7f"

FONT_FAMILY = "Segoe UI"


DANGER = "#e05a4e"
DANGER_HOVER = "#f06f62"


def apply_theme(root: tk.Tk) -> None:
    root.configure(bg=BG)

    root.option_add("*Background", BG)
    root.option_add("*Foreground", FG)
    root.option_add("*Font", (FONT_FAMILY, 10))

    root.option_add("*Entry.Background", BG_INPUT)
    root.option_add("*Entry.Foreground", FG)
    root.option_add("*Entry.insertBackground", FG)
    root.option_add("*Entry.relief", "flat")
    root.option_add("*Entry.highlightThickness", 1)
    root.option_add("*Entry.highlightBackground", BORDER)
    root.option_add("*Entry.highlightColor", ACCENT)
    root.option_add("*Entry.disabledBackground", BG)
    root.option_add("*Entry.disabledForeground", FG_FAINT)

    root.option_add("*Text.Background", BG_INPUT)
    root.option_add("*Text.Foreground", FG)
    root.option_add("*Text.insertBackground", FG)
    root.option_add("*Text.relief", "flat")
    root.option_add("*Text.highlightThickness", 1)
    root.option_add("*Text.highlightBackground", BORDER)
    root.option_add("*Text.highlightColor", ACCENT)

    root.option_add("*Button.Background", BTN_BG)
    root.option_add("*Button.Foreground", BTN_FG)
    root.option_add("*Button.activeBackground", BTN_ACTIVE_BG)
    root.option_add("*Button.activeForeground", BTN_FG)
    root.option_add("*Button.relief", "flat")
    root.option_add("*Button.borderWidth", 1)
    root.option_add("*Button.highlightThickness", 0)
    root.option_add("*Button.padX", 10)
    root.option_add("*Button.padY", 5)
    root.option_add("*Button.cursor", "hand2")

    root.option_add("*Checkbutton.Background", BG)
    root.option_add("*Checkbutton.activeBackground", BG)
    root.option_add("*Checkbutton.selectColor", BG_INPUT)
    root.option_add("*Checkbutton.Foreground", FG)
    root.option_add("*Checkbutton.activeForeground", FG)

    root.option_add("*Canvas.Background", BG)
    root.option_add("*Canvas.highlightThickness", 0)

    root.option_add("*Scrollbar.Background", BG_PANEL)
    root.option_add("*Scrollbar.troughColor", BG)
    root.option_add("*Scrollbar.activeBackground", BTN_ACTIVE_BG)
    root.option_add("*Scrollbar.highlightThickness", 0)
    root.option_add("*Scrollbar.borderWidth", 0)


def configure_ttk_style(root: tk.Tk) -> None:
    """
    ttk widgets (Treeview, Progressbar) don't pick up option_add -- they
    need an explicit ttk.Style. 'clam' is used as the base because it's
    the most reliably re-themeable built-in ttk theme across platforms.
    """
    from tkinter import ttk

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        "Treeview",
        background=BG_INPUT,
        fieldbackground=BG_INPUT,
        foreground=FG,
        bordercolor=BORDER,
        borderwidth=0,
        rowheight=26,
        font=(FONT_FAMILY, 10),
    )
    style.map(
        "Treeview",
        background=[("selected", ACCENT)],
        foreground=[("selected", ACCENT_TEXT)],
    )
    style.configure(
        "Treeview.Heading",
        background=BG_PANEL,
        foreground=FG,
        font=(FONT_FAMILY, 9, "bold"),
        relief="flat",
        borderwidth=1,
    )
    style.map("Treeview.Heading", background=[("active", BTN_ACTIVE_BG)])

    style.configure(
        "TProgressbar",
        background=ACCENT,
        troughcolor=BG_PANEL,
        bordercolor=BORDER,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
    )

    style.configure(
        "Vertical.TScrollbar",
        background=BG_PANEL,
        troughcolor=BG,
        bordercolor=BORDER,
        arrowcolor=FG,
    )


def style_primary_button(button: tk.Button) -> None:
    """Give a call-to-action button (Continue/Next/Finish/Build) the accent color."""
    button.configure(
        bg=ACCENT,
        fg=ACCENT_TEXT,
        activebackground=ACCENT_HOVER,
        activeforeground=ACCENT_TEXT,
    )


def style_danger_button(button: tk.Button) -> None:
    """Destructive action (Delete) gets a distinct red so it doesn't blend with neutral buttons."""
    button.configure(
        bg=DANGER,
        fg="#ffffff",
        activebackground=DANGER_HOVER,
        activeforeground="#ffffff",
    )


def style_panel_box(widget: tk.Widget) -> None:
    """Flat dark panel look for preview boxes / drop zones (replaces relief=groove)."""
    widget.configure(
        bg=BG_PANEL,
        fg=FG_MUTED,
        relief="flat",
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=BORDER,
    )


def style_heading(label: tk.Label) -> None:
    label.configure(fg=ACCENT)
