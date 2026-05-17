"""
smoke_test.py — Run before using TypeBuddy. All checks must pass.
  python smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def test(name: str, fn) -> bool:
    print(f"  {name}... ", end="", flush=True)
    try:
        result = fn()
        print(f"PASS  {result}")
        return True
    except Exception as e:
        print(f"FAIL  {e}")
        return False


print()
print("=" * 55)
print("  TypeBuddy — Smoke Test")
print("=" * 55)
print()

results: list[bool] = []


def t1():
    import dictionary as dict_mod

    dict_mod.ensure_data_files()
    dict_mod.reload_engine()
    n = dict_mod.word_count()
    if n < 1000:
        raise RuntimeError(f"vocab too small ({n})")
    return f"{n:,} words loaded"


results.append(test("1. SymSpell loads", t1))


def t2():
    import main

    main._hook_registered = False
    main.register_hook()
    if not main._hook_registered:
        raise RuntimeError("hook not registered")
    try:
        import keyboard

        keyboard.unhook_all()
    except Exception:
        pass
    main._hook_registered = False
    return "keyboard.hook registered"


results.append(test("2. Hook fires", t2))


def t3():
    import dictionary as dict_mod
    from corrector import fix_word

    dict_mod.reload_engine()
    pair = fix_word("teh")
    if not pair or pair[1].lower() != "the":
        raise RuntimeError(f"expected teh→the, got {pair}")
    return f'"{pair[0]}" → "{pair[1]}"'


results.append(test("3. Correction fires", t3))


def t3b():
    from corrector import _clean_doubles, _clean_doubles_word, fix_word, pre_correct

    if _clean_doubles("ddonewant") != "donewant":
        raise RuntimeError("double-strike failed on ddonewant")
    if _clean_doubles_word("sshouldbe") != "shouldbe":
        raise RuntimeError("double-strike failed on sshouldbe")
    if _clean_doubles_word("nnicesttool") != "nicesttool":
        raise RuntimeError("double-strike failed on nnicesttool")
    pair = fix_word("tteheequali")
    if not pair or "tehe" not in pair[1].lower():
        raise RuntimeError(f"fix_word ttehequali failed: {pair}")
    pc = pre_correct("sshouldbe nniciesttool").lower()
    if "sshould" in pc or "nnicest" in pc:
        raise RuntimeError(f"pre_correct pass 0 missing doubles: {pc}")
    if "niciest" not in pc and "nicest" not in pc:
        raise RuntimeError(f"expected niciest/nicest after doubles: {pc}")
    return "doubles in pre_correct + fix_word"


results.append(test("3b. Double-strike cleaner", t3b))


def t3c():
    from sentence_buffer import SentenceBuffer, _should_commit_sentence

    assert not _should_commit_sentence("Hi.")
    assert _should_commit_sentence("x" * 100)
    assert _should_commit_sentence("x" * 60 + ".")

    buf = SentenceBuffer()
    for ch in "a" * 100:
        buf.append_char(ch)
    for ch in "b" * 100:
        buf.append_char(ch)
    for ch in "Still typing":
        buf.append_char(ch)
    rows = buf.display_rows()
    if len(rows) != 6:
        raise RuntimeError(f"expected 6 rows, got {len(rows)}")
    if "aaa" not in rows[3]:
        raise RuntimeError(f"line4 wrong: {rows[3][:40]}")
    if "bbb" not in rows[4]:
        raise RuntimeError(f"line5 wrong: {rows[4][:40]}")
    if "Still" not in rows[5]:
        raise RuntimeError(f"line6 wrong: {rows[5]}")
    all_text = buf.get_all_corrected()
    if "aaa" not in all_text or "bbb" not in all_text or "Still" not in all_text:
        raise RuntimeError(f"get_all_corrected: {all_text[:80]}")
    return "6 rows + copy-all text"


results.append(test("3c. Sentence buffer (6 rows)", t3c))


def t3d():
    from corrector import pre_correct
    from patterns import apply_patterns

    if apply_patterns("athos athcs") != "patterns patterns":
        raise RuntimeError("pattern pass failed on athos/athcs")
    pc = pre_correct("ligjtwgit leeanifgn mathos")
    if "lightweight" not in pc or "learning" not in pc or "patterns" not in pc:
        raise RuntimeError(f"pre_correct patterns missing: {pc}")
    return "memory.json patterns (10×) fire in pre_correct"


results.append(test("3d. FixIt patterns", t3d))


def t3e():
    from corrector import fix_word
    from patterns import is_protected

    for term in ("sth", "smth", "bc", "w/", "w/o", "b/c"):
        if not is_protected(term):
            raise RuntimeError(f"{term!r} not protected")
    if fix_word("sth") is not None:
        raise RuntimeError('fix_word must not change "sth"')
    return "abbreviations protected (sth, smth, bc, w/, w/o, b/c)"


results.append(test("3e. Protected terms", t3e))


def t3f():
    from patterns import apply_patterns

    if apply_patterns("cannto cannt caanot") != "cannot cannot cannot":
        raise RuntimeError("cannot patterns failed")
    return "cannto/cannt/caanot → cannot"


results.append(test("3f. cannot patterns", t3f))


def t3g():
    from patterns import apply_patterns

    out = apply_patterns("inened thi sone wan tto")
    if out != "I need this one want to":
        raise RuntimeError(f"phrase patterns failed: {out!r}")
    return "multi-word + smash patterns"


results.append(test("3g. Phrase patterns", t3g))


def t3h():
    from corrector import pre_correct
    from patterns import apply_patterns, split_stuck_tokens

    if apply_patterns("apourtogether sspeedttesting") != "appear together speed testing":
        raise RuntimeError("stuck smash patterns failed")
    if "human" not in pre_correct("hunan beeng"):
        raise RuntimeError("being/human patterns failed")
    out = split_stuck_tokens("xxxxx")  # no split for short
    if out != "xxxxx":
        raise RuntimeError("split_stuck should skip short tokens")
    return "stuck split pass + smash patterns"


results.append(test("3h. Stuck-token split", t3h))


def t4():
    import dictionary as dict_mod

    dict_mod.reload_engine()
    before = (
        dict_mod.PERSONAL_FREQ.read_text(encoding="utf-8")
        if dict_mod.PERSONAL_FREQ.exists()
        else ""
    )
    dict_mod.record_correction("teh", "the")
    after = dict_mod.PERSONAL_FREQ.read_text(encoding="utf-8")
    if "the" not in after.lower():
        raise RuntimeError("personal frequency not saved")
    return "frequency_personal.txt updated"


results.append(test("4. Dictionary saves", t4))


def t5():
    import tkinter as tk

    from strip import StatusStrip

    root = tk.Tk()
    strip = StatusStrip(root)
    strip.set_typing("ggreat")
    strip.snap_to_cursor()
    root.update_idletasks()
    w = root.winfo_width()
    from strip import TOTAL_H, BAR_W

    if w < BAR_W - 20:
        raise RuntimeError(f"strip too narrow ({w}px)")
    strip.set_sentence_rows(
        "—",
        "—",
        "—",
        "First sentence here.",
        "Second sentence here.",
        "tthe third ssentence▌",
    )
    root.update_idletasks()
    h = root.winfo_height()
    if h < TOTAL_H - 4:
        raise RuntimeError(f"height too small ({h}px, want {TOTAL_H})")
    typing = strip._typing_var.get()
    if "ggreat" not in typing:
        raise RuntimeError(f"typing segment missing: {typing}")
    root.destroy()
    return f"strip rendered ({w}px, typing segment ok)"


results.append(test("5. UI renders", t5))

passed = sum(results)
print()
total = len(results)
print(f"  Result: {passed}/{total} passed")
if passed == total:
    print("  OK — run START_TYPEBUDDY.bat as Administrator")
else:
    print("  FAIL — fix errors above")
print("=" * 55)
print()
sys.exit(0 if passed == total else 1)
