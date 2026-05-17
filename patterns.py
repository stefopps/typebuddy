"""
patterns.py — Load learned typo patterns from FixIt memory.json (read-only).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
MEMORY_FILE = _ROOT / "memory.json"
_FIXIT_MEMORY = _ROOT.parent / "fixit" / "memory.json"


def _memory_path() -> Path:
    if MEMORY_FILE.exists():
        return MEMORY_FILE
    if _FIXIT_MEMORY.exists():
        return _FIXIT_MEMORY
    return MEMORY_FILE
_PUNCT = ".,!?;:'\""
_CACHE: tuple[float, dict[str, dict], frozenset[str]] | None = None


def _load_memory() -> tuple[dict[str, dict], frozenset[str]]:
    global _CACHE
    path = _memory_path()
    mtime = path.stat().st_mtime if path.exists() else 0.0
    if _CACHE is not None and _CACHE[0] == mtime:
        return _CACHE[1], _CACHE[2]
    patterns: dict[str, dict] = {}
    protected: frozenset[str] = frozenset()
    path = _memory_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            patterns = data.get("patterns", {}) or {}
            protected = frozenset(
                t.lower() for t in data.get("dictionary", []) if t
            )
        except Exception:
            pass
    _CACHE = (mtime, patterns, protected)
    return patterns, protected


def _load_patterns() -> dict[str, dict]:
    patterns, _ = _load_memory()
    return patterns


def is_protected(word: str) -> bool:
    """Terms in memory.json dictionary — never autocorrect."""
    _, protected = _load_memory()
    return word.lower().strip() in protected


def _strip_word_punct(word: str) -> tuple[str, str, str]:
    lead = ""
    clean = word
    while clean and clean[0] in _PUNCT:
        lead += clean[0]
        clean = clean[1:]
    trail = ""
    while clean and clean[-1] in _PUNCT:
        trail = clean[-1] + trail
        clean = clean[:-1]
    return clean, trail, lead


def _apply_phrase_patterns(text: str, patterns: dict, min_count: int) -> str:
    """Multi-word keys (e.g. 'thi sone' → 'this one') — longest match first."""
    phrases = [
        (k, e["fixed"])
        for k, e in patterns.items()
        if " " in k and e.get("count", 0) >= min_count
    ]
    if not phrases:
        return text
    phrases.sort(key=lambda x: -len(x[0]))
    for key, fixed in phrases:
        text = re.sub(re.escape(key), fixed, text, flags=re.IGNORECASE)
    return text


def apply_patterns(text: str, min_count: int = 2) -> str:
    """Replace phrase + token patterns from memory.json (count >= min_count)."""
    if not text or not text.strip():
        return text
    patterns = _load_patterns()
    if not patterns:
        return text

    protected = _load_memory()[1]
    text = _apply_phrase_patterns(text, patterns, min_count)

    out: list[str] = []
    for word in text.split():
        clean, trail, lead = _strip_word_punct(word)
        key = clean.lower()
        if key in protected:
            out.append(word)
            continue
        entry = patterns.get(key)
        if entry and entry.get("count", 0) >= min_count:
            fixed = entry.get("fixed", clean)
            if clean and clean[0].isupper():
                fixed = str(fixed).capitalize()
            out.append(lead + fixed + trail)
        else:
            out.append(word)
    return " ".join(out)
