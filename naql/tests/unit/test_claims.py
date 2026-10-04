"""Tests for claims.py (S1, FR-30..33) with FakeLLMClient."""

from __future__ import annotations

from naql_core.claims import judge_claim
from naql_core.llm import FakeLLMClient
from naql_core.models import ClaimVerdict

_TEXT = "قال المؤلف رحمه الله في باب الصلاة ما نصه هنا"


def test_claim_supported() -> None:
    llm = FakeLLMClient(
        [
            {
                "verdict": "SUPPORTED",
                "explanation": "النص يدعم الاستنتاج مباشرة.",
                "supporting_spans": ["قال المؤلف رحمه الله"],
                "contradicting_spans": [],
            }
        ]
    )
    result = judge_claim(llm, claim="المؤلف تكلم عن الصلاة", matched_text_raw=_TEXT)  # type: ignore[arg-type]
    assert result.verdict == ClaimVerdict.SUPPORTED
    assert result.supporting_spans == ("قال المؤلف رحمه الله",)


def test_claim_invalid_verdict_retries_then_not_proven() -> None:
    llm = FakeLLMClient(
        [
            {"verdict": "MAYBE", "explanation": "x"},
            {"__invalid__": True},
        ]
    )
    result = judge_claim(llm, claim="ادعاء", matched_text_raw=_TEXT)  # type: ignore[arg-type]
    assert result.verdict == ClaimVerdict.NOT_PROVEN_IN_SOURCE


def test_claim_spans_filtered_to_verbatim_only() -> None:
    llm = FakeLLMClient(
        [
            {
                "verdict": "PARTIAL",
                "explanation": "",
                "supporting_spans": ["قال المؤلف", "عبارة غير موجودة في النص"],
                "contradicting_spans": [],
            }
        ]
    )
    result = judge_claim(llm, claim="استنتاج", matched_text_raw=_TEXT)  # type: ignore[arg-type]
    assert result.supporting_spans == ("قال المؤلف",)
