"""Verdict card component (UI1, UI6): single source of verdict rendering.

Receives ready dataclass data from models.py; never calls ingest/db/llm.
Verdicts appear as word + icon + color — never color alone (UX-04).
"""

from __future__ import annotations

import streamlit as st

from app import strings_ar as S
from naql_core.models import PageVerdict, QuoteCheckResult

_VERDICT_ICONS = {
    "EXACT": "✔",
    "MINOR_DIFF": "◐",
    "ALTERED": "✎",
    "SEMANTIC_ONLY": "≈",
    "NOT_FOUND": "✘",
    "UNRELIABLE_OCR": "؟",
}


def render_verdict_card(result: QuoteCheckResult) -> None:
    """Render the fixed-order result card: verdict → page → diff → image (UX-03).

    Args:
        result: A completed QuoteCheckResult from naql_core.match.
    """
    verdict_label = S.VERDICT_LABELS[result.verdict.value]
    icon = _VERDICT_ICONS[result.verdict.value]
    confidence = S.CONFIDENCE_LABELS[result.confidence.value]

    st.markdown(f"### {icon} {verdict_label}")
    if result.verdict.value != "NOT_FOUND":
        percent = round(max(0.0, min(1.0, result.similarity)) * 100)
        st.markdown(f"**{S.SIMILARITY_LABEL}: {percent}%**")
    st.caption(f"{confidence} — {result.reason}")

    page_label = S.PAGE_VERDICT_LABELS[result.page_verdict.value]
    if result.page_verdict == PageVerdict.PAGE_WRONG and result.matched_pdf_page:
        st.warning(
            f"{page_label}. الصفحة الصحيحة: PDF {result.matched_pdf_page}"
            + (
                f" / الطبعة {result.matched_printed_page}"
                if result.matched_printed_page is not None
                else ""
            )
        )
    else:
        st.info(page_label)

    if result.matched_text_raw:
        st.markdown(f"**{S.MATCHED_TEXT_LABEL}:**")
        st.markdown(f"> {result.matched_text_raw}")
    if result.crossed_pages:
        st.caption(S.CROSSED_PAGES_NOTE)
