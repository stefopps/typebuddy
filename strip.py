"""
strip.py — TypeBuddy display-only: 6 × 100-char sentences, dock/close controls.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

import win32api

from sentence_buffer import NUM_ROWS, display_sentence

BAR_W = 720
TITLE_H = 32
ROW_H = 28
BTN_H = 36
TOTAL_H = TITLE_H + ROW_H * NUM_ROWS + BTN_H

_DOCK_ORANGE = "#fb923c"
_ICON_DIM = "#3a3a40"
_ICON_FLASH = "#e8e8e8"
_CLOSE_HOVER = "#f87171"


class StatusStrip:
    _BG = "#121214"
    _SURFACE = "#1a1a1c"
    _BORDER = "#2a2a2e"
    _FG = "#e8e8e8"
    _FG_DIM = "#5a5a62"
    _FG_TYPING = "#a8a8b0"
    _GREEN = "#4ade80"
    _ACCENT = "#22d3ee"
    _FONT = ("Segoe UI", 9)
    _FONT_BRAND = ("Segoe UI", 9, "bold")
    _FONT_ROW = ("Consolas", 10)
    _FONT_MONO = ("Consolas", 10)

    def __init__(
        self,
        root: tk.Tk,
        *,
        on_accept: Callable[[], None] | None = None,
        on_regenerate: Callable[[], None] | None = None,
        on_clear: Callable[[], None] | None = None,
    ) -> None:
        self.root = root
        self._on_accept = on_accept
        self._on_regenerate = on_regenerate
        self._on_clear = on_clear
        self._docked_top = False
        self._float_geom: str | None = None

        root.title("TypeBuddy")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=self._BG)
        root.minsize(BAR_W, TOTAL_H)
        root.geometry(f"{BAR_W}x{TOTAL_H}+0+0")

        self._outer = tk.Frame(root, bg=self._BG, width=BAR_W)
        self._outer.pack(fill="both", expand=True)

        self.bar_frame = tk.Frame(self._outer, bg=self._BG, height=TITLE_H)
        self.bar_frame.pack(fill="x")
        self.bar_frame.pack_propagate(False)
        self._bind_drag(self.bar_frame)

        tk.Label(
            self.bar_frame,
            text="TypeBuddy",
            bg=self._BG,
            fg=self._ACCENT,
            font=self._FONT_BRAND,
            padx=8,
        ).pack(side="left")

        self._sep(self.bar_frame)

        self._typing_var = tk.StringVar(value="typing: —")
        tk.Label(
            self.bar_frame,
            textvariable=self._typing_var,
            bg=self._BG,
            fg=self._FG_TYPING,
            font=self._FONT,
            padx=4,
        ).pack(side="left")

        self._sep(self.bar_frame)

        self._last_var = tk.StringVar(value="last fix: —")
        tk.Label(
            self.bar_frame,
            textvariable=self._last_var,
            bg=self._BG,
            fg=self._FG,
            font=self._FONT,
            padx=4,
        ).pack(side="left")

        self._sep(self.bar_frame)

        self._words_var = tk.StringVar(value="words: 0")
        tk.Label(
            self.bar_frame,
            textvariable=self._words_var,
            bg=self._BG,
            fg=self._FG_DIM,
            font=self._FONT,
            padx=4,
        ).pack(side="left")

        # Right-aligned: | ⌫ ⚓ ✕ (pack side=right, first = rightmost)
        self._sep(self.bar_frame, side="right", padx=(4, 8))

        self.close_btn = tk.Button(
            self.bar_frame,
            text="✕",
            command=root.destroy,
            bg=self._BG,
            fg=_ICON_DIM,
            activebackground=self._BG,
            activeforeground=_CLOSE_HOVER,
            relief="flat",
            cursor="hand2",
            font=(self._FONT_MONO[0], 11),
            padx=8,
            bd=0,
        )
        self.close_btn.pack(side="right")
        self.close_btn.bind("<Enter>", lambda _e: self.close_btn.config(fg=_CLOSE_HOVER))
        self.close_btn.bind("<Leave>", lambda _e: self.close_btn.config(fg=_ICON_DIM))

        self.dock_btn = tk.Button(
            self.bar_frame,
            text="⚓",
            command=self._toggle_dock,
            bg=self._BG,
            fg=_ICON_DIM,
            activebackground=self._BG,
            activeforeground=_DOCK_ORANGE,
            relief="flat",
            cursor="hand2",
            font=(self._FONT_MONO[0], 11),
            padx=8,
            bd=0,
        )
        self.dock_btn.pack(side="right")

        self.clear_btn = tk.Button(
            self.bar_frame,
            text="⌫",
            command=self._clear_click,
            bg=self._BG,
            fg=_ICON_DIM,
            activebackground=self._BG,
            activeforeground=_ICON_FLASH,
            relief="flat",
            cursor="hand2",
            font=(self._FONT_MONO[0], 11),
            padx=8,
            bd=0,
        )
        self.clear_btn.pack(side="right")

        self._text_block = tk.Frame(self._outer, bg=self._BG)
        self._text_block.pack(fill="x")

        self._row_vars: list[tk.StringVar] = []
        self._row_labels: list[tk.Label] = []
        self._sentence_rows: list[tk.Frame] = []
        for i in range(NUM_ROWS):
            row = tk.Frame(self._text_block, bg=self._BG, height=ROW_H)
            row.pack(fill="x")
            row.pack_propagate(False)
            self._sentence_rows.append(row)
            self._bind_drag(row)
            var = tk.StringVar(value="—")
            lbl = tk.Label(
                row,
                textvariable=var,
                bg=self._BG,
                fg=self._FG if i == NUM_ROWS - 1 else self._FG_DIM,
                font=self._FONT_ROW,
                anchor="w",
            )
            lbl.pack(side="left", fill="x", expand=True, padx=(10, 10))
            self._bind_drag(lbl)
            self._row_vars.append(var)
            self._row_labels.append(lbl)

        btn_row = tk.Frame(self._outer, bg=self._BG, height=BTN_H)
        btn_row.pack(fill="x")
        btn_row.pack_propagate(False)
        inner = tk.Frame(btn_row, bg=self._BG)
        inner.pack(expand=True)

        self.accept_btn = tk.Button(
            inner,
            text="⎘ Copy",
            command=self._accept_click,
            bg=self._GREEN,
            fg="#000",
            font=(self._FONT[0], 9, "bold"),
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
        )
        self.accept_btn.pack(side="left", padx=6)
        self._accept_reset_id: str | None = None
        self._ACCEPT_LABEL = "⎘ Copy"
        self._ACCEPT_GREEN = self._GREEN
        self._ACCEPT_COPIED_BG = "#166534"

        tk.Button(
            inner,
            text="↺ Regenerate",
            command=self._regenerate_click,
            bg=self._BORDER,
            fg=self._FG,
            font=self._FONT,
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
        ).pack(side="left", padx=6)

        self.bar_frame.bind(
            "<Double-Button-1>",
            lambda _e: self._undock() if self._docked_top else self.snap_to_cursor(),
        )
        self._bind_dock_toggle(self.bar_frame)
        self._bind_dock_toggle(self._text_block)
        for row in self._sentence_rows:
            self._bind_dock_toggle(row)
        self._bind_dock_toggle(btn_row)

    def _bind_drag(self, widget: tk.Widget) -> None:
        widget.bind("<ButtonPress-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._do_drag)

    def _start_drag(self, event) -> None:
        self.root._drag_x = event.x
        self.root._drag_y = event.y

    def _do_drag(self, event) -> None:
        x = self.root.winfo_x() + (event.x - self.root._drag_x)
        y = self.root.winfo_y() + (event.y - self.root._drag_y)
        self.root.geometry(f"{BAR_W}x{TOTAL_H}+{x}+{y}")

    def _bind_dock_toggle(self, widget: tk.Widget) -> None:
        """Right-click anywhere on bound widgets toggles dock/undock."""
        widget.bind("<Button-3>", self._on_right_click)
        for child in widget.winfo_children():
            self._bind_dock_toggle(child)

    def _toggle_dock(self) -> None:
        if self._docked_top:
            self._undock()
            print("[TypeBuddy] Undocked — following cursor")
        else:
            self._dock_freeze()
            print("[TypeBuddy] Docked — frozen at current position")

    def _on_right_click(self, _event=None) -> None:
        self._toggle_dock()

    def _dock_freeze(self) -> None:
        """Freeze window here — stops lazy follow only."""
        self._docked_top = True
        self.dock_btn.config(fg=_DOCK_ORANGE)

    def _undock(self) -> None:
        self._docked_top = False
        self.dock_btn.config(fg=_ICON_DIM)

    def snap_to_cursor(self) -> None:
        if self._docked_top:
            return
        try:
            x, y = win32api.GetCursorPos()
        except Exception:
            return
        sw = self.root.winfo_screenwidth()
        bx = max(0, min(x - BAR_W // 2, sw - BAR_W))
        by = max(0, y - 56)
        self.root.geometry(f"{BAR_W}x{TOTAL_H}+{bx}+{by}")

    def start_lazy_follow(self, initial_ms: int = 1000) -> None:
        self.root.after(initial_ms, self._lazy_follow)

    def _lazy_follow(self) -> None:
        if not self._docked_top:
            self.snap_to_cursor()
        try:
            self.root.after(2000, self._lazy_follow)
        except tk.TclError:
            pass

    def set_sentence_rows(self, *rows: str) -> None:
        for i in range(NUM_ROWS):
            text = rows[i] if i < len(rows) else "—"
            self._row_vars[i].set(display_sentence(text, 100))
            self._row_labels[i].config(
                fg=self._FG if i == NUM_ROWS - 1 else self._FG_DIM
            )

    def set_last_fix(self, original: str, fixed: str) -> None:
        o = original[:18] + ("…" if len(original) > 18 else "")
        f = fixed[:18] + ("…" if len(fixed) > 18 else "")
        self._last_var.set(f'last fix: "{o}" → "{f}"')

    def set_typing(self, word: str) -> None:
        if word:
            self._typing_var.set(f'typing: "{word}▌"')
        else:
            self._typing_var.set("typing: —")

    def set_words(self, count: int) -> None:
        self._words_var.set(f"words: {count:,}")

    def set_listening(self, on: bool) -> None:
        pass

    def _clear_click(self) -> None:
        try:
            self.clear_btn.config(fg=_ICON_FLASH)
            self.root.after(150, lambda: self.clear_btn.config(fg=_ICON_DIM))
        except tk.TclError:
            pass
        if self._on_clear:
            self._on_clear()

    def flash_copied(self) -> None:
        try:
            self.accept_btn.config(text="⎘ Copied!", bg=self._ACCEPT_COPIED_BG)
            if self._accept_reset_id:
                self.root.after_cancel(self._accept_reset_id)
            self._accept_reset_id = self.root.after(1200, self._reset_accept_btn)
        except tk.TclError:
            pass

    def _reset_accept_btn(self) -> None:
        self._accept_reset_id = None
        try:
            self.accept_btn.config(text=self._ACCEPT_LABEL, bg=self._ACCEPT_GREEN)
        except tk.TclError:
            pass

    def _accept_click(self) -> None:
        if self._on_accept:
            self._on_accept()

    def _regenerate_click(self) -> None:
        if self._on_regenerate:
            self._on_regenerate()

    def _sep(
        self, parent: tk.Frame, *, side: str = "left", padx: tuple[int, int] = (0, 0)
    ) -> None:
        tk.Label(parent, text="|", bg=self._BG, fg="#2a2a2e", font=self._FONT).pack(
            side=side, padx=padx
        )
