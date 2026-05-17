"""
line_fix.py — Capture / correct / replace current line in target field.
"""

from __future__ import annotations

import ctypes
import time

import keyboard
import pyperclip
import win32api
import win32gui

from corrector import pre_correct


def get_foreground_hwnd() -> int | None:
    try:
        hwnd = win32gui.GetForegroundWindow()
        return hwnd if hwnd else None
    except Exception:
        return None


def force_focus(hwnd: int) -> None:
    try:
        fg = win32gui.GetForegroundWindow()
        fg_tid = win32api.GetWindowThreadProcessId(fg)[0]
        our_tid = win32api.GetCurrentThreadId()
        attached = False
        if fg_tid != our_tid:
            ctypes.windll.user32.AttachThreadInput(fg_tid, our_tid, True)
            attached = True
        win32gui.SetForegroundWindow(hwnd)
        if attached:
            ctypes.windll.user32.AttachThreadInput(fg_tid, our_tid, False)
    except Exception:
        pass
    time.sleep(0.06)


def capture_line(hwnd: int | None = None) -> str:
    """Select current line via End → Shift+Home → Ctrl+C."""
    saved = ""
    try:
        saved = pyperclip.paste()
    except Exception:
        pass

    if hwnd:
        force_focus(hwnd)

    keyboard.send("end")
    time.sleep(0.03)
    keyboard.send("shift+home")
    time.sleep(0.03)
    keyboard.send("ctrl+c")
    time.sleep(0.12)

    try:
        raw = pyperclip.paste()
    except Exception:
        raw = ""

    try:
        pyperclip.copy(saved)
    except Exception:
        pass

    return raw or ""


def accept_line(fixed: str, hwnd: int | None = None) -> None:
    """Replace current line with fixed text."""
    if hwnd:
        force_focus(hwnd)

    pyperclip.copy(fixed)
    time.sleep(0.03)
    keyboard.send("end")
    time.sleep(0.03)
    keyboard.send("shift+home")
    time.sleep(0.03)
    keyboard.send("ctrl+v")
    time.sleep(0.04)


def correct_line(raw: str) -> str:
    return pre_correct(raw)
