"""
flow_bridge.py — Optional Flow key-7 correction (sibling fixit/ install).
Not imported at TypeBuddy startup; only used on Accept when Flow is available.
"""

from __future__ import annotations

import sys
from pathlib import Path

FIXIT_DIR = Path(__file__).resolve().parent.parent / "fixit"


def flow_key7_correct(text: str, hwnd: int = 0) -> str | None:
    """
    Run Flow's local correct_text (Ollama spelling pass).
    Returns None if fixit is missing or the call fails.
    """
    if not text or not text.strip():
        return text
    if not FIXIT_DIR.is_dir():
        return None

    fixit_path = str(FIXIT_DIR)
    if fixit_path not in sys.path:
        sys.path.insert(0, fixit_path)

    try:
        from corrector import correct_text  # fixit package

        out = correct_text(text, hwnd=hwnd)
        return out if out and out.strip() else None
    except Exception as exc:
        print(f"[TypeBuddy] Flow key-7 skipped: {exc}")
        return None
