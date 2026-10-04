"""Persistent limits reminder (M10, UX-09): always in the page footer."""

from __future__ import annotations

import streamlit as st

from app import strings_ar as S


def render_limits_footer() -> None:
    """Render the tool's fixed limits line at the bottom of every screen."""
    st.divider()
    st.caption(S.LIMITS_LINE)
