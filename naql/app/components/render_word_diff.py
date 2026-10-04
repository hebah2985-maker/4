"""Word-level diff renderer (FR-15, UX-04).

Each diff is described with readable text, not color alone.
"""

from __future__ import annotations

import streamlit as st

from app import strings_ar as S
from naql_core.models import DiffOp, DiffOpKind


def render_word_diff(diff: tuple[DiffOp, ...]) -> None:
    """Render added/removed/replaced words between quote and source.

    Args:
        diff: DiffOps from naql_core.match.compute_word_diff.
    """
    changed = [op for op in diff if op.kind != DiffOpKind.EQUAL]
    if not changed:
        st.success("لا فروق بين الاقتباس والمصدر.")
        return
    for op in changed:
        if op.kind == DiffOpKind.ADDED:
            st.markdown(f"- ➕ **{S.DIFF_ADDED}:** «{op.source_word}»")
        elif op.kind == DiffOpKind.REMOVED:
            st.markdown(f"- ➖ **{S.DIFF_REMOVED}:** «{op.quote_word}»")
        else:
            st.markdown(f"- ✎ **{S.DIFF_REPLACED}:** «{op.quote_word}» ← «{op.source_word}»")
