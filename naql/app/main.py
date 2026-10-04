"""Streamlit entry point: RTL setup and navigation (UI5).

Only three screens exist (UX-02): المصدر، التحقق من نقل، سؤال وجواب.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the repo root importable when hosted (Streamlit runs scripts from app/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from app import strings_ar as S  # noqa: E402

_RTL_CSS = """
<style>
  html, body, [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
  [data-testid="stSidebar"] { direction: rtl; }
  .stMarkdown, .stCaption, p, h1, h2, h3, h4, label { text-align: right; }
  @media (max-width: 768px) {
    [data-testid="stHorizontalBlock"] { flex-direction: column; }
  }
</style>
"""


def main() -> None:
    """Configure the app and dispatch to the three pages."""
    st.set_page_config(page_title=S.APP_TITLE, layout="wide")
    st.markdown(_RTL_CSS, unsafe_allow_html=True)
    pages = [
        st.Page("pages/1_source.py", title=S.PAGE_SOURCE, icon="📄"),
        st.Page("pages/2_check.py", title=S.PAGE_CHECK, icon="✔"),
        st.Page("pages/3_qa.py", title=S.PAGE_QA, icon="❓"),
        st.Page("pages/4_privacy.py", title=S.PAGE_PRIVACY, icon="🔒"),
    ]
    st.navigation(pages).run()


if __name__ == "__main__":
    main()
else:
    main()
