"""Typed wrappers around st.session_state (UI3): no direct access elsewhere."""

from __future__ import annotations

import uuid

import streamlit as st

_KEY_DOC_ID = "active_doc_id"
_KEY_LAST_CHECK = "last_check_result"
_KEY_LAST_QA = "last_qa_result"
_KEY_SESSION_ID = "session_id"


def get_active_doc_id() -> int | None:
    """Return the active document id, if any."""
    value = st.session_state.get(_KEY_DOC_ID)
    return int(value) if value is not None else None


def set_active_doc_id(doc_id: int) -> None:
    """Set the active document id."""
    st.session_state[_KEY_DOC_ID] = doc_id


def clear_active_doc() -> None:
    """Forget the active document and any cached results."""
    for key in (_KEY_DOC_ID, _KEY_LAST_CHECK, _KEY_LAST_QA):
        st.session_state.pop(key, None)


def set_last_check(result: object) -> None:
    """Cache the latest citation-check result for rendering."""
    st.session_state[_KEY_LAST_CHECK] = result


def get_last_check() -> object | None:
    """Return the latest citation-check result, if any."""
    return st.session_state.get(_KEY_LAST_CHECK)


def get_session_id() -> str:
    """Return this visitor's private session id, creating it on first use (FR-50)."""
    value = st.session_state.get(_KEY_SESSION_ID)
    if not isinstance(value, str):
        value = uuid.uuid4().hex
        st.session_state[_KEY_SESSION_ID] = value
    return value
