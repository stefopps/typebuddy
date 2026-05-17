"""
caret_hud.py — Floating keystroke tracker anchored near the text caret.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import tkinter as tk

user32 = ctypes.windll.user32
MONITOR_DEFAULTTONEAREST = 2

_BG = "#1a1a1c"
_FG = "#e8e8e8"
_FG_DIM = "#6b6b72"
_FG_FIX = "#4ade80"
_FG_WORD = "#22d3ee"
_FONT = ("Consolas", 10)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_uint),
    ]


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("hwndActive", ctypes.wintypes.HWND),
        ("hwndFocus", ctypes.wintypes.HWND),
        ("hwndCapture", ctypes.wintypes.HWND),
        ("hwndMenuOwner", ctypes.wintypes.HWND),
        ("hwndMoveSize", ctypes.wintypes.HWND),
        ("hwndCaret", ctypes.wintypes.HWND),
        ("rcCaret", RECT),
    ]


def get_caret_screen_pos() -> tuple[int, int] | None:
    info = GUITHREADINFO()
    info.cbSize = ctypes.sizeof(GUITHREADINFO)
    hwnd_fg = user32.GetForegroundWindow()
    thread_id = user32.GetWindowThreadProcessId(hwnd_fg, None)
    if not user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
        if not user32.GetGUIThreadInfo(0, ctypes.byref(info)):
            return None
    hwnd = info.hwndCaret or info.hwndFocus or info.hwndActive
    if not hwnd:
        return None
    pt = POINT(info.rcCaret.left, info.rcCaret.bottom)
    if not user32.ClientToScreen(hwnd, ctypes.byref(pt)):
        return None
    return pt.x, pt.y


def _work_area(x: int, y: int) -> RECT:
    pt = POINT(x, y)
    hmon = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
    if not hmon:
        return RECT(0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
        return mi.rcWork
    return RECT(0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))


class CaretHud:
    """Small HUD that follows the caret and shows live keystrokes."""

    def __init__(self, master: tk.Misc) -> None:
        self.root = tk.Toplevel(master)
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.94)
        self.root.configure(bg=_BG)

        frame = tk.Frame(self.root, bg=_BG, padx=8, pady=5)
        frame.pack()

        self._keys_var = tk.StringVar(value="")
        tk.Label(
            frame,
            textvariable=self._keys_var,
            bg=_BG,
            fg=_FG_WORD,
            font=_FONT,
            anchor="w",
        ).pack(anchor="w")

        self._fix_var = tk.StringVar(value="")
        tk.Label(
            frame,
            textvariable=self._fix_var,
            bg=_BG,
            fg=_FG_FIX,
            font=_FONT,
            anchor="w",
        ).pack(anchor="w")

        self._visible = False
        self._caret_y = 0
        self._hide_after_id: str | None = None

    def set_keystrokes(self, tail: str, current_word: str) -> None:
        tail = tail[-28:]
        word = current_word[-24:]
        if word:
            text = f"⌨ …{tail}{word}│"
        elif tail:
            text = f"⌨ …{tail}"
        else:
            self.hide()
            return
        self._keys_var.set(text)
        self._show_at_caret()

    def flash_fix(self, original: str, fixed: str) -> None:
        self._fix_var.set(f'✓ "{original}" → "{fixed}"')
        if self._hide_after_id:
            try:
                self.root.after_cancel(self._hide_after_id)
            except Exception:
                pass
        self._hide_after_id = self.root.after(2500, lambda: self._fix_var.set(""))

    def hide(self) -> None:
        if self._visible:
            self.root.withdraw()
            self._visible = False

    def _show_at_caret(self) -> None:
        pos = get_caret_screen_pos()
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()

        if pos:
            x, y = pos
            self._caret_y = y
            y = y + 8
        else:
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery() + 16
            self._caret_y = y

        if pos:
            work = _work_area(x, self._caret_y)
            edge = 6
            if x + w > work.right:
                x = work.right - w - edge
            if x < work.left:
                x = work.left + edge
            if y + h > work.bottom:
                y = self._caret_y - h - 8
            if y < work.top:
                y = work.top + edge

        self.root.geometry(f"+{x}+{y}")
        if not self._visible:
            self.root.deiconify()
            self.root.lift()
            self._visible = True

    def reposition(self) -> None:
        if self._visible:
            self._show_at_caret()

    def tick(self) -> None:
        try:
            self.root.update_idletasks()
        except tk.TclError:
            pass
