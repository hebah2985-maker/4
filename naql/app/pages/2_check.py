"""Screen 2: التحقق من نقل — paste a quote, verify, show verdict/diff/page (M3–M6)."""

from __future__ import annotations

import json

import streamlit as st

from app import state
from app import strings_ar as S
from app._shared import db_path, load_joined_source
from app.components.render_limits_footer import render_limits_footer
from app.components.render_page_image import render_page_image
from app.components.render_verdict_card import render_verdict_card
from app.components.render_word_diff import render_word_diff
from naql_core import db
from naql_core.claims import judge_claim
from naql_core.config import load_config
from naql_core.llm import LLMClient
from naql_core.match import check_quote
from naql_core.models import TextSource, Verdict

st.title(S.PAGE_CHECK)

doc_id = state.get_active_doc_id()
if doc_id is None:
    st.info(S.NO_DOCUMENT)
    st.stop()

path = db_path()
source = load_joined_source(str(path), doc_id)
with db.connect(path) as conn:
    doc = db.get_document(conn, doc_id)
    pages = db.get_pages(conn, doc_id)

quote = st.text_area(S.QUOTE_LABEL, height=120)
col_page, col_basis = st.columns(2)
with col_page:
    claimed_raw = st.text_input(S.CLAIMED_PAGE_LABEL, value="")
with col_basis:
    basis_label = st.radio(
        S.PAGE_BASIS_LABEL, [S.PAGE_BASIS_PDF, S.PAGE_BASIS_PRINTED], horizontal=True
    )
claim = st.text_area(S.CLAIM_LABEL, height=80)

if st.button(S.CHECK_BUTTON, disabled=not quote.strip(), use_container_width=True):
    with st.spinner(S.CHECK_RUNNING):
        claimed_page = int(claimed_raw) if claimed_raw.strip().isdigit() else None
        page_basis = "pdf" if basis_label == S.PAGE_BASIS_PDF else "printed"
        matched_pages = {p.pdf_page: p for p in pages}
        result = check_quote(
            source,
            quote,
            claimed_page=claimed_page,
            page_basis=page_basis,
            offset=doc.page_offset,
        )
        # UNRELIABLE_OCR if the matched page is a low-quality OCR page (M9)
        if result.matched_pdf_page in matched_pages:
            page_rec = matched_pages[result.matched_pdf_page]
            if (
                page_rec.text_source == TextSource.OCR
                and page_rec.ocr_confidence is not None
                and page_rec.ocr_confidence < 0.6
                and result.verdict in (Verdict.ALTERED, Verdict.SEMANTIC_ONLY)
            ):
                result = check_quote(
                    source,
                    quote,
                    claimed_page=claimed_page,
                    page_basis=page_basis,
                    offset=doc.page_offset,
                    ocr_low_quality=True,
                )
        state.set_last_check(result)
        with db.connect(path) as conn:
            db.insert_check_run(
                conn,
                doc_id=doc_id,
                quote=quote,
                claimed_page=claimed_page,
                page_basis=page_basis,
                claim=claim or None,
                verdict=result.verdict.value,
                page_verdict=result.page_verdict.value,
                matched_page=result.matched_pdf_page,
                confidence=result.confidence.value,
                diff_json=json.dumps(
                    [[op.kind.value, op.quote_word, op.source_word] for op in result.word_diff],
                    ensure_ascii=False,
                ),
            )

result = state.get_last_check()
if result is not None:
    render_verdict_card(result)
    if result.word_diff:
        render_word_diff(result.word_diff)
    if result.matched_pdf_page is not None:
        page_rec = next((p for p in pages if p.pdf_page == result.matched_pdf_page), None)
        if page_rec is not None:
            render_page_image(page_rec.image_path, page_rec.text_raw[:600])
    if claim.strip() and result.matched_text_raw:
        claim_result = judge_claim(
            LLMClient(load_config()), claim=claim, matched_text_raw=result.matched_text_raw
        )
        st.markdown(f"**{S.CLAIM_VERDICT_LABELS[claim_result.verdict.value]}**")
        if claim_result.explanation:
            st.caption(claim_result.explanation)
    col_ok, col_bad = st.columns(2)
    with col_ok:
        if st.button(S.FEEDBACK_CORRECT):
            st.caption(S.FEEDBACK_THANKS)
    with col_bad:
        if st.button(S.FEEDBACK_WRONG):
            st.caption(S.FEEDBACK_THANKS)

render_limits_footer()
