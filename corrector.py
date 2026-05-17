"""
corrector.py — Pre-correct (doubles + SymSpell) and optional Flow key-7 pass.
"""

from __future__ import annotations

import re

import dictionary as dict_mod
from patterns import apply_patterns, is_protected

_PUNCT = ".,!?;:'\""


def _clean_doubles_word(word: str) -> str:
    """Single-token double-strike fix (pass 0)."""
    if len(word) >= 4 and word[0] == word[1] and word[0].isalpha():
        return word[1:]
    return word


def _clean_doubles(text: str) -> str:
    """
    Pass 0 — remove double-struck first letters at word boundaries.
    'ddonewant' → 'donewant', 'sshouldchange' → 'shouldchange'
    """

    def fix_word(m: re.Match) -> str:
        return _clean_doubles_word(m.group(0))

    return re.sub(r"\b[a-zA-Z]{4,}\b", fix_word, text)


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


def pre_correct(text: str) -> str:
    """Pass 0: doubles. Pass 1: memory.json patterns. Pass 2: SymSpell."""
    if not text or not text.strip():
        return text
    text = _clean_doubles(text)
    text = apply_patterns(text)
    return fix_line(text, doubles_done=True)


def fix_word(word: str) -> tuple[str, str] | None:
    """If word is corrected, return (original, fixed)."""
    if is_protected(word.strip()):
        return None
    cleaned = _clean_doubles_word(word)
    if not cleaned:
        cleaned = _clean_doubles(word)
    patterned = apply_patterns(cleaned, min_count=2)
    if patterned != cleaned:
        if patterned.lower() != word.lower():
            return word, patterned
    fixed = dict_mod.correct_word(cleaned)
    result = fixed if fixed else cleaned
    if result == word:
        return None
    return word, result


def fix_line(text: str, *, doubles_done: bool = False) -> str:
    """SymSpell each token (pass 0 doubles unless already applied)."""
    if not text or not text.strip():
        return text

    if not doubles_done:
        text = _clean_doubles(text)

    out: list[str] = []
    for word in text.split():
        clean, trail, lead = _strip_word_punct(word)
        if not clean:
            out.append(word)
            continue
        if is_protected(clean):
            out.append(word)
            continue
        clean = _clean_doubles_word(clean)
        fixed = dict_mod.correct_word(clean)
        if fixed and fixed.lower() != clean.lower():
            if clean and clean[0].isupper():
                fixed = fixed.capitalize()
            if clean.isupper():
                fixed = fixed.upper()
            out.append(lead + fixed + trail)
        elif clean.lower() != word.lower().strip(_PUNCT):
            piece = lead + clean + trail
            out.append(piece)
        else:
            out.append(word)
    return " ".join(out)


def apply_fix(original: str, fixed: str) -> None:
    """Replace typed word in the active field via backspace + write."""
    import keyboard

    for _ in range(len(original)):
        keyboard.send("backspace")
    keyboard.write(fixed, delay=0.006)
    dict_mod.record_correction(original, fixed)
