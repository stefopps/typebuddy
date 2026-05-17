"""
sentence_buffer.py — 6-row display: 5 completed sentences + 1 active line.
"""

from __future__ import annotations

import threading

from corrector import pre_correct

MAX_COMPLETED = 5
NUM_ROWS = 6

_SENTENCE_END = frozenset(".!?")


def _should_commit_sentence(buf: str) -> bool:
    """Commit when 100+ chars, or .!? boundary and 60+ chars."""
    stripped = buf.strip()
    if len(stripped) >= 100:
        return True
    if len(stripped) >= 60 and stripped[-1] in _SENTENCE_END:
        return True
    return False


def display_sentence(s: str, max_chars: int = 100) -> str:
    """Truncate for UI only — full text stays in buffer."""
    t = s.replace("\n", " ").strip()
    if not t:
        return "—"
    return t if len(t) <= max_chars else t[: max_chars - 3] + "…"


class SentenceBuffer:
    """Up to 5 completed sentences + one live line (row 6)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sentence_buffer: list[dict[str, str]] = []
        self._current_raw = ""
        self._active_override: str | None = None

    def current_raw(self) -> str:
        with self._lock:
            return self._current_raw

    def get_all_corrected(self) -> str:
        """All completed sentences + active line, joined for clipboard."""
        with self._lock:
            parts = [c["corrected"].strip() for c in self._sentence_buffer if c["corrected"].strip()]
            if self._active_override is not None:
                parts.append(self._active_override.strip())
            elif self._current_raw.strip():
                parts.append(pre_correct(self._current_raw).strip())
            return " ".join(parts)

    def clear_all(self) -> None:
        with self._lock:
            self._sentence_buffer = []
            self._current_raw = ""
            self._active_override = None

    def append_char(self, ch: str) -> bool:
        with self._lock:
            self._current_raw += ch
            if _should_commit_sentence(self._current_raw):
                self._finalize_locked()
                return True
        return False

    def append_space(self) -> None:
        with self._lock:
            if self._current_raw and not self._current_raw.endswith(" "):
                self._current_raw += " "
            if _should_commit_sentence(self._current_raw):
                self._finalize_locked()

    def backspace(self) -> None:
        with self._lock:
            if self._current_raw:
                self._current_raw = self._current_raw[:-1]
            self._active_override = None

    def backspace_word(self) -> None:
        with self._lock:
            raw = self._current_raw.rstrip()
            if not raw:
                self._current_raw = ""
            elif " " in raw:
                self._current_raw = raw[: raw.rfind(" ") + 1]
            else:
                self._current_raw = ""
            self._active_override = None

    def clear_active_override(self) -> None:
        with self._lock:
            self._active_override = None

    def _append_completed(self, raw: str, corrected: str) -> None:
        corrected = corrected.strip()
        if not corrected:
            return
        if self._sentence_buffer and self._sentence_buffer[-1]["corrected"] == corrected:
            return
        self._sentence_buffer.append({"raw": raw, "corrected": corrected})
        self._sentence_buffer = self._sentence_buffer[-MAX_COMPLETED:]

    def commit_corrected(self, raw: str, corrected: str) -> None:
        with self._lock:
            self._append_completed(raw, corrected)
            self._current_raw = ""
            self._active_override = None

    def set_active_preview(self, corrected: str) -> None:
        with self._lock:
            self._active_override = corrected

    def _finalize_locked(self) -> None:
        raw = self._current_raw.strip()
        if not raw:
            self._current_raw = ""
            return
        corrected = pre_correct(raw)
        self._append_completed(raw, corrected)
        self._current_raw = ""
        self._active_override = None

    def display_rows(self) -> tuple[str, str, str, str, str, str]:
        """Rows 1–5: completed (dim). Row 6: active line (bright)."""
        with self._lock:
            comp = [c["corrected"] for c in self._sentence_buffer]
            prior = comp[-MAX_COMPLETED:]
            rows_1_5: list[str] = []
            pad = MAX_COMPLETED - len(prior)
            for i in range(MAX_COMPLETED):
                if i < pad:
                    rows_1_5.append("—")
                else:
                    rows_1_5.append(display_sentence(prior[i - pad]))

            if self._active_override is not None:
                row6 = self._active_override
            elif self._current_raw:
                row6 = pre_correct(self._current_raw)
                row6 = f"{row6}▌" if row6 else f"{self._current_raw}▌"
            else:
                row6 = "—"

            return (
                rows_1_5[0],
                rows_1_5[1],
                rows_1_5[2],
                rows_1_5[3],
                rows_1_5[4],
                row6,
            )
