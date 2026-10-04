"""Fatwa/sharia-ruling guard (C5, FR-25, TC-19).

A simple rule-based classifier detects requests for fatwa, religious
ruling, or personal judgement; such questions are politely refused with
the tool's stated limits.
"""

from __future__ import annotations

# Rule keywords (Arabic). Matching any of them marks the question as a
# ruling/fatwa request. Extend cautiously; log only counts, never text (L2).
_FATWA_PATTERNS = (
    "ما حكم",
    "ما حکم",
    "أفتني",
    "فتوى",
    "هل يجوز",
    "هل يحرم",
    "هل يحل",
    "ما الراجح",
    "أيهما أرجح",
    "رجّح",
    "ترجيح",
    "هل هذا صحيح شرعاً",
    "حلال أم حرام",
    "ما رأيك",
    "هل أنا على صواب",
)


def is_fatwa_request(question: str) -> bool:
    """Return True if the question asks for a fatwa/ruling (C5)."""
    return any(pattern in question for pattern in _FATWA_PATTERNS)


def refusal_reason() -> str:
    """Fixed polite refusal wording (US-10, C8 tone)."""
    return (
        "هذه الأداة لا تفتي ولا ترجّح ولا تحكم على صحة المعنى؛"
        " هي تقارن النصوص بما في ملفك المرفوع فقط."
    )
