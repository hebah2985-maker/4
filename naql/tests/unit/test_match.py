"""Tests for match.py (T3: EXACT/MINOR_DIFF/ALTERED, pages, diff, C1 gate)."""

from __future__ import annotations

from naql_core.match import (
    build_joined_source,
    check_quote,
    compute_word_diff,
    verify_quote_exists,
)
from naql_core.models import DiffOpKind, PageVerdict, Verdict

_PAGE1 = "قال الله تعالى في كتابه العزيز آيات بينات لكل مسلم"
_PAGE2 = "ثم قال المؤلف رحمه الله في باب الصلاة ما نصه هنا"


def _source() -> object:
    return build_joined_source([(1, 1, _PAGE1), (2, 2, _PAGE2)])


def test_check_quote_exact_match() -> None:
    result = check_quote(_source(), "آيات بينات لكل مسلم")  # type: ignore[arg-type]
    assert result.verdict == Verdict.EXACT
    assert result.matched_pdf_page == 1


def test_check_quote_exact_with_tashkeel_difference() -> None:
    result = check_quote(_source(), "آيَاتٍ بَيِّنَاتٍ لِكُلِّ مُسْلِمٍ")  # type: ignore[arg-type]
    assert result.verdict == Verdict.EXACT


def test_check_quote_minor_diff_punctuation() -> None:
    result = check_quote(_source(), "آيات بينات، لكل مسلم!")  # type: ignore[arg-type]
    assert result.verdict in (Verdict.EXACT, Verdict.MINOR_DIFF)


def test_check_quote_altered_word_replaced() -> None:
    result = check_quote(_source(), "آيات بينات لكل كافر")  # type: ignore[arg-type]
    assert result.verdict == Verdict.ALTERED
    replaced = [op for op in result.word_diff if op.kind == DiffOpKind.REPLACED]
    assert replaced and replaced[0].source_word == "مسلم"


def test_check_quote_not_found() -> None:
    result = check_quote(_source(), "نص غير موجود إطلاقاً في هذا الكتاب")  # type: ignore[arg-type]
    assert result.verdict == Verdict.NOT_FOUND


def test_check_quote_cross_page_span() -> None:
    quote = "لكل مسلم ثم قال المؤلف رحمه الله"
    result = check_quote(_source(), quote)  # type: ignore[arg-type]
    assert result.verdict in (Verdict.EXACT, Verdict.MINOR_DIFF, Verdict.ALTERED)
    assert result.matched_pdf_page == 1


def test_page_verdict_ok_when_claimed_correct() -> None:
    result = check_quote(_source(), "رحمه الله في باب الصلاة", claimed_page=2)  # type: ignore[arg-type]
    assert result.page_verdict == PageVerdict.PAGE_OK


def test_page_verdict_wrong_with_correct_page_shown() -> None:
    result = check_quote(_source(), "رحمه الله في باب الصلاة", claimed_page=5)  # type: ignore[arg-type]
    assert result.page_verdict == PageVerdict.PAGE_WRONG
    assert result.matched_pdf_page == 2


def test_page_verdict_unknown_without_claim() -> None:
    result = check_quote(_source(), "رحمه الله في باب الصلاة")  # type: ignore[arg-type]
    assert result.page_verdict == PageVerdict.PAGE_UNKNOWN


def test_page_verdict_printed_basis_with_offset() -> None:
    result = check_quote(
        _source(),
        "رحمه الله في باب الصلاة",  # type: ignore[arg-type]
        claimed_page=1,
        page_basis="printed",
        offset=1,
    )
    assert result.page_verdict == PageVerdict.PAGE_OK


def test_word_diff_added_removed_replaced() -> None:
    diff = compute_word_diff("قال تعالى في كتابه", "قال الله تعالى كتابه العزيز")
    kinds = {op.kind for op in diff}
    assert DiffOpKind.REPLACED in kinds or DiffOpKind.ADDED in kinds


def test_verify_quote_exists_true_for_real_quote() -> None:
    assert verify_quote_exists(_source(), "آيات بينات") is True  # type: ignore[arg-type]


def test_verify_quote_exists_false_for_fabrication() -> None:
    assert verify_quote_exists(_source(), "كلام مختلق لا وجود له نهائياً") is False  # type: ignore[arg-type]


def test_unreliable_ocr_when_flagged_and_weak() -> None:
    result = check_quote(_source(), "نص بعيد جداً عن المحتوى", ocr_low_quality=True)  # type: ignore[arg-type]
    assert result.verdict in (Verdict.UNRELIABLE_OCR, Verdict.NOT_FOUND)
