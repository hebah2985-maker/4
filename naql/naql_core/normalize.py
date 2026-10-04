"""Arabic normalization with original-position mapping (§17.1, K1).

Normalization is applied to a TEMPORARY copy only; the original source
text is never modified (C6). Every character in the normalized text maps
back to its position in the original via NormalizedText.norm_to_orig.

All functions here are pure (F4).
"""

from __future__ import annotations

import unicodedata

from naql_core.models import NormalizedText

_AR_DIACRITICS = frozenset(
    "ًٌٍَُِّْٰٓـ"  # tanween, harakat, shadda, sukun, superscript alef, tatweel
)
_TATWEEL = "ـ"

_ALEF_VARIANTS = frozenset("أإآٱ")
_YA_VARIANTS = frozenset("ىئ")
_TA_MARBUTA = "ة"
_HA = "ه"
_HAMZA_ON_WAW = "ؤ"

# Punctuation, brackets, ornaments stripped for matching (§17.1 rule 5).
_STRIP_CHARS = frozenset("«»﴾﴿[](){}<>‹›\"'`'’“”….,،;؛:؟?!—–-_/\\|*+=~^")

_AR_INDIC_DIGITS = {
    "٠": "0",
    "١": "1",
    "٢": "2",
    "٣": "3",
    "٤": "4",
    "٥": "5",
    "٦": "6",
    "٧": "7",
    "٨": "8",
    "٩": "9",
    "۰": "0",
    "۱": "1",
    "۲": "2",
    "۳": "3",
    "۴": "4",
    "۵": "5",
    "۶": "6",
    "۷": "7",
    "۸": "8",
    "۹": "9",
}


def _map_char(ch: str) -> str:
    """Map one original character to its normalized form ('' = dropped)."""
    if ch in _AR_DIACRITICS or ch == _TATWEEL:
        return ""
    if ch in _ALEF_VARIANTS:
        return "ا"
    if ch == _HAMZA_ON_WAW:
        return "و"
    if ch in _YA_VARIANTS:
        return "ي"
    if ch == _TA_MARBUTA:
        return _HA
    if ch in _AR_INDIC_DIGITS:
        return _AR_INDIC_DIGITS[ch]
    if ch in _STRIP_CHARS:
        return ""
    if unicodedata.category(ch) in ("Po", "Ps", "Pe", "So"):
        return ""
    if ch.isspace():
        return " "
    return ch


def normalize_for_match(text: str) -> NormalizedText:
    """Normalize Arabic text for matching, keeping a position map (K1).

    Rules (§17.1): strip tashkil and tatweel; unify alef/hamza variants,
    ya/alef-maqsura, ta-marbuta/ha; strip punctuation/brackets/ornaments;
    unify Arabic-Indic digits; collapse whitespace.

    Args:
        text: Original text (never modified — C6).

    Returns:
        NormalizedText with the normalized string and a per-character map
        back to original positions (CS10: chars written as UTF-8 literals).
    """
    norm_chars: list[str] = []
    positions: list[int] = []
    pending_space: int | None = None
    for idx, ch in enumerate(text):
        mapped = _map_char(ch)
        if mapped == "":
            continue
        if mapped == " ":
            if norm_chars and pending_space is None:
                pending_space = idx
            continue
        if pending_space is not None:
            norm_chars.append(" ")
            positions.append(pending_space)
            pending_space = None
        norm_chars.append(mapped)
        positions.append(idx)
    return NormalizedText(text_norm="".join(norm_chars), norm_to_orig=tuple(positions))


def orig_span(norm: NormalizedText, start: int, end: int, original: str) -> str:
    """Return the original-text substring covering norm[start:end] (K1).

    Args:
        norm: Result of normalize_for_match(original).
        start: Start index in the normalized string.
        end: End index (exclusive) in the normalized string.
        original: The original string the map was built from.

    Returns:
        The original substring, preserving tashkil and punctuation.
    """
    if start >= end or not norm.norm_to_orig:
        return ""
    orig_start = norm.norm_to_orig[start]
    orig_end = norm.norm_to_orig[min(end, len(norm.norm_to_orig)) - 1] + 1
    # Trailing tashkil/tatweel map to '' and would otherwise be clipped.
    while orig_end < len(original) and original[orig_end] in _AR_DIACRITICS:
        orig_end += 1
    return original[orig_start:orig_end]
