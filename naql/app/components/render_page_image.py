"""Page image renderer (M6, FR-16): image beside the matched text (UX-08).

Never renders a page number in results unless the reference page image is
available; when no image exists (text-layer PDFs), shows the text context
instead.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app import strings_ar as S


def render_page_image(image_path: str | None, context_text: str) -> None:
    """Render the source page image next to its matched text context.

    Args:
        image_path: Path to the rendered page image, or None (text-layer PDF).
        context_text: Neighboring source text for context (FR-16).
    """
    col_image, col_text = st.columns(2)
    with col_image:
        if image_path and Path(image_path).exists():
            st.image(image_path, caption=S.PAGE_IMAGE_LABEL, use_container_width=True)
        else:
            st.caption(f"{S.PAGE_IMAGE_LABEL}: غير متوفرة (ملف نصي الطبقة).")
    with col_text:
        st.markdown(f"**{S.CONTEXT_LABEL}:**")
        st.markdown(f"> {context_text}")
