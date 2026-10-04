"""Tests for safety.py (C5, TC-19: fatwa questions refused)."""

from __future__ import annotations

from naql_core.safety import is_fatwa_request, refusal_reason


def test_fatwa_detected_for_hukm_question() -> None:
    assert is_fatwa_request("ما حكم فعل كذا وكذا؟") is True


def test_fatwa_detected_for_tarjih_question() -> None:
    assert is_fatwa_request("ما الراجح في هذه المسألة؟") is True


def test_fatwa_detected_for_jawaz_question() -> None:
    assert is_fatwa_request("هل يجوز أن أفعل هذا؟") is True


def test_normal_question_not_refused() -> None:
    assert is_fatwa_request("ماذا قال المؤلف عن باب الصلاة؟") is False


def test_refusal_reason_states_limits() -> None:
    reason = refusal_reason()
    assert "لا تفتي" in reason or "لا تُفتي" in reason
