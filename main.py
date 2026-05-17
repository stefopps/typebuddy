"""
TypeBuddy — Display-only: 6-row sentence buffer (5 completed + 1 active).
"""

from __future__ import annotations

import ctypes
import sys
import threading
import tkinter as tk

import keyboard
import win32gui

import pyperclip

import dictionary as dict_mod
from corrector import apply_fix, fix_word, pre_correct
from line_fix import capture_line, get_foreground_hwnd
from sentence_buffer import SentenceBuffer
from strip import StatusStrip

_word_buffer: list[str] = []
_buffer_lock = threading.Lock()
_sentences = SentenceBuffer()
_hook_registered = False
_strip: StatusStrip | None = None
_root: tk.Tk | None = None
_panel_hwnd: int | None = None
_last_target_hwnd: int | None = None
_busy = False


def _is_admin() -> bool:
    if sys.platform == "win32":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            pass
    return True


def _find_panel_hwnd() -> int | None:
    try:
        return ctypes.windll.user32.FindWindowW(None, "TypeBuddy")
    except Exception:
        return None


def _foreground_is_panel() -> bool:
    global _panel_hwnd
    if _panel_hwnd is None:
        return False
    try:
        return win32gui.GetForegroundWindow() == _panel_hwnd
    except Exception:
        return False


def _track_focus() -> None:
    global _last_target_hwnd, _panel_hwnd
    try:
        hwnd = get_foreground_hwnd()
        if hwnd and hwnd != _panel_hwnd:
            _last_target_hwnd = hwnd
    except Exception:
        pass
    if _root:
        _root.after(200, _track_focus)


def _refresh_display() -> None:
    if _strip is None:
        return
    _strip.set_sentence_rows(*_sentences.display_rows())
    with _buffer_lock:
        word = "".join(_word_buffer)
    _strip.set_typing(word)
    _strip.set_words(dict_mod.session_correction_count())


def _schedule_display() -> None:
    if _root is not None:
        _root.after(0, _refresh_display)


def _sync_word_buffer_from_sentence() -> None:
    """Keep partial-word buffer in sync with the active sentence text."""
    raw = _sentences.current_raw()
    with _buffer_lock:
        _word_buffer.clear()
        if not raw or raw.endswith(" "):
            return
        last_space = raw.rfind(" ")
        word = raw[last_space + 1 :] if last_space >= 0 else raw
        _word_buffer.extend(list(word))


def _ctrl_held() -> bool:
    return (
        keyboard.is_pressed("ctrl")
        or keyboard.is_pressed("left ctrl")
        or keyboard.is_pressed("right ctrl")
    )


def _clear_buffer() -> None:
    _sentences.clear_all()
    with _buffer_lock:
        _word_buffer.clear()
    _schedule_display()


def _on_copy_all() -> None:
    """Clipboard-only — all completed rows + active line."""
    if _strip is None:
        return
    full = _sentences.get_all_corrected()
    if not full:
        print("[TypeBuddy] Nothing to copy")
        return
    try:
        pyperclip.copy(full)
        print(f"[TypeBuddy] Copied to clipboard: {full[:80]}")
        if _root:
            _root.after(0, lambda: _strip.flash_copied())
    except Exception as e:
        print(f"[TypeBuddy] Clipboard error: {e}")


def _on_regenerate() -> None:
    global _busy
    if _busy or _strip is None:
        return
    _busy = True
    hwnd = _last_target_hwnd

    def _work():
        global _busy
        try:
            raw = capture_line(hwnd=hwnd).strip()
            if not raw:
                raw = _sentences.current_raw().strip()
            if not raw:
                return
            preview = pre_correct(raw)

            def _ui():
                _sentences.set_active_preview(preview)
                _refresh_display()

            if _root:
                _root.after(0, _ui)
        finally:
            _busy = False

    threading.Thread(target=_work, daemon=True).start()


def _on_key(event) -> None:
    if event.event_type != "down":
        return

    if _foreground_is_panel():
        return

    name = event.name

    if name == "backspace":
        if _ctrl_held():
            _sentences.backspace_word()
        else:
            _sentences.backspace()
        _sync_word_buffer_from_sentence()
        _schedule_display()
        return

    if name in ("space", "enter", "tab"):
        with _buffer_lock:
            word = "".join(_word_buffer)
            _word_buffer.clear()

        if name == "space":
            _sentences.append_space()
            _sync_word_buffer_from_sentence()
            if len(word) >= 2:
                result = fix_word(word)
                if result:
                    original, fixed = result
                    apply_fix(original, fixed)
                    if _strip:
                        _root.after(
                            0,
                            lambda o=original, f=fixed: _strip.set_last_fix(o, f),
                        )

        _schedule_display()
        return

    if len(name) == 1 and name in ".!?":
        with _buffer_lock:
            _word_buffer.clear()
        _sentences.append_char(name)
        _sentences.clear_active_override()
        _schedule_display()
        return

    if len(name) == 1 and name.isalpha():
        ch = name
        if keyboard.is_pressed("shift") or keyboard.is_pressed("right shift"):
            ch = ch.upper()
        with _buffer_lock:
            _word_buffer.append(ch)
        _sentences.append_char(ch)
        _sentences.clear_active_override()
        _sync_word_buffer_from_sentence()
        _schedule_display()
        return

    if len(name) == 1 and name in ".,;:":
        _sentences.append_char(name)
        _sync_word_buffer_from_sentence()
        _schedule_display()
        return


def register_hook() -> None:
    global _hook_registered
    if _hook_registered:
        return
    keyboard.hook(_on_key, suppress=False)
    _hook_registered = True


def run_app() -> None:
    global _strip, _root, _panel_hwnd

    dict_mod.ensure_data_files()
    dict_mod._load_engine()

    _root = tk.Tk()
    _strip = StatusStrip(
        _root,
        on_accept=_on_copy_all,
        on_regenerate=_on_regenerate,
        on_clear=_clear_buffer,
    )

    def _track_panel():
        global _panel_hwnd
        _panel_hwnd = _find_panel_hwnd()
        _root.after(500, _track_panel)

    _root.after(200, _track_panel)
    _root.after(300, _track_focus)
    _strip.start_lazy_follow(initial_ms=1000)

    register_hook()
    _strip.set_listening(True)
    _refresh_display()

    print("[TypeBuddy] 6-row buffer | right-click to freeze follow (drag anytime)")
    print("[TypeBuddy] ⎘ Copy = one click → clipboard (paste manually)")
    if not _is_admin():
        print("[TypeBuddy] Run START_TYPEBUDDY.bat as Administrator for global hooks.")

    _root.mainloop()


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    run_app()
