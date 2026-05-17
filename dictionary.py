"""
dictionary.py — SymSpell frequency dictionaries (base + personal).
"""

from __future__ import annotations

import importlib.resources
import shutil
import threading
from pathlib import Path

from symspellpy import SymSpell, Verbosity

from patterns import is_protected

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
BASE_FREQ = DATA_DIR / "frequency_base.txt"
PERSONAL_FREQ = DATA_DIR / "frequency_personal.txt"

_MAX_EDIT = 2
_PREFIX_LEN = 7
_PERSONAL_BOOST = 12

_lock = threading.Lock()
_engine: SymSpell | None = None
_session_corrections = 0


def session_correction_count() -> int:
    return _session_corrections


def ensure_data_files() -> None:
    """Bundle base English dictionary on first run."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if BASE_FREQ.exists():
        return
    pkg = importlib.resources.files("symspellpy")
    src = pkg / "frequency_dictionary_en_82_765.txt"
    shutil.copy(src, BASE_FREQ)
    if not PERSONAL_FREQ.exists():
        PERSONAL_FREQ.write_text("", encoding="utf-8")


def _load_engine() -> SymSpell:
    global _engine
    if _engine is not None:
        return _engine

    ensure_data_files()
    sym = SymSpell(_MAX_EDIT, _PREFIX_LEN)
    sym.load_dictionary(str(BASE_FREQ), term_index=0, count_index=1)
    if PERSONAL_FREQ.exists() and PERSONAL_FREQ.stat().st_size > 0:
        sym.load_dictionary(str(PERSONAL_FREQ), term_index=0, count_index=1)
    _engine = sym
    return sym


def reload_engine() -> SymSpell:
    global _engine
    with _lock:
        _engine = None
        return _load_engine()


def word_count() -> int:
    sym = _load_engine()
    return len(sym.words)


def correct_word(word: str) -> str | None:
    """
    Return corrected spelling, or None if no change / too short.
  """
    clean = word.strip()
    if len(clean) < 2:
        return None

    key = clean.lower()
    if is_protected(key):
        return None
    sym = _load_engine()

    suggestions = sym.lookup(
        key,
        Verbosity.CLOSEST,
        max_edit_distance=_MAX_EDIT,
        include_unknown=True,
    )
    if not suggestions:
        return None

    best = suggestions[0].term
    if best.lower() == key:
        return None

    return _apply_case(clean, best)


def record_correction(original: str, fixed: str) -> None:
    """Append personal frequency so future fixes prefer this word."""
    global _session_corrections
    key = fixed.lower().strip()
    if not key:
        return

    with _lock:
        _session_corrections += 1
        sym = _load_engine()
        sym.create_dictionary_entry(key, _PERSONAL_BOOST)
        _append_personal_frequency(key, _PERSONAL_BOOST)


def _append_personal_frequency(word: str, count: int) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing: dict[str, int] = {}
    if PERSONAL_FREQ.exists():
        for line in PERSONAL_FREQ.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].isalpha():
                try:
                    existing[parts[0].lower()] = int(parts[1])
                except ValueError:
                    continue
    existing[word.lower()] = existing.get(word.lower(), 0) + count
    lines = [f"{w} {existing[w]}" for w in sorted(existing)]
    PERSONAL_FREQ.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _apply_case(original: str, fixed: str) -> str:
    if original.isupper():
        return fixed.upper()
    if original and original[0].isupper():
        return fixed.capitalize()
    return fixed
