"""Screen 4: الخصوصية — AI disclosure, privacy policy and limits (FR-53)."""

from __future__ import annotations

import streamlit as st

from app import strings_ar as S
from app.components.render_limits_footer import render_limits_footer

st.title(S.PRIVACY_TITLE)
st.markdown(S.PRIVACY_BODY)
render_limits_footer()
