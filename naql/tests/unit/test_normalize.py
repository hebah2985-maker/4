"""Tests for normalize.py (T3: tashkil, tatweel, hamza, digits, mapping)."""

from __future__ import annotations

from naql_core.normalize import normalize_for_match, orig_span


def test_normalize_strips_tashkeel() -> None:
    norm = normalize_for_match("بِسْمِ اللَّهِ الرَّحْمَٰنِ")
    assert norm.text_norm == "بسم الله الرحمن"


def test_normalize_removes_tatweel() -> None:
    norm = normalize_for_match("الحمـد لله")
    assert "ـ" not in norm.text_norm
    assert "الحمد" in norm.text_norm


def test_normalize_unifies_alef_hamza() -> None:
    norm = normalize_for_match("أإآٱ")
    assert norm.text_norm == "اااا"


def test_normalize_unifies_ya_and_alef_maqsura() -> None:
    norm = normalize_for_match("على موسى")
    assert norm.text_norm == "علي موسي"


def test_normalize_unifies_ta_marbuta() -> None:
    norm = normalize_for_match("الصلاة")
    assert norm.text_norm == "الصلاه"


def test_normalize_strips_brackets_and_ornaments() -> None:
    norm = normalize_for_match("﴾قال﴿ [تعليق] «نص»")
    for ch in "﴾﴿[]«»":
        assert ch not in norm.text_norm


def test_normalize_unifies_arabic_indic_digits() -> None:
    norm = normalize_for_match("ص ١٢٣ و ۴۵۶")
    assert "123" in norm.text_norm
    assert "456" in norm.text_norm


def test_normalize_collapses_whitespace() -> None:
    norm = normalize_for_match("قال   تعالى\n\n  في")
    assert "  " not in norm.text_norm
    assert norm.text_norm == "قال تعالي في"  # ى تُوحَّد إلى ي


def test_normalize_position_map_roundtrip() -> None:
    original = "بِسْمِ اللَّهِ"
    norm = normalize_for_match(original)
    recovered = orig_span(norm, 0, len(norm.text_norm), original)
    assert "بِسْمِ" in recovered
    assert "اللَّهِ" in recovered


def test_normalize_empty_text() -> None:
    norm = normalize_for_match("")
    assert norm.text_norm == ""
    assert norm.norm_to_orig == ()
