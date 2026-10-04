"""Screen 1: المصدر — upload, offset setup, deletion (M1, M2, M9, M11)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app import state
from app import strings_ar as S
from app._shared import db_path, session_data_dir
from app.components.render_limits_footer import render_limits_footer
from naql_core import db
from naql_core.errors import IngestError, NaqlError
from naql_core.ingest import ingest_pdf

st.title(S.PAGE_SOURCE)

path = db_path()
with db.connect(path) as conn:
    documents = db.list_documents(conn)

if documents:
    options = {f"{d.title} ({d.n_pages} صفحة)": d.id for d in documents}
    choice = st.selectbox(S.DOC_SELECT_LABEL, list(options.keys()))
    if choice:
        state.set_active_doc_id(options[choice])

uploaded = st.file_uploader(S.UPLOAD_LABEL, type=["pdf", "png", "jpg", "jpeg"])
title = st.text_input("عنوان المصدر", value=uploaded.name if uploaded else "")
volume = st.text_input("اسم الجزء (اختياري)", value="")

if st.button(S.UPLOAD_BUTTON, disabled=uploaded is None, use_container_width=True):
    data_dir = session_data_dir()
    pdf_path = data_dir / f"upload_{Path(uploaded.name).name}"
    pdf_path.write_bytes(uploaded.getvalue())
    bar = st.progress(0.0, text=S.UPLOAD_PROGRESS)
    try:
        with db.connect(path) as conn:

            def _on_progress(p) -> None:
                bar.progress(p.done_pages / max(1, p.total_pages), text=S.UPLOAD_PROGRESS)

            doc_id = ingest_pdf(
                conn,
                pdf_path,
                title=title or uploaded.name,
                volume_label=volume or None,
                data_dir=data_dir,
                on_progress=_on_progress,
            )
            pages = db.get_pages(conn, doc_id)
    except (IngestError, NaqlError) as exc:
        st.error(f"{S.ERROR_GENERIC} ({type(exc).__name__})")
        st.stop()
    state.set_active_doc_id(doc_id)
    bar.empty()
    st.success(f"{S.UPLOAD_DONE} {S.PAGE_COUNT_LABEL}: {len(pages)}")
    low = [p.pdf_page for p in pages if p.ocr_confidence is not None and p.ocr_confidence < 0.6]
    if low:
        st.warning(f"{S.LOW_QUALITY_WARNING} {', '.join(str(n) for n in low)}")

active_id = state.get_active_doc_id()
if active_id is not None:
    with db.connect(path) as conn:
        doc = db.get_document(conn, active_id)
    offset = st.number_input(
        S.OFFSET_LABEL, min_value=0, value=doc.page_offset, step=1, help=S.OFFSET_HELP
    )
    if offset != doc.page_offset:
        with db.connect(path) as conn:
            db.set_page_offset(conn, active_id, int(offset))
        st.cache_data.clear()
        st.rerun()
    if st.button(DELETE_LABEL := S.DELETE_BUTTON, type="secondary"):
        with db.connect(path) as conn:
            files = db.delete_document(conn, active_id)
        for file in files:
            Path(file).unlink(missing_ok=True)
        state.clear_active_doc()
        st.cache_data.clear()
        st.success(S.DELETE_DONE)
        st.rerun()

render_limits_footer()
