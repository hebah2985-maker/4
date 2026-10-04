"""Screen 3: سؤال وجواب — source-grounded Q&A with abstention (M7, M8)."""

from __future__ import annotations

import streamlit as st

from app import state
from app import strings_ar as S
from app._shared import db_path, load_joined_source
from app.components.render_limits_footer import render_limits_footer
from naql_core import db
from naql_core.config import load_config
from naql_core.llm import LLMClient
from naql_core.models import QaStatus
from naql_core.qa import answer_question
from naql_core.safety import refusal_reason

st.title(S.PAGE_QA)

doc_id = state.get_active_doc_id()
if doc_id is None:
    st.info(S.NO_DOCUMENT)
    st.stop()

path = db_path()
question = st.text_area(S.QA_LABEL, height=100)

if st.button(S.QA_BUTTON, disabled=not question.strip(), use_container_width=True):
    with st.spinner(S.QA_RUNNING):
        source = load_joined_source(str(path), doc_id)
        llm = LLMClient(load_config())
        with db.connect(path) as conn:
            result = answer_question(conn, source, llm, doc_id=doc_id, question=question)
    if result.status == QaStatus.REFUSED:
        st.warning(refusal_reason())
    elif result.status == QaStatus.ABSTAINED:
        st.info(S.QA_ABSTAINED)
        if result.nearest_chunks:
            st.markdown(f"**{S.QA_NEAREST}**")
            for item in result.nearest_chunks[:3]:
                st.caption(f"ص {item.chunk.pdf_page}: {item.chunk.text_raw[:200]}…")
    else:
        if result.model_id == "extractive-fallback":
            st.caption(S.QA_EXTRACTIVE_NOTE)
        for sentence in result.sentences:
            st.markdown(f"**{S.QA_SYSTEM_SAYS}:** {sentence.text}")
            st.markdown(
                f"**{S.QA_TEXT_SAYS} (ص {sentence.pdf_page} / الطبعة"
                f" {sentence.printed_page}):** «{sentence.quote}»"
            )

render_limits_footer()
